import os
import httpx
import faiss
import pickle
import uvicorn
import asyncio
import aiomysql
import numpy as np
from datetime import datetime
from openai import AsyncOpenAI
from pydantic import BaseModel
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

# 设置环境变量
os.environ["OPENAI_API_KEY"] = "******"
os.environ["OPENAI_BASE_URL"] = "https://integrate.api.nvidia.com/v1"

# 初始化 OpenAI 客户端
client = AsyncOpenAI(
    api_key=os.environ["OPENAI_API_KEY"],
    base_url=os.environ["OPENAI_BASE_URL"]
)

# 加载 FAISS 索引和 ID 映射
index = faiss.read_index("vector_index.faiss")
with open("id_map.pkl", "rb") as f:
    id_map = pickle.load(f)

# 请求 & 响应模型
class QueryRequest(BaseModel):
    mode: str
    code: str
    message: str

class QueryResponse(BaseModel):
    result: str

# 数据库启动
async def lifespan(app: FastAPI):
    app.state.db_pool = await aiomysql.create_pool(
        host='******',
        port=3306,
        user='******',
        password='******',
        db='******',
        charset='utf8',
        autocommit=True,
        minsize=1,
        maxsize=100
    )
    print("数据库连接池已创建")
    yield
    app.state.db_pool.close()
    await app.state.db_pool.wait_closed()
    print("数据库连接池已关闭")

# 创建 FastAPI 应用
app = FastAPI(lifespan=lifespan)

# 查询数据库中会员信息
async def query_member_info(pool, mem_code: str):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT real_name, sex, birthday FROM ads_members_information WHERE mem_code = %s",
                (mem_code,)
            )
            return await cursor.fetchone()
        
# 查询数据库中店铺信息
async def query_shop_info(pool, shop_code: str):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT distinct city FROM new_shop_channel_expanding WHERE shop_code = %s",
                (shop_code,)
            )
            result = await cursor.fetchone()
            return result[0]

# 天气数据获取函数
async def get_weather_info(adcode: str) -> str:
    url = f"https://api.caiyunapp.com/v2.6/******/weather.json?adcode={adcode}&alert=true"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("result", {}).get("forecast_keypoint", "暂无天气简报")
            else:
                return f"天气接口错误：{response.status_code}"
        except Exception as e:
            return f"天气接口异常：{str(e)}"

# 调用大模型生成回答
async def generate_response(prompt: str):
    try:
        response = await client.chat.completions.create(
            model="nvidia/llama-3.1-nemotron-ultra-253b-v1",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            stream=True
        )

        async def content_generator():
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        return content_generator()
    except Exception as e:
        async def error():
            yield f"模型调用失败: {str(e)}"
        return error()
    
# 调用大模型推理回答
async def generate_reasoning_response(prompt: str):
    try:
        response = await client.chat.completions.create(
            model="deepseek-ai/deepseek-r1",
            messages=[{"role": "user", "content": prompt}],
            temperature=1,
            stream=True
        )

        async def content_generator():
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        return content_generator()
    except Exception as e:
        async def error():
            yield f"模型调用失败: {str(e)}"
        return error()

# 嵌入获取
async def get_query_embedding(text: str):
    response = await client.embeddings.create(
        input=[text],
        model="nvidia/nv-embedcode-7b-v1",
        encoding_format="float",
        extra_body={"input_type": "query", "truncate": "NONE"}
    )
    return response.data[0].embedding

# 向量搜索
async def query(text_query: str, top_k: int = 10):
    query_vector = np.array(await get_query_embedding(text_query)).astype("float32").reshape(1, -1)
    distances, indices = index.search(query_vector, top_k)
    results = [(id_map[i], distances[0][j]) for j, i in enumerate(indices[0])]
    return results

# 主接口逻辑
@app.post("/script", response_model=QueryResponse)
async def conversation(request: QueryRequest, fastapi_request: Request):
    # 连接数据库
    db_pool = fastapi_request.app.state.db_pool
    # 获取当前日期
    current_date = datetime.now().strftime("%Y%m%d")

    if request.mode == "0":  # 生日祝福
        code = request.code.strip()
        member = await query_member_info(db_pool, code)

        if member:
            name, sex, birthday = member
            member_info = f"姓名：{name}，性别：{sex}，生日：{birthday}"
            prompt = (
                "你是生日祝福生成助手，请根据顾客信息生成一段生日祝福。\n"
                "- 第一步，理解顾客信息。\n"
                f"1.顾客信息：{member_info}\n"
                f"2.附加信息：{request.message}\n"
                f"3.当前日期：{current_date}\n"
                "- 第二步，理解生成规则。\n"
                "1.请输出中文生日祝福。\n"
                "2.可以结合顾客年龄添加emoji表情符号。\n"
                "3.祝福内容可以结合季节特点、顾客年龄、性别喜好等。\n"
                "4.不要输出解释或者无关内容。"
                "- 第三步，请直接输出生日祝福。"
            )
            stream_generator = await generate_response(prompt)
            return StreamingResponse(stream_generator, media_type="text/plain; charset=utf-8")
        else:
            return StreamingResponse(iter(["未找到该会员的信息。"]), media_type="text/plain; charset=utf-8")

    elif request.mode == "1":  # 天气提醒
        code = request.code.strip()
        shop = await query_shop_info(db_pool, code)
        if shop:
            shop = shop[:6]
            weather_info = await get_weather_info(shop)
            prompt = (
                "你是天气提醒生成助手，请根据天气信息生成一段天气提醒。\n"
                "- 第一步，理解天气信息。\n"
                f"1.天气信息：{weather_info}\n"
                f"2.附加信息：{request.message}\n"
                f"3.当前日期：{current_date}\n"
                "- 第二步，理解生成规则。\n"
                "1.天气提醒的对象是顾客。\n"
                "2.可以结合天气情况添加emoji表情符号。\n"
                "3.提醒内容可以结合出行建议、穿着建议、健康提醒、安全提示、平安祝福等。\n"
                "4.不要输出解释或者无关内容。\n"
                "- 第三步，请直接输出天气提醒。"
            )
            stream_generator = await generate_response(prompt)
            return StreamingResponse(stream_generator, media_type="text/plain; charset=utf-8")
        else:
            return StreamingResponse(iter(["未找到该会员的信息。"]), media_type="text/plain; charset=utf-8")
    
    elif request.mode == "2":  # 节日祝福
        code = request.code.strip()
        member = await query_member_info(db_pool, code)

        if member:
            name, sex, birthday = member
            birthday = datetime.strptime(birthday, "%Y%m%d")
            current_date = datetime.strptime(current_date, "%Y%m%d")
            age = current_date.year - birthday.year - ((current_date.month, current_date.day) < (birthday.month, birthday.day))
            member_info = f"姓名：{name}，性别：{sex}，年龄：{age}"
            prompt = (
                "你是节日祝福生成助手，请根据节日信息生成一段节日祝福。\n"
                "- 第一步，理解节日信息。\n"
                f"1.顾客信息：{member_info}\n"
                f"2.节日名称：{request.message}\n"
                f"3.当前日期：{current_date}\n"
                "- 第二步，理解生成规则。\n"
                "1.可以结合节日风格添加emoji表情符号。\n"
                "2.节日祝福可以结合顾客信息、季节特点、节日风俗等。\n"
                "3.如果节日名称为空，请输出离当前日期最近的节日祝福，可以包含小众节日。\n"
                "4.不要输出解释或者无关内容。\n"
                "- 第三步，请直接输出节日祝福。"
            )
            stream_generator = await generate_response(prompt)
            return StreamingResponse(stream_generator, media_type="text/plain; charset=utf-8")
        else:
            return StreamingResponse(iter(["未找到该会员的信息。"]), media_type="text/plain; charset=utf-8")

    elif request.mode == "3":  # 商品匹配
        code = request.code.strip()
        member = await query_member_info(db_pool, code)

        if member:
            name, sex, birthday = member
            birthday = datetime.strptime(birthday, "%Y%m%d")
            current_date = datetime.strptime(current_date, "%Y%m%d")
            age = current_date.year - birthday.year - ((current_date.month, current_date.day) < (birthday.month, birthday.day))
            member_info = f"{sex},{age}岁,{request.message}"
            result = await query(member_info)
            prompt = (
                "你是商品推荐助手，请向导购推荐适合顾客的商品方向，如类别、颜色、厚薄、风格等。\n"
                f"1.顾客信息：{name},{member_info}\n"
                f"2.相似记录：{result}\n"
                f"3.当前日期：{current_date}\n"
                "4.品牌信息：雅戈尔集团旗下品牌。"
            )
            stream_generator = await generate_reasoning_response(prompt)
            return StreamingResponse(stream_generator, media_type="text/plain; charset=utf-8")
        else:
            return StreamingResponse(iter(["未找到该会员的信息。"]), media_type="text/plain; charset=utf-8")
    else:
        return StreamingResponse(iter(["不支持的模式，请使用 '0'（生日）或 '1'（天气）或 '2'（节日）或 '3'（匹配）。"]), media_type="text/plain; charset=utf-8")

# 启动服务
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)

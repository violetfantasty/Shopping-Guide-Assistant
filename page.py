import gradio as gr 
import requests

API_URL = "http://localhost:8080/script"

def stream_query(mode, code, message):
    try:
        with requests.post(
            API_URL,
            json={"mode": mode, "code": code, "message": message},
            stream=True,
            timeout=500
        ) as response:
            if response.status_code == 200:
                text = ""
                for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                    if chunk:
                        text += chunk
                        yield text
            else:
                yield f"**请求失败**，状态码：{response.status_code}"
    except Exception as e:
        yield f"**请求出错**：{str(e)}"

def update_input_labels(mode):
    if mode == "0":
        return (
            gr.update(label="会员手机号（必填）", placeholder="请输入会员手机号"),
            gr.update(label="会员信息（非必填）", placeholder="可以补充会员喜好、职业等")
        )
    elif mode == "1":
        return (
            gr.update(label="门店编码（必填）", placeholder="请输入门店编码"),
            gr.update(label="附加信息（非必填）", placeholder="可以补充门店名称、电话等")
        )
    elif mode == "2":
        return (
            gr.update(label="会员手机号（必填）", placeholder="请输入会员手机号"),
            gr.update(label="节日名称（必填）", placeholder="请输入节日名称")
        )
    elif mode == "3":
        return (
            gr.update(label="会员手机号（必填）", placeholder="请输入会员手机号"),
            gr.update(label="会员信息（非必填）", placeholder="可以补充会员喜好、职业等")
        )
    else:
        return (
            gr.update(label="编码信息", placeholder="请输入相关编码"),
            gr.update(label="附加信息", placeholder="请输入补充说明")
        )

with gr.Blocks(title="导购助手") as demo:
    gr.Markdown("## 🎁 欢迎使用雅戈尔导购智能助手")

    mode_dropdown = gr.Dropdown(
        choices=[
            ("生日祝福 🎂", "0"),
            ("天气提醒 ☀️", "1"),
            ("节日祝福 🎉", "2"),
            ("商品匹配 🛍️", "3")
        ],
        value="0",
        label="请选择功能类别"
    )

    code_input = gr.Textbox(label="编码信息", placeholder="请先选择功能类别")
    message_input = gr.Textbox(label="附加信息", placeholder="请先选择功能类别")

    output_box = gr.Textbox(label="生成结果", lines=6)

    submit_btn = gr.Button("智能生成")

    submit_btn.click(
        fn=stream_query,
        inputs=[mode_dropdown, code_input, message_input],
        outputs=output_box
    )

    mode_dropdown.change(
        fn=update_input_labels,
        inputs=[mode_dropdown],
        outputs=[code_input, message_input]
    )

    demo.load(
        fn=update_input_labels,
        inputs=[mode_dropdown],
        outputs=[code_input, message_input]
    )

demo.launch(share=False)
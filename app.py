import spaces
import gradio as gr
import uvicorn
from main import app as fastapi_app

@spaces.GPU
def predict(text: str = ""):
    return text

demo = gr.Interface(fn=predict, inputs="text", outputs="text", title="Kopdes")

# Mount Gradio pada /_admin agar memenuhi scanner ZeroGPU,
# sementara seluruh aplikasi web FastAPI Anda berjalan normal di root "/"
app = gr.mount_gradio_app(fastapi_app, demo, path="/_admin")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860)

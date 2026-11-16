import gradio as gr
import uvicorn
from main import app as fastapi_app

# Mount Gradio pada /_admin agar kompatibel dengan Hugging Face Gradio SDK,
# sementara seluruh aplikasi web FastAPI Anda berjalan normal di root "/"
app = gr.mount_gradio_app(fastapi_app, gr.Blocks(title="Kopdes"), path="/_admin")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860)

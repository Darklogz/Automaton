from fastapi import FastAPI

app = FastAPI(title="Núcleo IA")


@app.get("/health")
def health():
    return {"estado": "ok"}
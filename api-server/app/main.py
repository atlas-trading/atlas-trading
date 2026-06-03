from fastapi import FastAPI

app = FastAPI(title="Atlas Trading Admin")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

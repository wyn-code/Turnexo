from fastapi import FastAPI

app = FastAPI(title="Turnexo")


@app.get("/", summary="Hello World check")
def read_root():
    return {"message": "Hello World"}


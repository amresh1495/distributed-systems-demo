from fastapi import FastAPI

app = FastAPI(
    title="Inventory Service",
    description="Manages product stock levels.",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"message": "Inventory Service is running"}

# Further endpoints will be added here.

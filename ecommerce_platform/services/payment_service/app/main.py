from fastapi import FastAPI

app = FastAPI(
    title="Payment Service",
    description="Manages payment processing (mocked).",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"message": "Payment Service is running"}

# Further endpoints will be added here.

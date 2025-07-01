from fastapi import FastAPI

app = FastAPI(
    title="Order Service",
    description="Manages order creation, updates, and status.",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"message": "Order Service is running"}

# Further endpoints will be added here.

from fastapi import FastAPI

app = FastAPI(
    title="Notification Service",
    description="Manages sending notifications (email/SMS - mocked).",
    version="0.1.0"
)

@app.get("/")
async def root():
    return {"message": "Notification Service is running"}

# Further endpoints will be added here.

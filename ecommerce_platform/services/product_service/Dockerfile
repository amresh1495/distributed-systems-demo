# Start with a Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the common requirements file first to leverage Docker cache
# Path is relative to the build context (services/product_service/)
COPY ../../requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY ./app /app/app

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

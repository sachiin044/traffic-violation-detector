FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (required for OpenCV and PaddleOCR)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port Hugging Face Spaces uses
EXPOSE 7860

# Command to run the FastAPI server on port 7860
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]

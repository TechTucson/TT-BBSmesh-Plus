FROM python:3.11-slim

RUN apt update && apt install -y \
 rtl-sdr sox ffmpeg multimon-ng build-essential \
 && rm -rf /var/lib/apt/lists/*

# Install CPU-only torch first
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Then whisper
RUN pip install --no-cache-dir openai-whisper

WORKDIR /app
COPY sdr.py .

CMD ["python","sdr.py"]

FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    rtl-sdr \
    sox \
    wsjtx \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
COPY app.py .

RUN mkdir -p /data /tmp/wspr

ENV WSPR_FREQUENCY=14.0971M \
    RTL_SAMPLE_RATE=12000 \
    RTL_GAIN=auto \
    RTL_PPM=0 \
    WSPR_CYCLE_SECONDS=114 \
    API_HOST=0.0.0.0 \
    API_PORT=8082 \
    DB_PATH=/data/wspr.db

EXPOSE 8082
VOLUME ["/data"]
CMD ["python3", "/app/app.py"]

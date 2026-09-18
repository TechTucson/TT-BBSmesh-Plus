FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    git \
    build-essential \
    cmake \
    libasound2-dev \
    libudev-dev \
    libusb-1.0-0-dev \
    libhamlib-dev \
    libgps-dev \
    python3 \
    python3-pip \
    rtl-sdr \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 https://github.com/wb2osz/direwolf.git /tmp/direwolf \
    && cd /tmp/direwolf \
    && mkdir build \
    && cd build \
    && cmake .. \
    && make -j"$(nproc)" \
    && make install \
    && rm -rf /tmp/direwolf

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY app.py .
COPY direwolf.conf .

RUN mkdir -p /data

ENV APRS_FREQUENCY=144.390M \
    RTL_SAMPLE_RATE=22050 \
    RTL_GAIN=auto \
    RTL_PPM=0 \
    API_HOST=0.0.0.0 \
    API_PORT=8080 \
    DB_PATH=/data/aprs.db

EXPOSE 8080
VOLUME ["/data"]

CMD ["python3", "/app/app.py"]

# TT-CW Receiver

Web-based HF CW/Morse receiver for an RTL-SDR Blog V3. The default frequency is **7.050 MHz** and the receiver uses the V3 Q-branch direct-sampling path.

## Hardware

- RTL-SDR Blog V3
- Appropriate 40-meter/HF antenna
- Linux Docker host with the RTL-SDR connected by USB

## Start

```bash
cd cw-receiver
docker compose up -d --build
docker logs -f tt-cw
```

Open `http://HOST-IP:8083`.

The UI shows receiver state, frequency, detected CW tone, approximate signal level, raw Morse, and decoded characters. Frequency can be changed from the browser.

## RTL-SDR test

Open `/api/rtl-test` or run:

```bash
docker exec tt-cw rtl_test -t
```

Only one application/container can normally own the RTL-SDR at a time. Stop another SDR service before starting TT-CW if it uses the same dongle.

## Configuration

Defaults in `docker-compose.yml`:

- `FREQUENCY=7050000`
- `SAMPLE_RATE=12000`
- `PPM=0`
- `RTL_DEVICE=0`
- `CW_TONE=700`
- `CW_WPM=18`

The receiver launches `rtl_fm` with USB demodulation and `-E direct2` (Q-branch direct sampling). This is intended for the RTL-SDR Blog V3 HF direct-sampling path.

## Decoder status

The included decoder is an initial real-time narrow-tone Morse decoder. It uses tone energy and Morse timing based on the configured WPM. Real-world CW has variable speed, fading, interference, and frequency offset, so adaptive tone tracking and automatic WPM estimation are logical next improvements after RF testing.

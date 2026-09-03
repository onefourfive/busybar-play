#!/usr/bin/env python3
# from https://github.com/rnadyrshin/busy-bar-http-api-examples-en/blob/main/clock-widget/clock-1.py
import argparse
import base64
import binascii
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from PIL import Image

LOGGER = logging.getLogger(__name__)

DEVICE_URL = "http://10.0.4.20"
APP_ID = "utc_clock"

SCREEN_WIDTH = 72
SCREEN_HEIGHT = 16

def log_request(response: requests.Response) -> None:
    request = response.request
    body = request.body
    if isinstance(body, bytes):
        body = body.decode("utf-8", errors="replace")

    LOGGER.debug(
        "HTTP request:\n%s %s\nHeaders: %s\nBody: %s",
        request.method,
        request.url,
        dict(request.headers),
        body,
    )


def capture_screen(output_path: str, display: int = 0) -> Path:
    """Capture a device display and save it as an image."""
    if display not in (0, 1):
        raise ValueError("display must be 0 (front) or 1 (back)")

    response = requests.get(
        f"{DEVICE_URL}/api/screen",
        params={"display": display},
        timeout=5,
    )
    log_request(response)
    response.raise_for_status()

    try:
        pixels = base64.b64decode(response.content.strip(), validate=True)
    except binascii.Error as exc:
        raise ValueError("screen response is not valid Base64 data") from exc

    expected_size = SCREEN_WIDTH * SCREEN_HEIGHT * 3
    if len(pixels) != expected_size:
        raise ValueError(
            f"expected {expected_size} RGB bytes, received {len(pixels)}"
        )

    path = Path(output_path)
    Image.frombytes("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), pixels).save(path)
    return path


def draw_clock():
    now = datetime.now(timezone.utc)

    date_text = now.strftime("%Y.%m.%d")
    time_text = now.strftime("%H:%M UTC")

    payload = {
        "application_name": APP_ID,
        "led_notification_color": "#FF0000FF",
        "elements": [
            {
                "id": "date",
                "type": "text",
                "text": date_text,
                "align": "top_mid",
                "x": SCREEN_WIDTH // 2,
                "y": -2,
                "font": "small",
                "color": "#FFFFFFFF",
                "timeout": 10,
            },
            {
                "id": "time",
                "type": "text",
                "text": time_text,
                "align": "top_mid",
                "x": SCREEN_WIDTH // 2,
                "y": 4,
                "font": "large",
                "color": "#FFFFFFFF",
                "timeout": 10,
            },
        ],
    }

    response = requests.post(
        f"{DEVICE_URL}/api/display/draw",
        json=payload,
        timeout=5,
    )
    log_request(response)
    response.raise_for_status()


def main() -> int:
    parser = argparse.ArgumentParser(description="Display a UTC clock on the LED screen.")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print each outgoing HTTP request",
    )
    parser.add_argument(
        "--capture-screen",
        metavar="PATH",
        help="draw once, save a PNG capture of the front screen, and exit",
    )
    args = parser.parse_args()

    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s")
    LOGGER.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    if args.capture_screen:
        try:
            draw_clock()
            time.sleep(0.1)
            path = capture_screen(args.capture_screen)
            LOGGER.info("Saved screen capture to %s", path)
            return 0
        except (OSError, ValueError, requests.RequestException) as exc:
            LOGGER.error("Failed to capture screen: %s", exc)
            return 1

    try:
        while True:
            try:
                draw_clock()
            except requests.RequestException as exc:
                LOGGER.error("Failed to update display: %s", exc)

            # Update shortly after each UTC second rolls over.
            time.sleep(1)
    except KeyboardInterrupt:
        LOGGER.info("Stopped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

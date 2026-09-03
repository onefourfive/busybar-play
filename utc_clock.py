#!/usr/bin/env python3
# from https://github.com/rnadyrshin/busy-bar-http-api-examples-en/blob/main/clock-widget/clock-1.py
import argparse
import logging
import time
from datetime import datetime, timezone

import requests

LOGGER = logging.getLogger(__name__)

DEVICE_URL = "http://10.0.4.20"
APP_ID = "utc_clock"

SCREEN_WIDTH = 72

# Assumed character advances, including spacing.
# Adjust these if the device's built-in font metrics differ.
SMALL_CHAR_WIDTH = 4
MEDIUM_CHAR_WIDTH = 5
BIG_CHAR_WIDTH = 7


def centered_x(text: str, char_width: int) -> int:
    text_width = len(text) * char_width
    return max(0, (SCREEN_WIDTH - text_width) // 2)


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


def draw_clock():
    now = datetime.now(timezone.utc)

    date_text = now.strftime("%Y.%m.%d")
    time_text = now.strftime("%H:%M")

    payload = {
        "application_name": APP_ID,
        "led_notification_color": "#FF0000FF",
        "elements": [
            {
                "id": "date",
                "timeout": 2,
                # "align": "center",
                "type": "text",
                "text": date_text,
                "x": centered_x(date_text, SMALL_CHAR_WIDTH),
                "y": 0,
                "font": "small",
                "color": "#FFFFFFFF",
                "width": SCREEN_WIDTH,
                "scroll_rate": 0,
                "timeout": 10
            },
            {
                "id": "time",
                "timeout": 2,
                # "align": "center",
                "type": "text",
                "text": time_text + " UTC",
                "x": centered_x(time_text, BIG_CHAR_WIDTH),
                "y": 6,
                "font": "large",
                "color": "#FFFFFFFF",
                "width": SCREEN_WIDTH,
                "scroll_rate": 0,
                "timeout": 10
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


def main():
    parser = argparse.ArgumentParser(description="Display a UTC clock on the LED screen.")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print each outgoing HTTP request",
    )
    args = parser.parse_args()

    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s")
    LOGGER.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    while True:
        try:
            draw_clock()
        except requests.RequestException as exc:
            LOGGER.error("Failed to update display: %s", exc)

        # Update shortly after each UTC second rolls over.
        time.sleep(1)


if __name__ == "__main__":
    main()

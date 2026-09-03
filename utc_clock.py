#!/usr/bin/env python3
# from https://github.com/rnadyrshin/busy-bar-http-api-examples-en/blob/main/clock-widget/clock-1.py
import argparse
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from busylib import BusyBar, exceptions, types

LOGGER = logging.getLogger(__name__)

DEVICE_ADDRESS = "10.0.4.20"
APP_ID = "utc_clock"

SCREEN_WIDTH = 72
DEFAULT_TIMEZONE_INTERVAL = 10.0
TIME_GROUP_X_POSITIONS = (21, 35, 49)
COLON_X_POSITIONS = (28, 42)
TEXT_COLOR = "#FFFFFFFF"
DIM_COLON_COLOR = "#666666FF"
TIMEZONES = (
    ZoneInfo("Australia/Adelaide"),
    ZoneInfo("Europe/Berlin"),
    ZoneInfo("America/Los_Angeles"),
    timezone.utc,
)


def positive_float(value: str) -> float:
    """Parse a positive floating-point command-line value."""
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def capture_screen(
    busy_bar: BusyBar,
    output_path: str,
    display: types.DisplayName = types.DisplayName.FRONT,
) -> Path:
    """Capture a device display and save it as a PNG image."""
    path = Path(output_path)
    path.write_bytes(busy_bar.frame(display).to_png())
    return path


def draw_clock(
    busy_bar: BusyBar,
    display_timezone: ZoneInfo | timezone,
    *,
    colons_bright: bool | None = None,
    clear_before_draw: bool = False,
) -> None:
    now = datetime.now(display_timezone)
    if colons_bright is None:
        colons_bright = now.microsecond < 500_000

    date_text = now.strftime("%Y.%m.%d")
    time_parts = now.strftime("%H:%M:%S").split(":")
    timezone_text = now.strftime("%Z")
    colon_color = TEXT_COLOR if colons_bright else DIM_COLON_COLOR

    busy_bar.display_draw(
        types.DisplayElements(
            application_name=APP_ID,
            led_notification_color="#FF0000FF",
            elements=[
                types.TextElement(
                    id="date",
                    text=date_text,
                    align="top_left",
                    x=1,
                    y=-2,
                    font="small",
                    color=TEXT_COLOR,
                    timeout=10,
                ),
                *[
                    types.TextElement(
                        id=f"time_{part_name}",
                        text=part_text,
                        align="top_mid",
                        x=x,
                        y=4,
                        font="large",
                        color=TEXT_COLOR,
                        timeout=10,
                    )
                    for part_name, part_text, x in zip(
                        ("hours", "minutes", "seconds"),
                        time_parts,
                        TIME_GROUP_X_POSITIONS,
                    )
                ],
                *[
                    types.TextElement(
                        id=f"time_colon_{index}",
                        text=":",
                        align="top_mid",
                        x=x,
                        y=4,
                        font="large",
                        color=colon_color,
                        timeout=10,
                    )
                    for index, x in enumerate(COLON_X_POSITIONS)
                ],
                types.TextElement(
                    id="timezone",
                    text=timezone_text,
                    align="top_right",
                    x=SCREEN_WIDTH - 1,
                    y=-2,
                    font="small",
                    color=TEXT_COLOR,
                    timeout=10,
                ),
            ],
        ),
        clear_before_draw=clear_before_draw,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Display a clock that cycles through multiple timezones."
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print each outgoing HTTP request",
    )
    parser.add_argument(
        "--timezone-interval",
        type=positive_float,
        default=DEFAULT_TIMEZONE_INTERVAL,
        metavar="SECONDS",
        help=(
            "seconds to show each timezone before cycling "
            f"(default: {DEFAULT_TIMEZONE_INTERVAL:g})"
        ),
    )
    parser.add_argument(
        "--capture-screen",
        metavar="PATH",
        help="draw once, save a PNG capture of the front screen, and exit",
    )
    args = parser.parse_args()

    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s")
    LOGGER.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    logging.getLogger("busylib").setLevel(
        logging.DEBUG if args.verbose else logging.WARNING
    )

    with BusyBar(DEVICE_ADDRESS) as busy_bar:
        if args.capture_screen:
            try:
                draw_clock(busy_bar, TIMEZONES[0], clear_before_draw=True)
                time.sleep(0.1)
                path = capture_screen(busy_bar, args.capture_screen)
                LOGGER.info("Saved screen capture to %s", path)
                return 0
            except (OSError, ValueError, exceptions.BusyBarError) as exc:
                LOGGER.error("Failed to capture screen: %s", exc)
                return 1

        try:
            cycle_started = time.monotonic()
            first_draw = True
            while True:
                try:
                    elapsed = time.monotonic() - cycle_started
                    timezone_index = int(elapsed / args.timezone_interval) % len(
                        TIMEZONES
                    )
                    draw_clock(
                        busy_bar,
                        TIMEZONES[timezone_index],
                        clear_before_draw=first_draw,
                    )
                    first_draw = False
                except exceptions.BusyBarError as exc:
                    LOGGER.error("Failed to update display: %s", exc)

                # Update shortly after each half-second pulse boundary.
                now = time.time()
                time.sleep(0.5 - (now % 0.5) + 0.01)
        except KeyboardInterrupt:
            LOGGER.info("Stopped.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

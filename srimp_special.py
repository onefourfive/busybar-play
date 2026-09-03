#!/usr/bin/env python3
"""Recreate the "JESUS SHRIMP SPECIAL" sign gag on a BUSY Bar."""

from __future__ import annotations

import argparse
import logging
import time

from busylib import BusyBar, exceptions, types


LOGGER = logging.getLogger(__name__)

DEVICE_ADDRESS = "10.0.4.20"
APP_ID = "srimp_special"
SCREEN_WIDTH = 72
SCREEN_HEIGHT = 16

VERSE = (
    "         " 
    "Jesus answered \"I am the way and the truth and the life. "
    "No one comes to the Father except through me.\""
)
SPECIAL = "    $6 SRIMP SPECIAL!!"

GREEN = "#00FF00FF"
YELLOW = "#FFFF00FF"
FAST_SCROLL_RATE = 3000
DRAMATIC_SCROLL_RATE = 640
VERSE_SECONDS = 10
SPECIAL_SECONDS = 8
FLASH_SECONDS = 0.3
FLASH_STEPS = 7
BEAT_SECONDS = 0.08
LOOP_PAUSE_SECONDS = 0.35


def nonnegative_float(value: str) -> float:
    """Parse a non-negative floating-point command-line value."""
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def positive_int(value: str) -> int:
    """Parse a positive integer command-line value."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def draw_marquee(
    busy_bar: BusyBar,
    *,
    element_id: str,
    text: str,
    font: types.DisplayFontName,
    color: str,
    y: int,
    scroll_rate: int,
) -> None:
    """Replace the front display with one edge-to-edge scrolling message."""
    busy_bar.display_draw(
        types.DisplayElements(
            application_name=APP_ID,
            elements=[
                types.TextElement(
                    id=element_id,
                    text=text,
                    font=font,
                    color=color,
                    align="top_left",
                    x=0,
                    y=y,
                    width=SCREEN_WIDTH,
                    scroll_rate=scroll_rate,
                    scroll_start_delay=0,
                    scroll_repeat_delay=0,
                )
            ],
        ),
        clear_before_draw=True,
    )


def play_yellow_flash(
    busy_bar: BusyBar,
    *,
    duration: float = FLASH_SECONDS,
    steps: int = FLASH_STEPS,
) -> None:
    """Fill the display yellow, then quickly fade it to black."""
    if duration <= 0:
        return

    frame_seconds = duration / steps
    for step in range(steps):
        brightness = round(255 * (1 - step / (steps - 1)))
        color = f"#{brightness:02X}{brightness:02X}00FF"
        busy_bar.display_draw(
            types.DisplayElements(
                application_name=APP_ID,
                elements=[
                    types.RectangleElement(
                        id="yellow_flash",
                        x=0,
                        y=0,
                        width=SCREEN_WIDTH,
                        height=SCREEN_HEIGHT,
                        fill="solid",
                        fill_colors=[color],
                        border_width=0,
                    )
                ],
            ),
            clear_before_draw=False,
        )
        time.sleep(frame_seconds)


def play_once(
    busy_bar: BusyBar,
    *,
    verse_rate: int = FAST_SCROLL_RATE,
    verse_seconds: float = VERSE_SECONDS,
    flash_seconds: float = FLASH_SECONDS,
    beat_seconds: float = BEAT_SECONDS,
    special_rate: int = DRAMATIC_SCROLL_RATE,
    special_seconds: float = SPECIAL_SECONDS,
) -> None:
    """Play one setup-and-punchline cycle."""
    draw_marquee(
        busy_bar,
        element_id="verse",
        text=VERSE,
        font="condensed",
        color=GREEN,
        y=4,
        scroll_rate=verse_rate,
    )
    time.sleep(verse_seconds)

    play_yellow_flash(busy_bar, duration=flash_seconds)

    # A tiny blank beat separates the flash from the yellow punchline.
    busy_bar.display_clear(application_name=APP_ID)
    time.sleep(beat_seconds)

    draw_marquee(
        busy_bar,
        element_id="special",
        text=SPECIAL,
        font="extra_large",
        color=YELLOW,
        y=3,
        scroll_rate=special_rate,
    )
    time.sleep(special_seconds)
    busy_bar.display_clear(application_name=APP_ID)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reference a very funny video on a BUSY bar"
    )
    parser.add_argument(
        "address",
        nargs="?",
        default=DEVICE_ADDRESS,
        help=f"BUSY Bar address (default: {DEVICE_ADDRESS})",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="play once and exit instead of looping",
    )
    parser.add_argument(
        "--verse-rate",
        type=positive_int,
        default=FAST_SCROLL_RATE,
        metavar="PX_PER_SECOND",
        help=f"green verse scroll speed (default: {FAST_SCROLL_RATE})",
    )
    parser.add_argument(
        "--special-rate",
        type=positive_int,
        default=DRAMATIC_SCROLL_RATE,
        metavar="PX_PER_SECOND",
        help=f"yellow punchline scroll speed (default: {DRAMATIC_SCROLL_RATE})",
    )
    parser.add_argument(
        "--verse-seconds",
        type=nonnegative_float,
        default=VERSE_SECONDS,
        metavar="SECONDS",
        help=f"time before the punchline (default: {VERSE_SECONDS:g})",
    )
    parser.add_argument(
        "--flash-seconds",
        type=nonnegative_float,
        default=FLASH_SECONDS,
        metavar="SECONDS",
        help=f"duration of the yellow flash and fade (default: {FLASH_SECONDS:g})",
    )
    parser.add_argument(
        "--special-seconds",
        type=nonnegative_float,
        default=SPECIAL_SECONDS,
        metavar="SECONDS",
        help=f"time to show the punchline (default: {SPECIAL_SECONDS:g})",
    )
    parser.add_argument(
        "--beat-seconds",
        type=nonnegative_float,
        default=BEAT_SECONDS,
        metavar="SECONDS",
        help=f"blank dramatic beat between messages (default: {BEAT_SECONDS:g})",
    )
    parser.add_argument(
        "--loop-pause",
        type=nonnegative_float,
        default=LOOP_PAUSE_SECONDS,
        metavar="SECONDS",
        help=f"pause between loops (default: {LOOP_PAUSE_SECONDS:g})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="print outgoing busylib requests",
    )
    args = parser.parse_args()

    logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("busylib").setLevel(
        logging.DEBUG if args.verbose else logging.WARNING
    )

    try:
        with BusyBar(args.address) as busy_bar:
            while True:
                play_once(
                    busy_bar,
                    verse_rate=args.verse_rate,
                    verse_seconds=args.verse_seconds,
                    flash_seconds=args.flash_seconds,
                    beat_seconds=args.beat_seconds,
                    special_rate=args.special_rate,
                    special_seconds=args.special_seconds,
                )
                if args.once:
                    return 0
                busy_bar.display_clear(application_name=APP_ID)
                time.sleep(args.loop_pause)
    except KeyboardInterrupt:
        LOGGER.info("Stopped")
        return 0
    except (OSError, ValueError, exceptions.BusyBarError) as exc:
        LOGGER.error("BUSY Bar error: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

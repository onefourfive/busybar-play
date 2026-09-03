#!/usr/bin/env python3
# from https://github.com/rnadyrshin/busy-bar-http-api-examples-en/blob/main/clock-widget/clock-1.py
import argparse
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from busylib import BusyBar, converter, exceptions, types

LOGGER = logging.getLogger(__name__)

DEVICE_ADDRESS = "10.0.4.20"
APP_ID = "utc_clock"

SCREEN_WIDTH = 72
DEFAULT_TIMEZONE_INTERVAL = 10.0
TIME_GROUP_X_POSITIONS = (21, 35, 49)
COLON_X_POSITIONS = (28, 42)
FLAGGED_TIME_GROUP_X_POSITIONS = (30, 44, 58)
FLAGGED_COLON_X_POSITIONS = (37, 51)
TEXT_COLOR = "#FFFFFFFF"
DIM_COLON_COLOR = "#666666FF"
FLAG_X = 4
FLAG_Y = 4
TIMEZONE_BACKGROUND_X = 53
TIMEZONE_BACKGROUND_WIDTH = SCREEN_WIDTH - TIMEZONE_BACKGROUND_X
ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "flags"


@dataclass(frozen=True)
class TimezoneConfig:
    """Visual and timezone settings for one stop in the clock cycle."""

    zone: str
    background_color: str
    text_color: str
    flag_png: Path | None = None

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.zone)


TIMEZONES = (
    TimezoneConfig(
        zone="Australia/Adelaide",
        background_color="#012169FF",
        text_color="#FFFFFFFF",
        flag_png=ASSETS_DIR / "au.png",
    ),
    TimezoneConfig(
        zone="Europe/Berlin",
        background_color="#FFCE00FF",
        text_color="#000000FF",
        flag_png=ASSETS_DIR / "de.png",
    ),
    TimezoneConfig(
        zone="America/Los_Angeles",
        background_color="#3C3B6EFF",
        text_color="#FFFFFFFF",
        flag_png=ASSETS_DIR / "us.png",
    ),
    TimezoneConfig(
        zone="UTC",
        background_color="#009EDBFF",
        text_color="#FFFFFFFF",
    ),
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


def upload_flag_assets(busy_bar: BusyBar) -> dict[Path, str]:
    """Convert and upload each configured flag, returning its device filename."""
    uploaded: dict[Path, str] = {}
    for timezone_config in TIMEZONES:
        flag_path = timezone_config.flag_png
        if flag_path is None or flag_path in uploaded:
            continue

        filename, payload = converter.convert_for_storage(
            flag_path.name,
            flag_path.read_bytes(),
        )
        busy_bar.assets_upload(APP_ID, filename, payload)
        uploaded[flag_path] = filename

    return uploaded


def flag_asset_for(
    timezone_config: TimezoneConfig,
    flag_assets: dict[Path, str],
) -> str | None:
    """Return the uploaded filename for a timezone's optional flag."""
    if timezone_config.flag_png is None:
        return None
    return flag_assets.get(timezone_config.flag_png)


def draw_clock(
    busy_bar: BusyBar,
    timezone_config: TimezoneConfig,
    *,
    flag_asset: str | None = None,
    colons_bright: bool | None = None,
    clear_before_draw: bool = False,
) -> None:
    now = datetime.now(timezone_config.tzinfo)
    if colons_bright is None:
        colons_bright = now.microsecond < 500_000

    date_text = now.strftime("%Y.%m.%d")
    time_parts = now.strftime("%H:%M:%S").split(":")
    timezone_text = now.strftime("%Z")
    colon_color = TEXT_COLOR if colons_bright else DIM_COLON_COLOR
    time_group_x_positions = (
        FLAGGED_TIME_GROUP_X_POSITIONS if flag_asset else TIME_GROUP_X_POSITIONS
    )
    colon_x_positions = (
        FLAGGED_COLON_X_POSITIONS if flag_asset else COLON_X_POSITIONS
    )

    busy_bar.display_draw(
        types.DisplayElements(
            application_name=APP_ID,
            # led_notification_color="#FF0000FF",
            elements=[
                types.RectangleElement(
                    id="timezone_background",
                    x=TIMEZONE_BACKGROUND_X,
                    y=0,
                    width=TIMEZONE_BACKGROUND_WIDTH,
                    height=5,
                    fill="solid",
                    fill_colors=[timezone_config.background_color],
                    border_width=0,
                    timeout=10,
                ),
                *(
                    [
                        types.ImageElement(
                            id="flag",
                            path=flag_asset,
                            align="top_left",
                            x=FLAG_X,
                            y=FLAG_Y,
                            timeout=10,
                        )
                    ]
                    if flag_asset
                    else []
                ),
                types.TextElement(
                    id="date",
                    text=date_text,
                    align="top_left",
                    x=1,
                    y=-1,
                    font="tiny",
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
                        time_group_x_positions,
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
                    for index, x in enumerate(colon_x_positions)
                ],
                types.TextElement(
                    id="timezone",
                    text=timezone_text,
                    align="top_right",
                    x=SCREEN_WIDTH - 1,
                    y=-1,
                    font="tiny",
                    color=timezone_config.text_color,
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
        try:
            flag_assets = upload_flag_assets(busy_bar)
        except (OSError, ValueError, exceptions.BusyBarError) as exc:
            LOGGER.error("Failed to upload flag assets: %s", exc)
            return 1

        if args.capture_screen:
            try:
                timezone_config = TIMEZONES[0]
                draw_clock(
                    busy_bar,
                    timezone_config,
                    flag_asset=flag_asset_for(timezone_config, flag_assets),
                    clear_before_draw=True,
                )
                time.sleep(0.1)
                path = capture_screen(busy_bar, args.capture_screen)
                LOGGER.info("Saved screen capture to %s", path)
                return 0
            except (OSError, ValueError, exceptions.BusyBarError) as exc:
                LOGGER.error("Failed to capture screen: %s", exc)
                return 1

        try:
            cycle_started = time.monotonic()
            previous_timezone_index: int | None = None
            while True:
                try:
                    elapsed = time.monotonic() - cycle_started
                    timezone_index = int(elapsed / args.timezone_interval) % len(
                        TIMEZONES
                    )
                    draw_clock(
                        busy_bar,
                        TIMEZONES[timezone_index],
                        flag_asset=flag_asset_for(
                            TIMEZONES[timezone_index],
                            flag_assets,
                        ),
                        clear_before_draw=timezone_index
                        != previous_timezone_index,
                    )
                    previous_timezone_index = timezone_index
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

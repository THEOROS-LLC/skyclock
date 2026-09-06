#!/usr/bin/env python3
"""Claude Code statusline: elected greeting + Moon phase glyph + zodiac position.
Reads session JSON on stdin (ignored), prints one line to stdout."""
import os, sys, json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from skyfield.api import Loader, load_file
from skyfield.framelib import ecliptic_frame

VS15 = "\uFE0E"
SIGN_GLYPH = [chr(c) + VS15 for c in range(0x2648, 0x2654)]
SIGN_NAME = "Aries Taurus Gemini Cancer Leo Virgo Libra Scorpio Sagittarius Capricorn Aquarius Pisces".split()

# Moon glyph sets — elect via SKYCLOCK_MOON_SET
MOON_SETS = {
    # colour emoji, always emoji-presentation (font supplies the colour)
    "emoji": ["\U0001F311", "\U0001F312", "\U0001F313", "\U0001F314",
              "\U0001F315", "\U0001F316", "\U0001F317", "\U0001F318"],
    # same, with VS15 appended — may or may not force text presentation
    "emoji_text": [c + VS15 for c in ["\U0001F311", "\U0001F312", "\U0001F313",
                   "\U0001F314", "\U0001F315", "\U0001F316", "\U0001F317",
                   "\U0001F318"]],
    # geometric, never emoji; waning crescent/gibbous approximated
    "geo": ["\u25CB", "\u25D4", "\u25D7", "\u25D5",
            "\u25CF", "\u25D5", "\u25D6", "\u25D4"],
}

GREETINGS = {
    "new": ["Dark moon, clean slate.", "Nothing showing yet.", "The seed hour."],
    "waxing": ["Light is gathering.", "Building toward something.", "On the way up."],
    "full": ["Everything lit.", "Full light, no shadow.", "The whole face showing."],
    "waning": ["Letting go of light.", "Releasing.", "Winding down toward dark."],
}

def sky():
    D = os.path.expanduser(os.environ.get("SKYCLOCK_DATA_DIR", "~/.skyclock"))
    L = Loader(D, verbose=False)
    ts = L.timescale()
    p = os.environ.get("SKYCLOCK_EPHEMERIS", "")
    E = load_file(os.path.expanduser(p)) if p else L("de440s.bsp")
    ea, t = E["earth"], ts.from_datetime(datetime.now(timezone.utc))
    def lon(k):
        _, l, _ = ea.at(t).observe(E[k]).apparent().frame_latlon(ecliptic_frame)
        return l.degrees % 360.0
    return lon("moon"), (lon("moon") - lon("sun")) % 360

def render(color=True):
    ml, el = sky()
    i = int(ml // 30) % 12
    deg = int(ml % 30)
    mins = int(round((ml % 30 - deg) * 60))
    if mins == 60:
        mins, deg = 0, deg + 1
    mset = MOON_SETS.get(os.environ.get("SKYCLOCK_MOON_SET", "emoji"), MOON_SETS["emoji"])
    moon = mset[int(((el + 22.5) % 360) // 45)]
    band = "new" if el < 22.5 or el >= 337.5 else \
           "waxing" if el < 157.5 else "full" if el < 202.5 else "waning"
    tz = os.environ.get("SKYCLOCK_TZ")
    now = datetime.now(ZoneInfo(tz)) if tz else datetime.now().astimezone()
    greet = GREETINGS[band][(now.timetuple().tm_yday + now.hour) % 3]
    pos = f"{moon}  {SIGN_GLYPH[i]} {deg}\u00b0{mins:02d}\u2032"
    clock = now.strftime("%-I:%M %p")
    if color:
        return f"\033[38;5;223m{pos}\033[0m"
    return pos

if __name__ == "__main__":
    try:
        sys.stdin.read()
    except Exception:
        pass
    try:
        print(render())
    except Exception as e:
        print(f"sky: {e}", file=sys.stderr)
        sys.exit(1)

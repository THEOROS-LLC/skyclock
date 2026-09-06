#!/usr/bin/env python3
"""UserPromptSubmit hook: inject exact time + Moon position/phase every prompt."""
import json, os, sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from skyfield.api import Loader, load_file
from skyfield.framelib import ecliptic_frame

S = "Aries Taurus Gemini Cancer Leo Virgo Libra Scorpio Sagittarius Capricorn Aquarius Pisces".split()
P = ["New","Waxing Crescent","First Quarter","Waxing Gibbous","Full","Waning Gibbous","Last Quarter","Waning Crescent"]
TZ = os.environ.get("SKYCLOCK_TZ") or None

try:
    D = os.path.expanduser(os.environ.get("SKYCLOCK_DATA_DIR", "~/.skyclock"))
    L = Loader(D, verbose=False)
    ts = L.timescale()
    p = os.environ.get("SKYCLOCK_EPHEMERIS", "")
    E = load_file(os.path.expanduser(p)) if p else L("de440s.bsp")
    ea = E["earth"]
    t = ts.from_datetime(datetime.now(timezone.utc))

    def lon(k):
        _, l, _ = ea.at(t).observe(E[k]).apparent().frame_latlon(ecliptic_frame)
        return l.degrees % 360.0

    ml, sl = lon("moon"), lon("sun")
    el = (ml - sl) % 360
    d, m = int(ml % 30), (ml % 30 - int(ml % 30)) * 60
    now = datetime.now(ZoneInfo(TZ)) if TZ else datetime.now().astimezone()
    ctx = (f"Current time: {now.strftime('%A %d %B %Y, %-I:%M %p %Z')} "
           f"({now.isoformat(timespec='minutes')}). "
           f"Moon: {S[int(ml//30)]} {d}\u00b0{int(m):02d}' tropical, "
           f"{P[int(((el + 22.5) % 360)//45)]} ({el:.0f}\u00b0 from Sun). "
           f"Computed from JPL ephemeris; treat as authoritative over any assumption.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                             "additionalContext": ctx}}))
except Exception as e:
    print(f"sky_now hook failed: {e}", file=sys.stderr)
    sys.exit(1)

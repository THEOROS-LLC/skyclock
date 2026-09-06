import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
try:
    from mcp.server import MCPServer as F
except ImportError:
    from mcp.server.fastmcp import FastMCP as F
from skyfield import almanac
from skyfield.api import Loader, load_file, wgs84
from skyfield.framelib import ecliptic_frame

mcp = F("skyclock")
SIGNS = "Aries Taurus Gemini Cancer Leo Virgo Libra Scorpio Sagittarius Capricorn Aquarius Pisces".split()
BODIES = [("Sun","sun"),("Moon","moon"),("Mercury","mercury"),("Venus","venus"),("Mars","mars barycenter"),
          ("Jupiter","jupiter barycenter"),("Saturn","saturn barycenter"),("Uranus","uranus barycenter"),
          ("Neptune","neptune barycenter"),("Pluto","pluto barycenter")]
ASPECTS = [(0,"conjunction"),(60,"sextile"),(90,"square"),(120,"trine"),(180,"opposition")]
CHALDEAN = "Saturn Jupiter Mars Sun Venus Mercury Moon".split()
DAYRUL = {0:"Moon",1:"Mars",2:"Mercury",3:"Jupiter",4:"Venus",5:"Saturn",6:"Sun"}
PHASES = ["New Moon","Waxing Crescent","First Quarter","Waxing Gibbous","Full Moon",
          "Waning Gibbous","Last Quarter","Waning Crescent"]

D = os.path.expanduser(os.environ.get("SKYCLOCK_DATA_DIR","~/.skyclock"))
os.makedirs(D, exist_ok=True)
L = Loader(D, verbose=False)
_ts = L.timescale()
_p = os.environ.get("SKYCLOCK_EPHEMERIS","")
E = load_file(os.path.expanduser(_p)) if _p else L("de440s.bsp")
EA = E["earth"]

def _tz():
    n = os.environ.get("SKYCLOCK_TZ","")
    return ZoneInfo(n) if n else datetime.now().astimezone().tzinfo

def _obs():
    a, o = os.environ.get("SKYCLOCK_LAT",""), os.environ.get("SKYCLOCK_LON","")
    return wgs84.latlon(float(a), float(o)) if a and o else None

def _now():
    return _ts.from_datetime(datetime.now(timezone.utc))

def _lon(k, t):
    _, l, _ = EA.at(t).observe(E[k]).apparent().frame_latlon(ecliptic_frame)
    return l.degrees % 360.0

def _w(x):
    return ((x + 180.0) % 360.0) - 180.0

def _iso(t, tz):
    return t.utc_datetime().astimezone(tz).isoformat(timespec="seconds")

def _bis(f, a, b, n=40):
    fa = f(_ts.tt_jd(a))
    for _ in range(n):
        m = (a + b) / 2.0
        fm = f(_ts.tt_jd(m))
        if (fa < 0) == (fm < 0):
            a, fa = m, fm
        else:
            b = m
    return _ts.tt_jd((a + b) / 2.0)

def _cross(f, t0, t1, step):
    out, j0, j1 = [], t0.tt, t1.tt
    pj, pv = j0, f(_ts.tt_jd(j0))
    for i in range(1, int((j1 - j0) / step) + 2):
        j = min(j0 + i * step, j1)
        v = f(_ts.tt_jd(j))
        if (pv < 0) != (v < 0) and abs(pv) < 45 and abs(v) < 45:
            out.append(_bis(f, pj, j))
        pj, pv = j, v
        if j >= j1:
            break
    return out

@mcp.tool()
def get_current_sky() -> dict:
    """Exact current date/time and the live state of the sky. Call this whenever
    the current time, date, day of week, Moon phase/sign, retrogrades, or any
    planet's present zodiacal position is relevant - never guess these."""
    tz, t = _tz(), _now()
    nl = datetime.now(tz)
    t2 = _ts.tt_jd(t.tt + 1/24.0)
    pos = {}
    for nm, k in BODIES:
        d = _lon(k, t)
        p = {"sign": SIGNS[int(d//30) % 12], "degree": round(d % 30, 2), "longitude": round(d, 4)}
        if nm not in ("Sun", "Moon"):
            p["retrograde"] = bool(_w(_lon(k, t2) - d) < 0)
        pos[nm] = p
    el = (pos["Moon"]["longitude"] - pos["Sun"]["longitude"]) % 360
    out = {"local_time": nl.isoformat(timespec="seconds"),
           "utc_time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "weekday": nl.strftime("%A"), "timezone": str(tz),
           "julian_date_ut": round(t.ut1, 5),
           "moon_phase": {"name": PHASES[int(((el + 22.5) % 360)//45)],
                          "illumination": round(float(almanac.fraction_illuminated(E, "moon", t)), 3),
                          "sun_moon_angle": round(el, 1)},
           "positions": pos, "zodiac": "tropical"}
    if _obs() is not None:
        s = (t.gmst + float(os.environ["SKYCLOCK_LON"])/15.0) % 24.0
        h = int(s); m = int((s-h)*60)
        out["local_sidereal_time"] = f"{h:02d}:{m:02d}:{int(((s-h)*60-m)*60):02d}"
    return out


@mcp.tool()
def get_void_of_course() -> dict:
    """Whether the Moon is void-of-course right now: last exact aspect made,
    next aspect (if any) before the Moon leaves its sign, and when the void
    period begins/ends. Call for any electional or timing question."""
    tz, t = _tz(), _now()
    ln = _lon("moon", t)
    i = int(ln//30) % 12
    hi = ((i+1)*30.0) % 360.0 or 360.0
    fwd = _cross(lambda x: _w(_lon("moon", x) - hi), t, _ts.tt_jd(t.tt+3.2), 0.02)
    back = _cross(lambda x: _w(_lon("moon", x) - i*30.0), _ts.tt_jd(t.tt-3.2), t, 0.02)
    if not fwd:
        return {"error": "could not locate next lunar ingress"}
    ing = fwd[0]
    trad = os.environ.get("SKYCLOCK_VOC_SET","").lower() == "traditional"
    keys = [k for n, k in BODIES if n != "Moon"][:6 if trad else 99]
    ev = []
    for k in keys:
        for ang, an in ASPECTS:
            f = lambda x, k=k, ang=ang: _w(_lon("moon", x) - _lon(k, x) - ang)
            for tc in _cross(f, back[-1] if back else _ts.tt_jd(t.tt-3.2), ing, 0.02):
                ev.append((tc.tt, an, k.split()[0].capitalize(), tc))
    ev.sort(key=lambda e: e[0])
    past = [e for e in ev if e[0] <= t.tt]
    fut = [e for e in ev if e[0] > t.tt]
    out = {"moon_sign": SIGNS[i], "is_void": not fut,
           "sign_ingress": {"next_sign": SIGNS[(i+1) % 12], "at": _iso(ing, tz)},
           "aspect_set": "traditional (Sun-Saturn)" if trad else "modern (Sun-Pluto)"}
    if past:
        _, a, p, tc = past[-1]
        out["last_aspect"] = {"aspect": a, "planet": p, "at": _iso(tc, tz)}
    if fut:
        _, a, p, tc = fut[0]
        out["next_aspect"] = {"aspect": a, "planet": p, "at": _iso(tc, tz)}
    else:
        out["void_until"] = _iso(ing, tz)
        if past:
            out["void_since"] = out["last_aspect"]["at"]
    return out


@mcp.tool()
def get_planetary_hours() -> dict:
    """The current planetary hour (Chaldean order) for the configured location:
    hour ruler, day ruler, and when this hour ends. Requires SKYCLOCK_LAT/LON."""
    o = _obs()
    if o is None:
        return {"error": "set SKYCLOCK_LAT and SKYCLOCK_LON to enable planetary hours"}
    tz, t = _tz(), _now()
    tm, kd = almanac.find_discrete(_ts.tt_jd(t.tt-2), _ts.tt_jd(t.tt+2), almanac.sunrise_sunset(E, o))
    ris = [x for x, k in zip(tm, kd) if k == 1]
    sets = [x for x, k in zip(tm, kd) if k == 0]
    lr = max([x for x in ris if x.tt <= t.tt], key=lambda x: x.tt)
    nr = min([x for x in ris if x.tt > t.tt], key=lambda x: x.tt)
    ss = min([x for x in sets if x.tt > lr.tt], key=lambda x: x.tt)
    dr = DAYRUL[lr.utc_datetime().astimezone(tz).weekday()]
    if t.tt < ss.tt:
        sp = (ss.tt - lr.tt)/12.0
        n = int((t.tt - lr.tt)/sp)
        hs, hn = lr.tt + n*sp, n
    else:
        sp = (nr.tt - ss.tt)/12.0
        n = int((t.tt - ss.tt)/sp)
        hs, hn = ss.tt + n*sp, 12 + n
    return {"day_ruler": dr, "hour_ruler": CHALDEAN[(CHALDEAN.index(dr) + hn) % 7],
            "hour_number": hn + 1, "kind": "day" if hn < 12 else "night",
            "hour_begins": _iso(_ts.tt_jd(hs), tz), "hour_ends": _iso(_ts.tt_jd(hs+sp), tz),
            "sunrise": _iso(lr, tz), "sunset": _iso(ss, tz)}


if __name__ == "__main__":
    mcp.run()

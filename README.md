# skyclock (working name — final name pending election)

MCP server giving an LLM client exact current time + live sky state, computed
locally from NASA JPL ephemerides via Skyfield (MIT). No Swiss Ephemeris code;
no AGPL obligations. Three tools:

- `get_current_sky` — local/UTC time, weekday, Julian date, LST, tropical
  positions Sun–Pluto with retrograde flags, Moon phase + illumination
- `get_void_of_course` — is the Moon void now, last/next exact aspect, ingress
- `get_planetary_hours` — current hour ruler, day ruler, hour bounds (Chaldean)

## Install (elect the directory first)

```bash
cd <ELECTED_DIR>            # your election
python3 -m venv .venv
.venv/bin/pip install "mcp[cli]" skyfield
```

First run downloads `de440s.bsp` (~32 MB, one time, from ssd.jpl.nasa.gov)
into `SKYCLOCK_DATA_DIR` (default `~/.skyclock`). To stay fully offline,
pre-place any JPL `.bsp` and point `SKYCLOCK_EPHEMERIS` at it.

## Wire into Claude Code (recommended on the Linux boxes)

```bash
claude mcp add skyclock \
  -e SKYCLOCK_LAT=<LAT> -e SKYCLOCK_LON=<LON> -e SKYCLOCK_TZ=<IANA_TZ> \
  -- <ELECTED_DIR>/.venv/bin/python <ELECTED_DIR>/server.py
```

(Claude Desktop config wiring exists too, but per standing note the Linux
Desktop beta crashes on MCP entries — Claude Code CLI is the safe rail.
Docs: https://docs.claude.com/en/docs/claude-code/mcp)

## Elections (env vars)

| var | meaning | default |
|---|---|---|
| `SKYCLOCK_LAT` / `SKYCLOCK_LON` | observer coords (LST + planetary hours) | unset — those features report instructions |
| `SKYCLOCK_TZ` | IANA timezone | system tz |
| `SKYCLOCK_EPHEMERIS` | path to a `.bsp` kernel | auto-download de440s |
| `SKYCLOCK_DATA_DIR` | kernel/cache dir | `~/.skyclock` |
| `SKYCLOCK_VOC_SET` | `modern` (Sun–Pluto) or `traditional` (Sun–Saturn) | modern |

## Verification protocol (verify > assert)

Run `verify.py`, compare each line against astro.com's current planets page
and a trusted VoC table for the same minute. Log the diff once; then the
credit-line wording "verified against Swiss Ephemeris" is earned, not assumed.

MIT. Data: NASA JPL DE440s (public domain).

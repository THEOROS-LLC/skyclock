import asyncio, inspect, json, server
def call(f):
    r = f()
    return asyncio.run(r) if inspect.iscoroutine(r) else r
for n in ("get_current_sky", "get_void_of_course", "get_planetary_hours"):
    print(f"\n=== {n} ===")
    print(json.dumps(call(getattr(server, n)), indent=1, default=str))

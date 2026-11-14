# Meteo des tournois ATP du jour (6h, 12h, 16h UTC) -> meteo_tennis.json
import json, os, time, datetime as dt, urllib.request, urllib.parse, urllib.error

def get(url, tries=2):
    err = None
    for i in range(tries):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (400, 404): break
            time.sleep(3)
        except Exception as e:
            err = e; time.sleep(3)
    print("ERREUR", url[:100], err)
    return None


now = dt.datetime.now(dt.timezone.utc)
if now.hour in (6, 12, 16) and now.minute < 30:
    j = get("https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard") or {}
    villes = {}
    for e in j.get("events", []):
        v = (e.get("venue") or {}).get("displayName")
        if v: villes.setdefault(v, []).append(e.get("name"))
    cache = json.load(open("geo_tennis.json")) if os.path.exists("geo_tennis.json") else {}
    out = {}
    for v, tournois in villes.items():
        if v not in cache:
            ville, _, pays = v.partition(",")
            r = get("https://geocoding-api.open-meteo.com/v1/search?count=10&name=" + urllib.parse.quote(ville.strip()))
            res = (r or {}).get("results") or []
            ok = [x for x in res if pays.strip() and pays.strip().lower() in (x.get("country") or "").lower()]
            x = (ok or res or [None])[0]
            cache[v] = [round(x["latitude"], 3), round(x["longitude"], 3)] if x else None
        g = cache.get(v)
        if not g: continue
        r = get(f"https://api.open-meteo.com/v1/forecast?latitude={g[0]}&longitude={g[1]}"
                "&hourly=precipitation,wind_speed_10m,temperature_2m&timezone=GMT&forecast_days=3")
        if r and "hourly" in r:
            out[v] = dict(tournois=tournois, heures=r["hourly"]["time"], pluie=r["hourly"]["precipitation"],
                          vent_kmh=r["hourly"]["wind_speed_10m"], temp_c=r["hourly"]["temperature_2m"])

"""v2 (14/11) : pluie prévue au coup d'envoi pour TOUS les championnats suivis par le Carnet (+ coupes d'Europe).
1) ESPN : matchs des 7 prochains jours par championnat, avec la ville du stade ;
2) Open-Meteo géocodage (cache geo_cache.json, une seule fois par ville) puis prévision horaire (cache par ville) ;
3) écrit meteo_matchs.json : une ligne par match {t, lg, dom, ext, ville, pays, mm (pluie heure du match + heure suivante)}."""
import json, os, time, datetime as dt, urllib.request, urllib.parse, urllib.error
LIGUES = ("arg.1 aus.1 aut.1 bra.1 chi.1 chn.1 col.1 cze.1 den.1 ecu.1 eng.1 eng.2 fin.1 fra.1 fra.2 ger.1 ger.2 gre.1 "
          "ita.1 ita.2 jpn.1 mex.1 ned.1 nor.1 par.1 por.1 irl.1 rou.1 sco.1 esp.1 esp.2 swe.1 sui.1 "
          "tur.1 usa.1 uefa.champions uefa.europa uefa.europa.conf").split()
def get(url, tries=3):
    for i in range(tries):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=60).read())
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (400, 404): break
            time.sleep(3 + 5 * i)
        except Exception as e:
            err = e; time.sleep(3 + 5 * i)
    print("ERREUR", url[:90], err); return None
cache = json.load(open("geo_cache.json")) if os.path.exists("geo_cache.json") else {}
auj = dt.datetime.utcnow().date()
matchs = []
for lg in LIGUES:
    for k in range(7):
        d = (auj + dt.timedelta(days=k)).strftime("%Y%m%d")
        j = get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard?dates={d}")
        for e in (j or {}).get("events", []):
            c = e["competitions"][0]
            a = (c.get("venue") or {}).get("address") or {}
            eq = {x.get("homeAway"): (x.get("team") or {}).get("displayName") for x in c.get("competitors", [])}
            if a.get("city") and eq.get("home"):
                matchs.append(dict(t=e["date"], lg=lg, dom=eq.get("home"), ext=eq.get("away"), ville=a["city"], pays=a.get("country", "")))
        time.sleep(0.2)
print("matchs", len(matchs))
# géocodage (cache)
for v in sorted({(m["ville"], m["pays"]) for m in matchs}):
    cle = f"{v[0]}|{v[1]}"
    if cle in cache: continue
    nom = v[0].split(",")[0].strip()
    r = get("https://geocoding-api.open-meteo.com/v1/search?count=10&name=" + urllib.parse.quote(nom))
    res = (r or {}).get("results") or []
    ok = [x for x in res if v[1] and v[1].lower() in (x.get("country") or "").lower()]
    x = (ok or res or [None])[0]
    cache[cle] = [round(x["latitude"], 3), round(x["longitude"], 3)] if x else None
    time.sleep(0.3)
json.dump(cache, open("geo_cache.json", "w"), ensure_ascii=False, indent=0, sort_keys=True)
# prévision par ville
prev = {}
for cle in {f"{m['ville']}|{m['pays']}" for m in matchs}:
    g = cache.get(cle)
    if not g: continue
    r = get(f"https://api.open-meteo.com/v1/forecast?latitude={g[0]}&longitude={g[1]}&hourly=precipitation&timezone=GMT&forecast_days=8")
    if r and "hourly" in r:
        prev[cle] = dict(zip(r["hourly"]["time"], r["hourly"]["precipitation"]))
    time.sleep(0.2)
out = []
for m in matchs:
    p = prev.get(f"{m['ville']}|{m['pays']}")
    if not p: continue
    t = dt.datetime.fromisoformat(m["t"].replace("Z", "+00:00"))
    h0 = t.strftime("%Y-%m-%dT%H:00"); h1 = (t + dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:00")
    if h0 not in p: continue
    m["mm"] = round((p.get(h0) or 0) + (p.get(h1) or 0), 1)
    out.append(m)
json.dump(dict(maj=dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), source="ESPN + Open-Meteo (CC BY 4.0)", matchs=out),
          open("meteo_matchs.json", "w"), separators=(",", ":"), ensure_ascii=False)
print("ok", len(out), "matchs avec pluie prévue,", len(cache), "villes en cache")

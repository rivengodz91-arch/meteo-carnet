"""Prévision de pluie (7 jours, heure par heure) pour les stades des 5 grands championnats.
Lancé chaque jour par GitHub Actions ; écrit meteo.json, que le Carnet de paris lit ensuite."""
import json, urllib.request, time, datetime as dt
stades = json.load(open("stades.json"))
coords = list(stades)
out = {"maj": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), "source": "Open-Meteo (CC BY 4.0)", "equipes": {}, "pluie": {}}
for i in range(0, len(coords), 50):
    lot = coords[i:i + 50]
    lat = ",".join(c.split(",")[0] for c in lot); lon = ",".join(c.split(",")[1] for c in lot)
    url = ("https://api.open-meteo.com/v1/forecast?latitude=" + lat + "&longitude=" + lon +
           "&hourly=precipitation&timezone=GMT&forecast_days=7")
    rep = None
    for essai in range(3):
        try:
            rep = json.loads(urllib.request.urlopen(url, timeout=60).read())
            break
        except Exception:
            time.sleep(10)
    if rep is None:
        continue
    rep = rep if isinstance(rep, list) else [rep]
    for c, r in zip(lot, rep):
        h = r["hourly"]
        out["pluie"][c] = {"t0": h["time"][0], "mm": h["precipitation"]}
        for e in stades[c]:
            out["equipes"][e] = c
json.dump(out, open("meteo.json", "w"), separators=(",", ":"))
print("ok", len(out["pluie"]), "stades")

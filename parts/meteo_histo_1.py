import json, os, time, csv, datetime as dt, urllib.request, urllib.parse, urllib.error

LIGUES = ("arg.1 aus.1 aut.1 bra.1 chi.1 chn.1 col.1 cze.1 den.1 ecu.1 eng.1 eng.2 fin.1 fra.1 fra.2 ger.1 ger.2 gre.1 "
          "ita.1 ita.2 jpn.1 mex.1 ned.1 nor.1 par.1 por.1 irl.1 rou.1 sco.1 esp.1 esp.2 swe.1 sui.1 "
          "tur.1 usa.1 uefa.champions uefa.europa uefa.europa.conf").split()
DEBUT = dt.date(2023, 7, 1)
JOURS_PAR_PASSAGE = int(os.environ.get("JOURS", "60"))  # jours ESPN traités par championnat à chaque passage
D = "data/histo"
os.makedirs(D, exist_ok=True)
T0 = time.time()
LIMITE_S = 4.5 * 3600  # GitHub coupe à 6 h


def get(url, tries=3):
    err = None
    for i in range(tries):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=90).read())
        except urllib.error.HTTPError as e:
            err = e
            if e.code in (400, 404): break
            time.sleep(5 + 10 * i)
        except Exception as e:
            err = e; time.sleep(5 + 10 * i)
    print("ERREUR", url[:100], err)
    return None


def lire(f, defaut):
    return json.load(open(f)) if os.path.exists(f) else defaut


etat = lire(f"{D}/etat.json", {})
geo = lire(f"{D}/geo.json", {})
hier = dt.datetime.utcnow().date() - dt.timedelta(days=1)


def geocode(ville, pays):
    cle = f"{ville}|{pays}"
    if cle in geo: return geo[cle]
    nom = ville.split(",")[0].strip()
    r = get("https://geocoding-api.open-meteo.com/v1/search?count=10&name=" + urllib.parse.quote(nom))
    res = (r or {}).get("results") or []
    ok = [x for x in res if pays and pays.lower() in (x.get("country") or "").lower()]
    x = (ok or res or [None])[0]
    geo[cle] = [round(x["latitude"], 3), round(x["longitude"], 3), x.get("elevation")] if x else None
    time.sleep(0.3)
    return geo[cle]


# ---------- 1-3) foot ----------
for lg in LIGUES:
    if time.time() - T0 > LIMITE_S: break
    d0 = dt.date.fromisoformat(etat.get(lg, DEBUT.isoformat()))
    if d0 > hier: continue
    d1 = min(hier, d0 + dt.timedelta(days=JOURS_PAR_PASSAGE - 1))
    neufs = []
    d = d0
    while d <= d1:

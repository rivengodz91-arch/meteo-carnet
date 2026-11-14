# Robot compos officielles (14/11) : compo ESPN des matchs qui commencent dans les 100 min -> data/compos/AAAA-MM-JJ/<id>.json
import json, os, time, datetime as dt, urllib.request, urllib.parse, urllib.error

LIGUES = ("arg.1 aus.1 aut.1 bra.1 chi.1 chn.1 col.1 cze.1 den.1 ecu.1 eng.1 eng.2 fin.1 fra.1 fra.2 ger.1 ger.2 gre.1 "
          "ita.1 ita.2 jpn.1 mex.1 ned.1 nor.1 par.1 por.1 irl.1 rou.1 sco.1 esp.1 esp.2 swe.1 sui.1 "
          "tur.1 usa.1 uefa.champions uefa.europa uefa.europa.conf").split()


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
n_ok = n_vus = 0
jours = sorted({now.date(), (now + dt.timedelta(minutes=100)).date(), (now - dt.timedelta(minutes=20)).date()})
for lg in LIGUES:
    for jour in jours:
        j = get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard?dates={jour:%Y%m%d}")
        for e in (j or {}).get("events", []):
            t = dt.datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
            if not (-20 <= (t - now).total_seconds() / 60 <= 100): continue
            n_vus += 1
            dos = f"data/compos/{t:%Y-%m-%d}"; f = f"{dos}/{e['id']}.json"
            if os.path.exists(f): continue
            s = get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/summary?event={e['id']}")
            eq = {}
            for r in (s or {}).get("rosters", []) or []:
                nom = (r.get("team") or {}).get("displayName")
                tit, rem = [], []
                for p in r.get("roster", []) or []:
                    a = p.get("athlete") or {}

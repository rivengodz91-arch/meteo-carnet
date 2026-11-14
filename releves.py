"""Relevés à heures fixes (robot GitHub, PC éteint) — usage privé du Carnet de paris.
1) Pinnacle : cotes joueurs (« Player Props ») NBA / NHL / foot + cotes principales NBA, NHL, 5 grands championnats.
   La clé « guest » Pinnacle n'est PAS dans ce dépôt : elle est lue dans le secret GitHub PIN_KEY (sinon cette partie est sautée).
2) ESPN : blessures annoncées NBA et NHL (historique qu'ESPN ne garde pas).
Écrit data/AAAA-MM-JJ/HHMM_<nom>.json.gz"""
import json, os, gzip, time, datetime as dt, urllib.request
now = dt.datetime.utcnow()
dossier = f"data/{now:%Y-%m-%d}"; os.makedirs(dossier, exist_ok=True)
stamp = f"{now:%H%M}"
def get(url, headers=None, tries=3):
    for i in range(tries):
        try:
            b = urllib.request.urlopen(urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"}), timeout=90).read()
            if b[:2] == b"\x1f\x8b": b = gzip.decompress(b)
            return json.loads(b)
        except Exception as e:
            err = e; time.sleep(5)
    print("ERREUR", url[:80], err); return None
def save(nom, obj):
    with gzip.open(f"{dossier}/{stamp}_{nom}.json.gz", "wt", encoding="utf-8") as f:
        json.dump(obj, f, separators=(",", ":"), ensure_ascii=False)
    print("ok", nom)
LIGUES_FOOT = ("England - Premier League", "Spain - La Liga", "Italy - Serie A", "Germany - Bundesliga", "France - Ligue 1")
KEY = os.environ.get("PIN_KEY", "").strip()
if KEY:
    H = {"User-Agent": "Mozilla/5.0", "X-API-Key": KEY, "Accept-Encoding": "gzip"}
    B = "https://guest.api.arcadia.pinnacle.com/0.1"
    for sp, nom in ((4, "basket"), (19, "hockey"), (29, "foot")):
        MU = get(f"{B}/sports/{sp}/matchups", H); MK = get(f"{B}/sports/{sp}/markets/straight?primaryOnly=false", H)
        if not isinstance(MU, list) or not isinstance(MK, list): continue
        def garder(m):
            lg = (m.get("league") or {}).get("name", "")
            if sp == 4: return lg == "NBA"
            if sp == 19: return lg == "NHL"
            return lg in LIGUES_FOOT
        par = {m["id"]: m for m in MU if m.get("type") == "matchup" and garder(m)}
        out = {"matchs": {}, "props": [], "cotes": []}
        for i, m in par.items():
            out["matchs"][i] = dict(t=m.get("startTime"), lg=m["league"]["name"], eq=[p.get("name") for p in m.get("participants", [])])
        props = {m["id"]: m for m in MU if m.get("type") == "special" and m.get("parentId") in par and (m.get("special") or {}).get("category") == "Player Props"}
        for k in MK:
            mid = k.get("matchupId")
            if mid in props:
                s = props[mid]
                out["props"].append(dict(m=s["parentId"], d=s["special"]["description"], p={pp["id"]: pp["name"] for pp in s.get("participants", [])},
                                         c=[(x.get("participantId"), x.get("designation"), x.get("points"), x.get("price")) for x in k.get("prices", [])]))
            elif mid in par and k.get("period") == 0 and k.get("type") in ("moneyline", "total", "spread") and not k.get("isAlternate"):
                out["cotes"].append(dict(m=mid, ty=k["type"], c=[(x.get("designation"), x.get("points"), x.get("price")) for x in k.get("prices", [])]))
        save(f"pinnacle_{nom}", out)
else:
    print("PIN_KEY absent : relevé Pinnacle sauté")
for sp, nom in (("basketball/nba", "nba"), ("hockey/nhl", "nhl")):
    j = get(f"https://site.api.espn.com/apis/site/v2/sports/{sp}/injuries")
    if j:
        out = []
        for t in j.get("injuries", []):
            for i in t.get("injuries", []):
                a = i.get("athlete") or {}
                out.append(dict(eq=t.get("displayName"), j=a.get("displayName"), id=a.get("id"), st=i.get("status"), d=i.get("date"),
                                ty=(i.get("details") or {}).get("type"), ret=(i.get("details") or {}).get("returnDate")))
        save(f"blessures_{nom}", out)

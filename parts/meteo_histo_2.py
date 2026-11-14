        j = get(f"https://site.api.espn.com/apis/site/v2/sports/soccer/{lg}/scoreboard?dates={d:%Y%m%d}")
        for e in (j or {}).get("events", []):
            c = e["competitions"][0]
            if not c.get("status", {}).get("type", {}).get("completed"): continue
            a = (c.get("venue") or {}).get("address") or {}
            cp = {x.get("homeAway"): x for x in c.get("competitors", [])}
            if not a.get("city") or "home" not in cp or "away" not in cp: continue
            neufs.append(dict(id=e["id"], t=e["date"], dom=cp["home"]["team"].get("displayName"), ext=cp["away"]["team"].get("displayName"),
                              sd=cp["home"].get("score"), se=cp["away"].get("score"), ville=a["city"], pays=a.get("country", "")))
        time.sleep(0.15)
        d += dt.timedelta(days=1)
    # météo : une requête d'archive par ville pour la période du morceau
    parville = {}
    for m in neufs: parville.setdefault((m["ville"], m["pays"]), []).append(m)
    for (v, p), L in parville.items():
        g = geocode(v, p)
        if not g: continue
        t1 = min(m["t"][:10] for m in L); t2 = max(m["t"][:10] for m in L)
        r = get(f"https://archive-api.open-meteo.com/v1/archive?latitude={g[0]}&longitude={g[1]}&start_date={t1}&end_date={t2}"
                "&hourly=precipitation,wind_speed_10m,temperature_2m&timezone=GMT")
        time.sleep(0.3)
        if not r or "hourly" not in r: continue
        H = r["hourly"]; idx = {h: i for i, h in enumerate(H["time"])}
        for m in L:
            t = dt.datetime.fromisoformat(m["t"].replace("Z", "+00:00"))
            h0 = t.strftime("%Y-%m-%dT%H:00"); h1 = (t + dt.timedelta(hours=1)).strftime("%Y-%m-%dT%H:00")
            if h0 not in idx: continue
            i0 = idx[h0]; i1 = idx.get(h1, i0)
            m["alt"] = g[2]
            m["pluie_mm"] = round((H["precipitation"][i0] or 0) + (H["precipitation"][i1] or 0), 1)

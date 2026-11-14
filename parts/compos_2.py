                    x = [a.get("id"), a.get("displayName"), (p.get("position") or {}).get("abbreviation")]
                    (tit if p.get("starter") else rem).append(x)
                if nom and len(tit) >= 11: eq[nom] = {"titulaires": tit, "remplacants": rem}
            if len(eq) == 2:
                os.makedirs(dos, exist_ok=True)
                cp = {x.get("homeAway"): (x.get("team") or {}).get("displayName") for x in e["competitions"][0].get("competitors", [])}
                json.dump(dict(t=e["date"], lg=lg, dom=cp.get("home"), ext=cp.get("away"), releve=now.strftime("%Y-%m-%dT%H:%MZ"), equipes=eq),
                          open(f, "w"), ensure_ascii=False, separators=(",", ":"))
                n_ok += 1
            time.sleep(0.2)
        time.sleep(0.1)
print(f"compos : {n_vus} match(s) dans la fenêtre, {n_ok} compo(s) officielle(s) relevée(s)")

import subprocess, sys
subprocess.run([sys.executable, "meteo_tennis.py"])

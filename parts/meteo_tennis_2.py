        time.sleep(0.3)
    json.dump(cache, open("geo_tennis.json", "w"), ensure_ascii=False, indent=0, sort_keys=True)
    json.dump(dict(maj=now.strftime("%Y-%m-%dT%H:%MZ"), source="ESPN + Open-Meteo (CC BY 4.0)",
                   note="indoor non indiqué : le labo le prend dans l'historique des tournois", villes=out),
              open("meteo_tennis.json", "w"), ensure_ascii=False, separators=(",", ":"))
    print("météo tennis :", len(out), "ville(s)")

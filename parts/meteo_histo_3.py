            m["vent_kmh"] = H["wind_speed_10m"][i0]
            m["temp_c"] = H["temperature_2m"][i0]
    f = f"{D}/foot_{lg}.csv"; neuf_f = not os.path.exists(f)
    with open(f, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "t", "dom", "ext", "sd", "se", "ville", "pays", "alt", "pluie_mm", "vent_kmh", "temp_c"], extrasaction="ignore")
        if neuf_f: w.writeheader()
        for m in neufs: w.writerow(m)
    etat[lg] = (d1 + dt.timedelta(days=1)).isoformat()
    print(lg, d0, "→", d1, ":", len(neufs), "matchs,", sum(1 for m in neufs if "pluie_mm" in m), "avec météo")
    json.dump(etat, open(f"{D}/etat.json", "w"), indent=0, sort_keys=True)
    json.dump(geo, open(f"{D}/geo.json", "w"), ensure_ascii=False, indent=0, sort_keys=True)

# ---------- 4) tennis : villes des tournois ATP (coordonnées fixées à la main) ----------
TENNIS = {"'s-Hertogenbosch": (51.69, 5.30), "Acapulco": (16.86, -99.88), "Adelaide": (-34.93, 138.60), "Almaty": (43.24, 76.89),
          "Antalya": (36.90, 30.70), "Antwerp": (51.22, 4.40), "Athens": (37.98, 23.73), "Atlanta": (33.75, -84.39), "Auckland": (-36.85, 174.76),
          "Banja Luka": (44.77, 17.19), "Barcelona": (41.39, 2.17), "Basel": (47.56, 7.59), "Bastad": (56.43, 12.85), "Beijing": (39.90, 116.40),
          "Belgrade": (44.79, 20.45), "Brisbane": (-27.47, 153.03), "Brussels": (50.85, 4.35), "Bucharest": (44.43, 26.10),
          "Buenos Aires": (-34.60, -58.38), "Cagliari": (39.22, 9.12), "Chengdu": (30.57, 104.07), "Cincinnati": (39.10, -84.51),
          "Cologne": (50.94, 6.96), "Cordoba": (-31.42, -64.18), "Dallas": (32.78, -96.80), "Delray Beach": (26.46, -80.07), "Doha": (25.29, 51.53),
          "Dubai": (25.20, 55.27), "Eastbourne": (50.77, 0.28), "Estoril": (38.71, -9.40), "Florence": (43.77, 11.26), "Geneva": (46.20, 6.14),
          "Gijon": (43.54, -5.66), "Gstaad": (46.47, 7.29), "Halle": (52.06, 8.36), "Hamburg": (53.55, 9.99), "Hangzhou": (30.27, 120.16),

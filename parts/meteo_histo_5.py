    for i, d in enumerate(Dd["time"]):
        lignes.append([v, d, Dd["precipitation_sum"][i], Dd["wind_speed_10m_max"][i], Dd["temperature_2m_max"][i]])
    fait[v] = (hier + dt.timedelta(days=1)).isoformat()
if lignes:
    neuf_f = not os.path.exists(ft)
    with open(ft, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if neuf_f: w.writerow(["ville", "date", "pluie_mm", "vent_max_kmh", "temp_max_c"])
        w.writerows(lignes)
json.dump(fait, open(f"{D}/tennis_etat.json", "w"), indent=0, sort_keys=True)
reste = sum(1 for lg in LIGUES if dt.date.fromisoformat(etat.get(lg, DEBUT.isoformat())) <= hier)
print(f"tennis : {len(lignes)} jours-villes ajoutés ; foot : {reste} championnat(s) pas encore à jour ; {time.time() - T0:.0f} s")

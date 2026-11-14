          "Hong Kong": (22.32, 114.17), "Houston": (29.76, -95.37), "Indian Wells": (33.72, -116.31), "Kitzbuhel": (47.45, 12.39),
          "London": (51.51, -0.13), "Los Cabos": (22.89, -109.91), "Lyon": (45.76, 4.84), "Madrid": (40.42, -3.70), "Mallorca": (39.57, 2.65),
          "Marbella": (36.51, -4.88), "Marrakech": (31.63, -8.01), "Marseille": (43.30, 5.37), "Melbourne": (-37.81, 144.96), "Metz": (49.12, 6.18),
          "Miami": (25.76, -80.19), "Monte Carlo": (43.74, 7.42), "Montpellier": (43.61, 3.88), "Montreal": (45.50, -73.57), "Moscow": (55.76, 37.62),
          "Munich": (48.14, 11.58), "Napoli": (40.85, 14.27), "New York": (40.71, -74.01), "Newport": (41.49, -71.31), "Nur-Sultan": (51.17, 71.45),
          "Paris": (48.86, 2.35), "Parma": (44.80, 10.33), "Pune": (18.52, 73.86), "Queens Club": (51.49, -0.21), "Rio de Janeiro": (-22.91, -43.17),
          "Rome": (41.90, 12.50), "Rotterdam": (51.92, 4.48), "San Diego": (32.72, -117.16), "Santiago": (-33.45, -70.67), "Sardinia": (39.22, 9.12),
          "Seoul": (37.57, 126.98), "Shanghai": (31.23, 121.47), "Singapore": (1.35, 103.82), "Sofia": (42.70, 23.32), "St. Petersburg": (59.93, 30.36),
          "Stockholm": (59.33, 18.07), "Stuttgart": (48.78, 9.18), "Sydney": (-33.87, 151.21), "Tel Aviv": (32.09, 34.78), "Tokyo": (35.68, 139.69),
          "Toronto": (43.65, -79.38), "Turin": (45.07, 7.69), "Umag": (45.43, 13.52), "Vienna": (48.21, 16.37), "Washington": (38.91, -77.04),
          "Winston-Salem": (36.10, -80.24), "Zhuhai": (22.27, 113.58)}
ft = f"{D}/tennis_meteo.csv"
fait = lire(f"{D}/tennis_etat.json", {})
lignes = []
for v, (la, lo) in TENNIS.items():
    if time.time() - T0 > LIMITE_S: break
    d0 = dt.date.fromisoformat(fait.get(v, "2020-01-01"))
    if d0 > hier: continue
    r = get(f"https://archive-api.open-meteo.com/v1/archive?latitude={la}&longitude={lo}&start_date={d0}&end_date={hier}"
            "&daily=precipitation_sum,wind_speed_10m_max,temperature_2m_max&timezone=auto")
    time.sleep(0.5)
    if not r or "daily" not in r: continue
    Dd = r["daily"]

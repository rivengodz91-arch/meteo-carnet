# Robot meteo_tennis : code découpé en 2 morceaux dans parts/ (limite de taille de GitHub)
exec(compile("".join(open(f, encoding="utf-8").read() for f in ('parts/meteo_tennis_1.py', 'parts/meteo_tennis_2.py')), "meteo_tennis", "exec"))

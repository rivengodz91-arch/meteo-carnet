# Robot compos : code découpé en 2 morceaux dans parts/ (limite de taille de GitHub)
exec(compile("".join(open(f, encoding="utf-8").read() for f in ('parts/compos_1.py', 'parts/compos_2.py')), "compos", "exec"))

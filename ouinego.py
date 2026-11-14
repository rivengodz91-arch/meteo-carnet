# Robots OUInégo (gratuits, tournent sur GitHub) — 4 veilles :
# 1) ouvertures de magasins des réseaux franchisés (diff des sitemaps officiels)
# 1 bis) ouvertures annoncées dans la presse (Google Actualités), tous les réseaux suivis
# 2) fournisseurs d'énergie en difficulté (BODACC + registre + presse)
# 3) alerte prix bas du marché de gros (prix spot France, energy-charts.info)
# Sorties : dossier ouinego/ ; résumé lu par la tâche « Copilote OUInégo du matin » : ouinego/synthese.json
import json, os, re, gzip, io, time, datetime, statistics, urllib.request, urllib.parse, xml.etree.ElementTree as ET

D = "ouinego"
os.makedirs(D, exist_ok=True)
NOW = datetime.datetime.now(datetime.timezone.utc)
TODAY = NOW.date().isoformat()
UA = {"User-Agent": "Mozilla/5.0 (compatible; ouinego-veille/1.0; +https://github.com/rivengodz91-arch/meteo-carnet)"}

def get(url, timeout=40, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    if url.endswith(".gz") or data[:2] == b"\x1f\x8b":
        try: data = gzip.decompress(data)
        except Exception: pass
    return data if binary else data.decode("utf-8", "replace")

def getj(url, timeout=40):
    return json.loads(get(url, timeout))

def load(name, default):
    p = os.path.join(D, name)
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def save(name, obj):
    with open(os.path.join(D, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

ETAT = {"maj": NOW.isoformat(timespec="minutes"), "robots": {}}

# ---------------------------------------------------------------- 1) OUVERTURES
RESEAUX = load("reseaux.json", [])

def sitemap_urls(domain, limit_files=60):
    """Toutes les URL des sitemaps du site (robots.txt + emplacements classiques), parcours récursif limité.
    Renvoie aussi un diagnostic par sitemap essayé (pour corriger un réseau qui ne donne rien)."""
    seeds, diag = [], []
    try:
        for line in get(f"https://{domain}/robots.txt", 25).splitlines():
            if line.lower().startswith("sitemap:"):
                seeds.append(line.split(":", 1)[1].strip())
        diag.append(f"robots.txt ok, {len(seeds)} sitemap(s) déclaré(s)")
    except Exception as e:
        diag.append("robots.txt : " + str(e)[:80])
    for s in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"):
        seeds.append(f"https://{domain}{s}")
    seen, todo, urls = set(), list(dict.fromkeys(seeds)), set()
    while todo and len(seen) < limit_files:
        sm = todo.pop(0)
        if sm in seen: continue
        seen.add(sm)
        try:
            txt = get(sm, 40)
        except Exception as e:
            if len(diag) < 12: diag.append(f"{sm} : {str(e)[:80]}")
            continue
        try:
            root = ET.fromstring(txt.encode("utf-8"))
        except Exception:
            if len(diag) < 12: diag.append(f"{sm} : pas du XML ({txt[:60].strip()!r})")
            continue
        n = 0
        for el in root.iter():
            if el.tag.endswith("loc") and el.text:
                u = el.text.strip(); n += 1
                if root.tag.endswith("sitemapindex"): todo.append(u)
                else: urls.add(u)
        if len(diag) < 12: diag.append(f"{sm} : {n} liens")
    return urls, len(seen), diag

CP = re.compile(r"\b((?:0[1-9]|[1-8]\d|9[0-8])\d{3})\s+([A-ZÉÈÂÎ][A-Za-zÀ-ÿ'’ -]{1,40})")
LIAISONS = {"sur", "en", "de", "du", "des", "la", "le", "les", "lès", "lez", "sous", "aux", "au", "saint", "sainte", "st", "ste", "d'"}

def _sans_accent(x):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", x.lower()) if unicodedata.category(c) != "Mn")

def _ville(brut):
    """« AMBERIEU EN BUGEY Voir » -> « AMBERIEU EN BUGEY » ; « Portet sur Garonne » garde la liaison."""
    mots, garde = brut.split(), []
    for i, w in enumerate(mots):
        if i == 0 or w.isupper() or _sans_accent(w) in LIAISONS or _sans_accent(garde[-1]) in LIAISONS:
            garde.append(w)
        else:
            break
    while garde and _sans_accent(garde[-1]) in LIAISONS:
        garde.pop()
    return " ".join(garde[:5]).strip(" -")

def verifier(u):
    """Ouvre la page d'un nouveau magasin et y lit le code postal + la ville (ceux qui collent à l'adresse de la page en priorité)."""
    try:
        h = get(u, 25)
    except Exception:
        return {"adresse": "page illisible, à vérifier"}
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)))
    if re.search(r"aucune ouverture n.est prévue|\b0 clubs?\b", t, re.I):
        return None  # page « ville sans magasin » ou liste vide : pas une ouverture
    lien = re.sub(r"[^a-z0-9]+", " ", _sans_accent(u))
    trouves = [(m.group(1), _ville(m.group(2))) for m in CP.finditer(t)][:30]
    if not trouves:
        return {"adresse": "non lue sur la page, à vérifier"}
    bon = next(((cp, v) for cp, v in trouves if v and " " + re.sub(r"[^a-z0-9]+", " ", _sans_accent(v)).strip() + " " in " " + lien + " "), trouves[0])
    return {"cp": bon[0], "ville": bon[1]}

def robot_ouvertures():
    res = {"reseaux": {}, "nouveaux": []}
    hist = load("ouvertures.json", {"nouveaux": []})
    for R in RESEAUX:
        nom, dom, pat = R["nom"], R["domaine"], re.compile(R["motif"])
        fichier = "magasins_" + re.sub(r"[^a-z0-9]+", "-", nom.lower()).strip("-") + ".json"
        connu = load(fichier, None)
        try:
            urls, nfic, diag = sitemap_urls(dom)
            mag = sorted(u for u in urls if pat.search(u))
        except Exception as e:
            res["reseaux"][nom] = {"statut": "erreur", "detail": str(e)[:200]}; continue
        if not mag:
            ex = sorted({"/".join(u.split("/")[:5]) for u in urls})[:15]
            res["reseaux"][nom] = {"statut": "aucune fiche magasin trouvée", "sitemaps_lus": nfic, "urls_vues": len(urls), "diagnostic": diag, "exemples": ex}
            continue
        if connu is None:
            save(fichier, {"depuis": TODAY, "magasins": mag})
            res["reseaux"][nom] = {"statut": "référence créée", "magasins": len(mag), "test_page": [mag[0], verifier(mag[0])]}
            continue
        anciens = set(connu["magasins"])
        neufs = [u for u in mag if u not in anciens]
        disparus = [u for u in anciens if u not in set(mag)]
        # garde-fou : un site qui change toute sa structure ne doit pas créer 300 « ouvertures »
        if len(neufs) > max(15, 0.2 * len(anciens)):
            res["reseaux"][nom] = {"statut": "trop de changements d'un coup : vérification à la main", "nouvelles_url": len(neufs), "magasins": len(mag)}
            continue
        ignores = 0
        for u in neufs:
            v = verifier(u)
            if v is None: ignores += 1; continue
            a = dict({"reseau": nom, "lien": u}, **v)
            hist["nouveaux"].append(dict(a, date=TODAY)); res["nouveaux"].append(a)
        save(fichier, {"depuis": connu.get("depuis", TODAY), "magasins": mag})
        res["reseaux"][nom] = {"statut": "ok", "magasins": len(mag), "nouveaux": len(neufs) - ignores, "pages_sans_magasin_ignorees": ignores, "disparus": len(disparus)}
        if os.environ.get("FORCER") == "tout": res["reseaux"][nom]["test_page"] = [mag[0], verifier(mag[0])]
    hist["nouveaux"] = hist["nouveaux"][-500:]
    save("ouvertures.json", hist)
    return res

# ---------------------------------------------------------------- 1 bis) OUVERTURES ANNONCÉES DANS LA PRESSE
# Couvre aussi les réseaux dont le site bloque les robots (Domino's, B&B, Kyriad, Carrefour Contact, Wefit, Yelloh, Magic Form).
PRESSE = {
    "Domino's": ["domino's", "dominos", "domino’s"],
    "Carrefour Contact": ["carrefour contact"],
    "Kyriad": ["kyriad"],
    "B&B Hotels": ["b&b hotel", "b&b hôtel", "hôtel b&b", "hotel b&b", "b&b hotels"],
    "Yelloh Village": ["yelloh"],
    "Magic Form": ["magic form"],
    "Wefit": ["wefit"],
    "Tutti Pizza": ["tutti pizza"],
    "Moustache Glaces": ["glaces moustache", "glacier moustache", "moustache glaces"],
    "Fitness Park": ["fitness park"],
    "Keep Cool": ["keep cool", "keepcool"],
    "L'Orange Bleue": ["orange bleue"],
    "Biocoop": ["biocoop"],
    "5àSec": ["5 à sec", "5àsec", "5asec", "5 a sec"],
    "Boulangerie Ange": ["boulangerie ange", "boulangeries ange"],
}
OUVRE = re.compile(r"ouvr|ouverture|inaugur|s'install|s’install|arrive à|arrive au|arrive en|débarque|nouveau restaurant|nouvel hôtel|nouvelle salle|nouveau magasin|nouvelle boutique|prochainement", re.I)
FERME = re.compile(r"ferme|fermeture|liquidation|redressement|braqu|incendie|agress|vol |cambriol|condamn", re.I)

def robot_presse():
    res = {"nouveaux": [], "requetes_ko": []}
    vus = load("presse_vus.json", {})
    for nom, alias in PRESSE.items():
        q = "(" + " OR ".join(f'"{a}"' for a in alias[:3]) + ") (ouverture OR ouvre OR inauguration OR \"s'installe\") when:7d"
        try:
            x = get("https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q, "hl": "fr", "gl": "FR", "ceid": "FR:fr"}), 30)
            root = ET.fromstring(x.encode("utf-8"))
        except Exception as e:
            res["requetes_ko"].append(f"{nom}: {str(e)[:80]}"); continue
        for it in root.iter("item"):
            t = (it.findtext("title") or "").strip(); l = (it.findtext("link") or "").strip()
            src = (it.findtext("source") or "").strip(); dt = (it.findtext("pubDate") or "").strip()
            tl = t.lower()
            if not t or not any(a in tl for a in alias) or not OUVRE.search(t) or FERME.search(t):
                continue
            cle = re.sub(r"\W+", "", tl)[:90]
            if cle in vus: continue
            vus[cle] = TODAY
            res["nouveaux"].append({"reseau": nom, "titre": t, "source": src, "publie": dt[:16], "lien": l})
        time.sleep(0.6)
    vus = {k: v for k, v in vus.items() if v >= (NOW - datetime.timedelta(days=60)).date().isoformat()}
    save("presse_vus.json", vus)
    hist = load("presse.json", {"articles": []})
    hist["articles"] = (hist["articles"] + [dict(a, vu_le=TODAY) for a in res["nouveaux"]])[-400:]
    save("presse.json", hist)
    return res

# ---------------------------------------------------------------- 2) FOURNISSEURS EN DIFFICULTÉ
API = "https://recherche-entreprises.api.gouv.fr/search"

def fournisseurs():
    """Sociétés actives de commerce d'électricité (35.14Z) et de gaz (35.23Z), liste rafraîchie chaque lundi."""
    cache = load("fournisseurs_liste.json", None)
    if cache and (NOW.weekday() != 0 or cache.get("maj") == TODAY):
        return cache["liste"]
    liste = {}
    for naf in ("35.14Z", "35.23Z"):
        for page in range(1, 61):
            try:
                j = getj(f"{API}?activite_principale={naf}&etat_administratif=A&per_page=25&page={page}&minimal=true")
            except Exception:
                time.sleep(2); continue
            for r in j.get("results", []):
                liste[r["siren"]] = r.get("nom_complet", "")
            if page >= j.get("total_pages", 1): break
            time.sleep(0.25)
    save("fournisseurs_liste.json", {"maj": TODAY, "liste": liste})
    return liste

CONNUS = ("edf", "engie", "totalenergies", "total energies", "ekwateur", "ohm energie", "ohm énergie", "mint energie", "alpiq", "vattenfall", "enercoop", "plum", "octopus", "eni gas", "eni plenitude", "plenitude", "iberdrola", "ilek", "gaz de bordeaux", "elmy", "energem", "primeo", "wekiwi", "alterna", "gedia", "sowee", "hydroption", "volterres", "selia", "met france", "gazel", "dyneff", "butagaz", "gaz europeen", "gaz européen", "proxelia", "lucia", "mega energie", "énergie d'ici", "energie d'ici", "urban solar", "barry", "happ-e", "la bellenergie", "geg", "es energies", "seolis", "sorégies", "soregies", "uem", "elecocite")
BODACC = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"
MOTS_PRESSE = ("redressement", "liquidation", "faillite", "sauvegarde", "cessation", "suspend", "retrait", "défaillance", "defaillance", "difficult", "fournisseur de secours", "fournisseur de dernier recours", "arrête", "arrete")

def robot_fournisseurs():
    res = {"alertes": []}
    vus = load("fournisseurs_vus.json", {})
    liste = fournisseurs()
    res["fournisseurs_suivis"] = len(liste)
    depuis = (NOW - datetime.timedelta(days=10)).date().isoformat()
    # a) BODACC : procédures collectives des 10 derniers jours visant un fournisseur suivi
    sirens = list(liste)
    for i in range(0, len(sirens), 40):
        lot = sirens[i:i+40]
        cond = " or ".join(f'registre like "{s}"' for s in lot)
        where = f'familleavis="collective" and dateparution>="{depuis}" and ({cond})'
        try:
            j = getj(BODACC + "?" + urllib.parse.urlencode({"where": where, "limit": 100}))
        except Exception as e:
            res.setdefault("erreurs", []).append("bodacc: " + str(e)[:120]); continue
        for r in j.get("results", []):
            cle = "bodacc:" + str(r.get("id"))
            if cle in vus: continue
            reg = re.sub(r"\D", "", json.dumps(r.get("registre", "")))
            siren = next((s for s in lot if s in reg), "")
            jug = r.get("jugement") or ""
            try: jug = json.loads(jug) if isinstance(jug, str) and jug.startswith("{") else jug
            except Exception: pass
            nature = (jug.get("nature") if isinstance(jug, dict) else "") or r.get("familleavis_lib", "")
            nomf = (liste.get(siren) or r.get("commercant", "") or "")
            a = {"source": "BODACC", "fournisseur_connu": any(c in nomf.lower() for c in CONNUS), "date": r.get("dateparution"), "fournisseur": nomf, "siren": siren,
                 "quoi": nature, "lien": r.get("url_complete") or f"https://www.bodacc.fr/pages/annonces-commerciales-detail/?q.id=id:{r.get('id')}"}
            res["alertes"].append(a); vus[cle] = TODAY
        time.sleep(0.3)
    # b) Presse (Google Actualités, RSS) : mots-clés de difficulté + fournisseur d'énergie
    reqs = ['"fournisseur d\'électricité" (redressement OR liquidation OR faillite OR "cessation d\'activité")',
            '"fournisseur d\'énergie" (redressement OR liquidation OR faillite OR "suspend" OR "défaillance")',
            '"fournisseur de secours" électricité', '"fournisseur de dernier recours" gaz OR électricité']
    for q in reqs:
        try:
            x = get("https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q + " when:7d", "hl": "fr", "gl": "FR", "ceid": "FR:fr"}), 30)
            root = ET.fromstring(x.encode("utf-8"))
        except Exception as e:
            res.setdefault("erreurs", []).append("presse: " + str(e)[:120]); continue
        for it in root.iter("item"):
            t = (it.findtext("title") or "").strip(); l = (it.findtext("link") or "").strip()
            if not t or not any(m in t.lower() for m in MOTS_PRESSE): continue
            cle = "presse:" + re.sub(r"\W+", "", t.lower())[:90]
            if cle in vus: continue
            res["alertes"].append({"source": "Presse", "date": TODAY, "fournisseur": "", "quoi": t, "lien": l}); vus[cle] = TODAY
        time.sleep(0.5)
    # c) Registre : fournisseur suivi la semaine dernière et radié depuis (lundi seulement)
    ancienne = load("fournisseurs_liste_prec.json", None)
    if NOW.weekday() == 0:
        if ancienne:
            for s, n in ancienne.get("liste", {}).items():
                if s not in liste and ("radie:" + s) not in vus:
                    try:
                        j = getj(f"{API}?q={s}&minimal=true")
                        r = next((x for x in j.get("results", []) if x["siren"] == s), None)
                    except Exception: r = None
                    if r and r.get("etat_administratif") == "C":
                        res["alertes"].append({"source": "Registre", "date": TODAY, "fournisseur": n, "siren": s, "quoi": "société cessée (radiée du registre)", "lien": f"https://annuaire-entreprises.data.gouv.fr/entreprise/{s}"})
                        vus["radie:" + s] = TODAY
        save("fournisseurs_liste_prec.json", {"maj": TODAY, "liste": liste})
    save("fournisseurs_vus.json", vus)
    hist = load("fournisseurs.json", {"alertes": []})
    hist["alertes"] = (hist["alertes"] + [dict(a, vu_le=TODAY) for a in res["alertes"]])[-300:]
    save("fournisseurs.json", hist)
    return res

# ---------------------------------------------------------------- 3) PRIX BAS DU MARCHÉ
def robot_prix():
    """Prix spot day-ahead France (€/MWh), source energy-charts.info (Fraunhofer ISE, données EPEX/ENTSO-E)."""
    hist = load("prix.json", {"jours": {}})
    debut = (NOW - datetime.timedelta(days=400 if len(hist["jours"]) < 300 else 10)).date().isoformat()
    j = getj(f"https://api.energy-charts.info/price?bzn=FR&start={debut}&end={TODAY}", 60)
    par_jour = {}
    for ts, p in zip(j.get("unix_seconds", []), j.get("price", [])):
        if p is None: continue
        d = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).date().isoformat()
        par_jour.setdefault(d, []).append(p)
    for d, v in par_jour.items():
        if len(v) >= 20: hist["jours"][d] = round(sum(v) / len(v), 2)
    jours = sorted(hist["jours"])
    hist["jours"] = {d: hist["jours"][d] for d in jours[-420:]}
    jours = sorted(hist["jours"])
    vals = [hist["jours"][d] for d in jours]
    res = {"source": "energy-charts.info (prix spot day-ahead France, moyenne journalière base)"}
    if len(vals) < 60:
        res["statut"] = "historique trop court"; save("prix.json", hist); return res
    m7 = sum(vals[-7:]) / 7
    m30 = sum(vals[-30:]) / 30
    an = vals[-365:]
    rang = sum(1 for x in an if x <= m7) / len(an)  # part des jours de l'année moins chers que la moyenne 7 j
    q20 = sorted(an)[int(0.2 * (len(an) - 1))]
    res.update({"dernier_jour": jours[-1], "moy_7j": round(m7, 1), "moy_30j": round(m30, 1), "moy_365j": round(sum(an) / len(an), 1),
                "seuil_bas_20pct": round(q20, 1), "rang_7j_sur_an_pct": round(100 * rang)})
    alerte = None
    if m7 <= q20:
        alerte = f"Prix spot au plus bas : moyenne 7 jours {m7:.0f} €/MWh, parmi les 20 % les plus bas de l'année (moyenne 1 an : {sum(an)/len(an):.0f} €/MWh)."
    elif m7 <= 0.85 * m30:
        alerte = f"Prix spot en forte baisse : moyenne 7 jours {m7:.0f} €/MWh, soit {100*(1-m7/m30):.0f} % sous la moyenne 30 jours ({m30:.0f} €/MWh)."
    der = hist.get("derniere_alerte")
    if alerte and der and (NOW.date() - datetime.date.fromisoformat(der)).days < 7:
        res["alerte_deja_envoyee_le"] = der; alerte = None  # pas plus d'une alerte par semaine
    if alerte:
        hist["derniere_alerte"] = TODAY
    res["alerte"] = alerte
    save("prix.json", hist)
    return res

# ---------------------------------------------------------------- lancement
SYN = load("synthese.json", {"historique": []})
nouv = {"date": TODAY}
quand = os.environ.get("FORCER", "")
for nom, fn, jours in (("ouvertures", robot_ouvertures, {0}), ("presse", robot_presse, {0,1,2,3,4,5,6}), ("fournisseurs", robot_fournisseurs, {0,1,2,3,4,5,6}), ("prix", robot_prix, {0,1,2,3,4,5,6})):
    if NOW.weekday() not in jours and nom not in quand and quand != "tout":
        continue
    try:
        r = fn(); ETAT["robots"][nom] = {"statut": "ok", "resultat": r}
        if nom == "ouvertures" and r.get("nouveaux"): nouv["ouvertures"] = r["nouveaux"]
        if nom == "presse" and r.get("nouveaux"): nouv["presse"] = r["nouveaux"]
        if nom == "fournisseurs" and r.get("alertes"): nouv["fournisseurs"] = r["alertes"]
        if nom == "prix" and r.get("alerte"): nouv["prix"] = r["alerte"]
    except Exception as e:
        ETAT["robots"][nom] = {"statut": "erreur", "detail": f"{type(e).__name__}: {str(e)[:300]}"}
SYN["maj"] = ETAT["maj"]
SYN["etat"] = {k: v["statut"] for k, v in ETAT["robots"].items()}
if len(nouv) > 1:
    # fusion avec ce qui a déjà été trouvé aujourd'hui (plusieurs passages possibles dans la journée)
    du_jour = next((h for h in SYN["historique"] if h.get("date") == TODAY), None)
    if du_jour is None:
        SYN["historique"].append(nouv)
    else:
        for k, v in nouv.items():
            if k == "date": continue
            if isinstance(v, list): du_jour[k] = du_jour.get(k, []) + v
            else: du_jour[k] = v
SYN["historique"] = SYN["historique"][-60:]
save("synthese.json", SYN)
save("etat.json", ETAT)
print(json.dumps(ETAT, ensure_ascii=False)[:3000])
# Robots OUInégo (gratuits, tournent sur GitHub) — 3 veilles :
# 1) ouvertures de magasins des réseaux franchisés (diff des sitemaps officiels)
# 2) fournisseurs d'énergie en difficulté (BODACC + registre + presse)
# 3) alerte prix bas du marché de gros (prix spot France, energy-charts.info)
# Sorties : dossier ouinego/ ; résumé lu par la tâche « Copilote OUInégo du matin » : ouinego/synthese.json
import json, os, re, gzip, io, time, datetime, statistics, urllib.request, urllib.parse, xml.etree.ElementTree as ET

D = "ouinego"
os.makedirs(D, exist_ok=True)
NOW = datetime.datetime.now(datetime.timezone.utc)
TODAY = NOW.date().isoformat()
UA = {"User-Agent": "Mozilla/5.0 (compatible; ouinego-veille/1.0; +https://github.com/rivengodz91-arch/meteo-carnet)"}

def get(url, timeout=40, binary=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    if url.endswith(".gz") or data[:2] == b"\x1f\x8b":
        try: data = gzip.decompress(data)
        except Exception: pass
    return data if binary else data.decode("utf-8", "replace")

def getj(url, timeout=40):
    return json.loads(get(url, timeout))

def load(name, default):
    p = os.path.join(D, name)
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except Exception: return default

def save(name, obj):
    with open(os.path.join(D, name), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

ETAT = {"maj": NOW.isoformat(timespec="minutes"), "robots": {}}

# ---------------------------------------------------------------- 1) OUVERTURES
RESEAUX = load("reseaux.json", [])

def sitemap_urls(domain, limit_files=60):
    """Toutes les URL des sitemaps du site (robots.txt + emplacements classiques), parcours récursif limité.
    Renvoie aussi un diagnostic par sitemap essayé (pour corriger un réseau qui ne donne rien)."""
    seeds, diag = [], []
    try:
        for line in get(f"https://{domain}/robots.txt", 25).splitlines():
            if line.lower().startswith("sitemap:"):
                seeds.append(line.split(":", 1)[1].strip())
        diag.append(f"robots.txt ok, {len(seeds)} sitemap(s) déclaré(s)")
    except Exception as e:
        diag.append("robots.txt : " + str(e)[:80])
    for s in ("/sitemap.xml", "/sitemap_index.xml", "/sitemap-index.xml"):
        seeds.append(f"https://{domain}{s}")
    seen, todo, urls = set(), list(dict.fromkeys(seeds)), set()
    while todo and len(seen) < limit_files:
        sm = todo.pop(0)
        if sm in seen: continue
        seen.add(sm)
        try:
            txt = get(sm, 40)
        except Exception as e:
            if len(diag) < 12: diag.append(f"{sm} : {str(e)[:80]}")
            continue
        try:
            root = ET.fromstring(txt.encode("utf-8"))
        except Exception:
            if len(diag) < 12: diag.append(f"{sm} : pas du XML ({txt[:60].strip()!r})")
            continue
        n = 0
        for el in root.iter():
            if el.tag.endswith("loc") and el.text:
                u = el.text.strip(); n += 1
                if root.tag.endswith("sitemapindex"): todo.append(u)
                else: urls.add(u)
        if len(diag) < 12: diag.append(f"{sm} : {n} liens")
    return urls, len(seen), diag

CP = re.compile(r"\b((?:0[1-9]|[1-8]\d|9[0-8])\d{3})\s+([A-ZÉÈÂÎ][A-Za-zÀ-ÿ'’ -]{1,40})")
LIAISONS = {"sur", "en", "de", "du", "des", "la", "le", "les", "lès", "lez", "sous", "aux", "au", "saint", "sainte", "st", "ste", "d'"}

def _sans_accent(x):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", x.lower()) if unicodedata.category(c) != "Mn")

def _ville(brut):
    """« AMBERIEU EN BUGEY Voir » -> « AMBERIEU EN BUGEY » ; « Portet sur Garonne » garde la liaison."""
    mots, garde = brut.split(), []
    for i, w in enumerate(mots):
        if i == 0 or w.isupper() or _sans_accent(w) in LIAISONS or _sans_accent(garde[-1]) in LIAISONS:
            garde.append(w)
        else:
            break
    while garde and _sans_accent(garde[-1]) in LIAISONS:
        garde.pop()
    return " ".join(garde[:5]).strip(" -")

def verifier(u):
    """Ouvre la page d'un nouveau magasin et y lit le code postal + la ville (ceux qui collent à l'adresse de la page en priorité)."""
    try:
        h = get(u, 25)
    except Exception:
        return {"adresse": "page illisible, à vérifier"}
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h)))
    if re.search(r"aucune ouverture n.est prévue|\b0 clubs?\b", t, re.I):
        return None  # page « ville sans magasin » ou liste vide : pas une ouverture
    lien = re.sub(r"[^a-z0-9]+", " ", _sans_accent(u))
    trouves = [(m.group(1), _ville(m.group(2))) for m in CP.finditer(t)][:30]
    if not trouves:
        return {"adresse": "non lue sur la page, à vérifier"}
    bon = next(((cp, v) for cp, v in trouves if v and " " + re.sub(r"[^a-z0-9]+", " ", _sans_accent(v)).strip() + " " in " " + lien + " "), trouves[0])
    return {"cp": bon[0], "ville": bon[1]}

def robot_ouvertures():
    res = {"reseaux": {}, "nouveaux": []}
    hist = load("ouvertures.json", {"nouveaux": []})
    for R in RESEAUX:
        nom, dom, pat = R["nom"], R["domaine"], re.compile(R["motif"])
        fichier = "magasins_" + re.sub(r"[^a-z0-9]+", "-", nom.lower()).strip("-") + ".json"
        connu = load(fichier, None)
        try:
            urls, nfic, diag = sitemap_urls(dom)
            mag = sorted(u for u in urls if pat.search(u))
        except Exception as e:
            res["reseaux"][nom] = {"statut": "erreur", "detail": str(e)[:200]}; continue
        if not mag:
            ex = sorted({"/".join(u.split("/")[:5]) for u in urls})[:15]
            res["reseaux"][nom] = {"statut": "aucune fiche magasin trouvée", "sitemaps_lus": nfic, "urls_vues": len(urls), "diagnostic": diag, "exemples": ex}
            continue
        if connu is None:
            save(fichier, {"depuis": TODAY, "magasins": mag})
            res["reseaux"][nom] = {"statut": "référence créée", "magasins": len(mag), "test_page": [mag[0], verifier(mag[0])]}
            continue
        anciens = set(connu["magasins"])
        neufs = [u for u in mag if u not in anciens]
        disparus = [u for u in anciens if u not in set(mag)]
        # garde-fou : un site qui change toute sa structure ne doit pas créer 300 « ouvertures »
        if len(neufs) > max(15, 0.2 * len(anciens)):
            res["reseaux"][nom] = {"statut": "trop de changements d'un coup : vérification à la main", "nouvelles_url": len(neufs), "magasins": len(mag)}
            continue
        ignores = 0
        for u in neufs:
            v = verifier(u)
            if v is None: ignores += 1; continue
            a = dict({"reseau": nom, "lien": u}, **v)
            hist["nouveaux"].append(dict(a, date=TODAY)); res["nouveaux"].append(a)
        save(fichier, {"depuis": connu.get("depuis", TODAY), "magasins": mag})
        res["reseaux"][nom] = {"statut": "ok", "magasins": len(mag), "nouveaux": len(neufs) - ignores, "pages_sans_magasin_ignorees": ignores, "disparus": len(disparus)}
        if os.environ.get("FORCER") == "tout": res["reseaux"][nom]["test_page"] = [mag[0], verifier(mag[0])]
    hist["nouveaux"] = hist["nouveaux"][-500:]
    save("ouvertures.json", hist)
    return res

# ---------------------------------------------------------------- 2) FOURNISSEURS EN DIFFICULTÉ
API = "https://recherche-entreprises.api.gouv.fr/search"

def fournisseurs():
    """Sociétés actives de commerce d'électricité (35.14Z) et de gaz (35.23Z), liste rafraîchie chaque lundi."""
    cache = load("fournisseurs_liste.json", None)
    if cache and (NOW.weekday() != 0 or cache.get("maj") == TODAY):
        return cache["liste"]
    liste = {}
    for naf in ("35.14Z", "35.23Z"):
        for page in range(1, 61):
            try:
                j = getj(f"{API}?activite_principale={naf}&etat_administratif=A&per_page=25&page={page}&minimal=true")
            except Exception:
                time.sleep(2); continue
            for r in j.get("results", []):
                liste[r["siren"]] = r.get("nom_complet", "")
            if page >= j.get("total_pages", 1): break
            time.sleep(0.25)
    save("fournisseurs_liste.json", {"maj": TODAY, "liste": liste})
    return liste

CONNUS = ("edf", "engie", "totalenergies", "total energies", "ekwateur", "ohm energie", "ohm énergie", "mint energie", "alpiq", "vattenfall", "enercoop", "plum", "octopus", "eni gas", "eni plenitude", "plenitude", "iberdrola", "ilek", "gaz de bordeaux", "elmy", "energem", "primeo", "wekiwi", "alterna", "gedia", "sowee", "hydroption", "volterres", "selia", "met france", "gazel", "dyneff", "butagaz", "gaz europeen", "gaz européen", "proxelia", "lucia", "mega energie", "énergie d'ici", "energie d'ici", "urban solar", "barry", "happ-e", "la bellenergie", "geg", "es energies", "seolis", "sorégies", "soregies", "uem", "elecocite")
BODACC = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"
MOTS_PRESSE = ("redressement", "liquidation", "faillite", "sauvegarde", "cessation", "suspend", "retrait", "défaillance", "defaillance", "difficult", "fournisseur de secours", "fournisseur de dernier recours", "arrête", "arrete")

def robot_fournisseurs():
    res = {"alertes": []}
    vus = load("fournisseurs_vus.json", {})
    liste = fournisseurs()
    res["fournisseurs_suivis"] = len(liste)
    depuis = (NOW - datetime.timedelta(days=10)).date().isoformat()
    # a) BODACC : procédures collectives des 10 derniers jours visant un fournisseur suivi
    sirens = list(liste)
    for i in range(0, len(sirens), 40):
        lot = sirens[i:i+40]
        cond = " or ".join(f'registre like "{s}"' for s in lot)
        where = f'familleavis="collective" and dateparution>="{depuis}" and ({cond})'
        try:
            j = getj(BODACC + "?" + urllib.parse.urlencode({"where": where, "limit": 100}))
        except Exception as e:
            res.setdefault("erreurs", []).append("bodacc: " + str(e)[:120]); continue
        for r in j.get("results", []):
            cle = "bodacc:" + str(r.get("id"))
            if cle in vus: continue
            reg = re.sub(r"\D", "", json.dumps(r.get("registre", "")))
            siren = next((s for s in lot if s in reg), "")
            jug = r.get("jugement") or ""
            try: jug = json.loads(jug) if isinstance(jug, str) and jug.startswith("{") else jug
            except Exception: pass
            nature = (jug.get("nature") if isinstance(jug, dict) else "") or r.get("familleavis_lib", "")
            nomf = (liste.get(siren) or r.get("commercant", "") or "")
            a = {"source": "BODACC", "fournisseur_connu": any(c in nomf.lower() for c in CONNUS), "date": r.get("dateparution"), "fournisseur": nomf, "siren": siren,
                 "quoi": nature, "lien": r.get("url_complete") or f"https://www.bodacc.fr/pages/annonces-commerciales-detail/?q.id=id:{r.get('id')}"}
            res["alertes"].append(a); vus[cle] = TODAY
        time.sleep(0.3)
    # b) Presse (Google Actualités, RSS) : mots-clés de difficulté + fournisseur d'énergie
    reqs = ['"fournisseur d\'électricité" (redressement OR liquidation OR faillite OR "cessation d\'activité")',
            '"fournisseur d\'énergie" (redressement OR liquidation OR faillite OR "suspend" OR "défaillance")',
            '"fournisseur de secours" électricité', '"fournisseur de dernier recours" gaz OR électricité']
    for q in reqs:
        try:
            x = get("https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": q + " when:7d", "hl": "fr", "gl": "FR", "ceid": "FR:fr"}), 30)
            root = ET.fromstring(x.encode("utf-8"))
        except Exception as e:
            res.setdefault("erreurs", []).append("presse: " + str(e)[:120]); continue
        for it in root.iter("item"):
            t = (it.findtext("title") or "").strip(); l = (it.findtext("link") or "").strip()
            if not t or not any(m in t.lower() for m in MOTS_PRESSE): continue
            cle = "presse:" + re.sub(r"\W+", "", t.lower())[:90]
            if cle in vus: continue
            res["alertes"].append({"source": "Presse", "date": TODAY, "fournisseur": "", "quoi": t, "lien": l}); vus[cle] = TODAY
        time.sleep(0.5)
    # c) Registre : fournisseur suivi la semaine dernière et radié depuis (lundi seulement)
    ancienne = load("fournisseurs_liste_prec.json", None)
    if NOW.weekday() == 0:
        if ancienne:
            for s, n in ancienne.get("liste", {}).items():
                if s not in liste and ("radie:" + s) not in vus:
                    try:
                        j = getj(f"{API}?q={s}&minimal=true")
                        r = next((x for x in j.get("results", []) if x["siren"] == s), None)
                    except Exception: r = None
                    if r and r.get("etat_administratif") == "C":
                        res["alertes"].append({"source": "Registre", "date": TODAY, "fournisseur": n, "siren": s, "quoi": "société cessée (radiée du registre)", "lien": f"https://annuaire-entreprises.data.gouv.fr/entreprise/{s}"})
                        vus["radie:" + s] = TODAY
        save("fournisseurs_liste_prec.json", {"maj": TODAY, "liste": liste})
    save("fournisseurs_vus.json", vus)
    hist = load("fournisseurs.json", {"alertes": []})
    hist["alertes"] = (hist["alertes"] + [dict(a, vu_le=TODAY) for a in res["alertes"]])[-300:]
    save("fournisseurs.json", hist)
    return res

# ---------------------------------------------------------------- 3) PRIX BAS DU MARCHÉ
def robot_prix():
    """Prix spot day-ahead France (€/MWh), source energy-charts.info (Fraunhofer ISE, données EPEX/ENTSO-E)."""
    hist = load("prix.json", {"jours": {}})
    debut = (NOW - datetime.timedelta(days=400 if len(hist["jours"]) < 300 else 10)).date().isoformat()
    j = getj(f"https://api.energy-charts.info/price?bzn=FR&start={debut}&end={TODAY}", 60)
    par_jour = {}
    for ts, p in zip(j.get("unix_seconds", []), j.get("price", [])):
        if p is None: continue
        d = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).date().isoformat()
        par_jour.setdefault(d, []).append(p)
    for d, v in par_jour.items():
        if len(v) >= 20: hist["jours"][d] = round(sum(v) / len(v), 2)
    jours = sorted(hist["jours"])
    hist["jours"] = {d: hist["jours"][d] for d in jours[-420:]}
    jours = sorted(hist["jours"])
    vals = [hist["jours"][d] for d in jours]
    res = {"source": "energy-charts.info (prix spot day-ahead France, moyenne journalière base)"}
    if len(vals) < 60:
        res["statut"] = "historique trop court"; save("prix.json", hist); return res
    m7 = sum(vals[-7:]) / 7
    m30 = sum(vals[-30:]) / 30
    an = vals[-365:]
    rang = sum(1 for x in an if x <= m7) / len(an)  # part des jours de l'année moins chers que la moyenne 7 j
    q20 = sorted(an)[int(0.2 * (len(an) - 1))]
    res.update({"dernier_jour": jours[-1], "moy_7j": round(m7, 1), "moy_30j": round(m30, 1), "moy_365j": round(sum(an) / len(an), 1),
                "seuil_bas_20pct": round(q20, 1), "rang_7j_sur_an_pct": round(100 * rang)})
    alerte = None
    if m7 <= q20:
        alerte = f"Prix spot au plus bas : moyenne 7 jours {m7:.0f} €/MWh, parmi les 20 % les plus bas de l'année (moyenne 1 an : {sum(an)/len(an):.0f} €/MWh)."
    elif m7 <= 0.85 * m30:
        alerte = f"Prix spot en forte baisse : moyenne 7 jours {m7:.0f} €/MWh, soit {100*(1-m7/m30):.0f} % sous la moyenne 30 jours ({m30:.0f} €/MWh)."
    der = hist.get("derniere_alerte")
    if alerte and der and (NOW.date() - datetime.date.fromisoformat(der)).days < 7:
        res["alerte_deja_envoyee_le"] = der; alerte = None  # pas plus d'une alerte par semaine
    if alerte:
        hist["derniere_alerte"] = TODAY
    res["alerte"] = alerte
    save("prix.json", hist)
    return res

# ---------------------------------------------------------------- lancement
SYN = load("synthese.json", {"historique": []})
nouv = {"date": TODAY}
quand = os.environ.get("FORCER", "")
for nom, fn, jours in (("ouvertures", robot_ouvertures, {0}), ("fournisseurs", robot_fournisseurs, {0,1,2,3,4,5,6}), ("prix", robot_prix, {0,1,2,3,4,5,6})):
    if NOW.weekday() not in jours and nom not in quand and quand != "tout":
        continue
    try:
        r = fn(); ETAT["robots"][nom] = {"statut": "ok", "resultat": r}
        if nom == "ouvertures" and r.get("nouveaux"): nouv["ouvertures"] = r["nouveaux"]
        if nom == "fournisseurs" and r.get("alertes"): nouv["fournisseurs"] = r["alertes"]
        if nom == "prix" and r.get("alerte"): nouv["prix"] = r["alerte"]
    except Exception as e:
        ETAT["robots"][nom] = {"statut": "erreur", "detail": f"{type(e).__name__}: {str(e)[:300]}"}
SYN["maj"] = ETAT["maj"]
SYN["etat"] = {k: v["statut"] for k, v in ETAT["robots"].items()}
if len(nouv) > 1:
    SYN["historique"] = [h for h in SYN["historique"] if h.get("date") != TODAY] + [nouv]
SYN["historique"] = SYN["historique"][-60:]
save("synthese.json", SYN)
save("etat.json", ETAT)
print(json.dumps(ETAT, ensure_ascii=False)[:3000])

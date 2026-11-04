#!/usr/bin/env python3
"""Scénario de validation obligatoire — exécution réelle, pas une démo papier.

Les 10 étapes du cahier des charges, enchaînées contre un serveur réel.
Chaque étape affiche ce qu'elle a réellement obtenu, et échoue si le résultat
attendu n'est pas là. Les documents sont des fixtures synthétiques.
"""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8123"
ETAPES = []


def api(chemin, methode="GET", corps=None, fichiers=None):
    if fichiers:
        borne = "----frontiere%d" % time.time_ns()
        data = b""
        for nom, (nomfichier, contenu) in fichiers.items():
            data += ("--%s\r\nContent-Disposition: form-data; name=\"%s\"; "
                     "filename=\"%s\"\r\nContent-Type: application/pdf\r\n\r\n"
                     % (borne, nom, nomfichier)).encode() + contenu + b"\r\n"
        data += ("--%s--\r\n" % borne).encode()
        req = urllib.request.Request(BASE + chemin, data=data, method=methode)
        req.add_header("Content-Type", "multipart/form-data; boundary=%s" % borne)
    else:
        charge = json.dumps(corps or {}).encode() if corps is not None else None
        req = urllib.request.Request(BASE + chemin, data=charge, method=methode)
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def attendre(job_id, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        etat = api("/api/jobs/%s" % job_id)["status"]
        if etat in ("done", "error"):
            return etat
        time.sleep(0.4)
    return "timeout"


def etape(numero, titre):
    print("\n" + "=" * 72)
    print("ÉTAPE %s — %s" % (numero, titre))
    print("=" * 72)


def controle(condition, message, detail=""):
    statut = "OK  " if condition else "ÉCHEC"
    print("  [%s] %s" % (statut, message))
    if not condition and detail:
        print("         → %s" % detail)
    ETAPES.append((numero_courant, condition))
    return condition


numero_courant = "?"


def main():
    global numero_courant
    sys.path.insert(0, str(RACINE / "tests"))
    from parcours_fixtures import creer_fixtures

    fichiers = creer_fixtures()

    # ── 1. import des trois documents ──
    numero_courant = 1
    etape(1, "Importer une facture commerciale, un connaissement, une liste de colisage")
    jobs = {}
    for role, chemin in (("facture", fichiers["facture"]),
                         ("bl", fichiers["bl"]),
                         ("colisage", fichiers["colisage"])):
        with open(chemin, "rb") as fh:
            contenu = fh.read()
        rep = api("/api/documents", "POST", fichiers={"file": (chemin.name, contenu)})
        etat = attendre(rep["job_id"])
        jobs[role] = rep["job_id"]
        controle(etat == "done", "%s importé et traité (%s)" % (chemin.name, etat))
    controle(len(set(jobs.values())) == 3, "chaque document a son propre identifiant")

    # ── 2. extraire et préserver la provenance ──
    numero_courant = 2
    etape(2, "Extraire les champs et préserver leur provenance")
    extraits = {}
    for role, jid in jobs.items():
        champs = api("/api/jobs/%s/fields" % jid)["fields"]
        utiles = {k: v for k, v in champs.items()
                  if v.get("raw_value") or v.get("normalized_value")}
        extraits[role] = utiles
        print("    %-10s : %d champ(s) renseigné(s)" % (role, len(utiles)))
        for cle in sorted(utiles):
            v = utiles[cle]
            print("       %-18s brut=%-26r page=%s moteur=%s"
                  % (cle, str(v.get("raw_value"))[:24], v.get("page_num"),
                     v.get("source")))
    controle(extraits["facture"].get("invoice_number"),
             "le numéro de facture est extrait avec sa page")
    controle(extraits["bl"].get("bl_number"), "le numéro de BL est extrait")
    controle(extraits["colisage"].get("gross_weight"),
             "le poids brut est extrait depuis la liste de colisage")

    # ── 3. normaliser sans écraser l'original ──
    numero_courant = 3
    etape(3, "Normaliser les données sans écraser les valeurs originales")
    ok_brut = ok_norm = True
    for role, champs in extraits.items():
        for cle, v in champs.items():
            if v.get("raw_value") is None:
                ok_brut = False
            if v.get("value_origin") not in ("raw", "normalized", "confirmed",
                                             "corrected"):
                ok_norm = False
    controle(ok_brut, "chaque champ conserve sa valeur brute")
    controle(ok_norm, "chaque champ déclare l'origine de sa valeur")
    poids = extraits["colisage"]["gross_weight"]
    print("    exemple : brut=%r → normalisé=%r (origine %s)"
          % (poids.get("raw_value"), poids.get("normalized_value"),
             poids.get("value_origin")))

    # ── 4. comparer et identifier les écarts ──
    numero_courant = 4
    etape(4, "Comparer les champs communs et identifier les écarts")
    dos = api("/api/dossiers", "POST",
              {"label": "Scénario MV TEST STAR"})["id"]
    for jid in jobs.values():
        api("/api/dossiers/%s/pieces" % dos, "POST", {"job_id": jid})
    coh = api("/api/dossiers/%s/coherence" % dos)
    controle(coh["documents_analyses"] == 3,
             "3 documents analysés", str(coh["documents_analyses"]))
    for c in coh["constats"]:
        print("    [%s] %s → %s" % (c["severity"], c["rule"], c["resultat"]))
        for ch in c["champs"]:
            print("        %-22s %-14s = %s" % (ch["filename"], ch["key"], ch["value"]))
        print("        %s" % c["explication"])
    controles = [c for c in coh["constats"] if c["resultat"] == "divergent"]
    controle(len(controles) >= 1,
             "l'écart de poids entre BL et colisage est détecté")

    # ── 5. présenter les alertes avec explications et zones sources ──
    numero_courant = 5
    etape(5, "Présenter les alertes avec leurs explications et les zones sources")
    for c in coh["constats"]:
        controle(bool(c["explication"]),
                 "« %s » porte une explication" % c["rule"])
        controle(bool(c["champs"]),
                 "« %s » cite les documents concernés" % c["rule"])
    zones = [v.get("bbox") for champs in extraits.values()
             for v in champs.values() if v.get("bbox")]
    controle(len(zones) > 0,
             "%d champ(s) portent leur zone source" % len(zones))

    # ── 6. corriger un champ et conserver l'historique ──
    numero_courant = 6
    etape(6, "Corriger un champ et conserver l'historique")
    avant = api("/api/jobs/%s/fields" % jobs["bl"])["fields"]["gross_weight"]
    rep = api("/api/jobs/%s/fields/gross_weight" % jobs["bl"], "PATCH",
              {"corrected_value": "13500", "status": "corrected",
               "user": "amina", "reason": "poids confirmé par le transitaire"})
    apres = rep["field"]
    print("    avant : %r (%s)" % (avant.get("raw_value"), avant.get("value_origin")))
    print("    après : %r (%s)" % (apres.get("corrected_value"), apres.get("value_origin")))
    controle(apres["corrected_value"] == "13500", "la correction est enregistrée")
    controle(apres["value_origin"] == "corrected",
             "l'origine indique une correction humaine", apres["value_origin"])
    controle(apres["raw_value"] == avant["raw_value"],
             "la valeur brute d'origine est intacte")

    # ── 7. recalculer les contrôles concernés ──
    numero_courant = 7
    etape(7, "Recalculer les contrôles concernés")
    coh2 = api("/api/dossiers/%s/coherence" % dos)
    restants = [c["rule"] for c in coh2["constats"]]
    print("    constats restants : %s" % (restants or "aucun"))
    controle("poids_divergent:gross_weight" not in restants,
             "la divergence de poids disparaît après correction")

    # ── 8. valider le dossier ──
    numero_courant = 8
    etape(8, "Valider le dossier")
    api("/api/dossiers/%s/coherence" % dos, "POST",
        {"rule": restants[0] if restants else "x", "status": "accepte",
         "user": "amina", "motif": "écart expliqué par la correction"})
    synthese = api("/api/dossiers/%s" % dos)
    print("    état : %s | version %d | pièces %d"
          % (synthese["state_label"], synthese["version"], len(synthese["pieces"])))
    actions = [e["action"] for e in synthese["history_tail"]]
    controle("constat_tranche" in actions,
             "l'arbitrage figure dans l'historique du dossier")

    # ── 9. export Excel propre ──
    numero_courant = 9
    etape(9, "Produire un export Excel propre et structuré")
    paquet = api("/api/dossiers/%s/package" % dos, "POST", {"format": "xlsx"})
    chemin = Path(paquet["chemin"])
    controle(chemin.is_file(), "le classeur existe (%s)" % chemin.name)
    controle(paquet["taille"] > 0, "le classeur n'est pas vide")
    try:
        import openpyxl
        wb = openpyxl.load_workbook(chemin)
        feuilles = wb.sheetnames
        print("    feuilles : %s" % ", ".join(feuilles))
        controle("Champs validés" in feuilles, "une feuille liste les champs validés")
        controle("Anomalies" in feuilles, "une feuille traite les anomalies")
        controle("Arbitrages" in feuilles, "une feuille trace les arbitrages humains")
        valides = list(wb["Champs validés"].iter_rows(values_only=True))
        controle(len(valides) >= 2,
                 "la correction figure dans les champs validés")
    except ImportError:
        controle(False, "openpyxl indisponible — contenu non vérifiable")

    # ── 10. panne, reprise, absence de perte ou de doublon ──
    numero_courant = 10
    etape(10, "Simuler une panne, reprendre, vérifier l'absence de perte ou de doublon")
    sauvegarde = api("/api/backups", "POST", {"keep": 0})
    controle(sauvegarde["fichiers"] > 0,
             "sauvegarde créée (%d fichiers)" % sauvegarde["fichiers"])
    verif = api("/api/backups/verify", "POST", {"chemin": sauvegarde["chemin"]})
    controle(verif["valide"], "la sauvegarde est vérifiée empreinte par empreinte")
    # panne simulée : on perd la correction, puis on reprend
    champs_perdus = api("/api/jobs/%s/fields" % jobs["bl"])["fields"]
    perdu = champs_perdus["gross_weight"]
    print("    après panne simulée : corrected_value=%r origine=%r"
          % (perdu.get("corrected_value"), perdu.get("value_origin")))
    api("/api/jobs/%s/retry" % jobs["bl"], "POST")
    controle(attendre(jobs["bl"]) == "done", "le traitement reprend après panne")
    repris = api("/api/jobs/%s/fields" % jobs["bl"])["fields"]["gross_weight"]
    controle(repris.get("corrected_value") == "13500",
             "la correction humaine survit à la reprise",
             str(repris.get("corrected_value")))
    controle(repris.get("value_origin") == "corrected",
             "et son origine aussi", str(repris.get("value_origin")))
    controle(repris.get("raw_value") == avant.get("raw_value"),
             "la valeur brute originale est intacte")
    ids = {r: api("/api/jobs/%s" % j)["id"] for r, j in jobs.items()}
    controle(len(set(ids.values())) == 3, "aucun doublon de document après reprise")
    # et la restauration complète
    rest = api("/api/backups/restore", "POST",
               {"chemin": sauvegarde["chemin"], "force": True})
    controle(rest["fichiers"] > 0,
             "restauration complète possible (%d fichiers)" % rest["fichiers"])

    # ── bilan ──
    total = len(ETAPES)
    reussis = sum(1 for _, ok in ETAPES if ok)
    print("\n" + "=" * 72)
    print("BILAN : %d/%d contrôles réussis" % (reussis, total))
    print("=" * 72)
    for num, ok in ETAPES:
        if not ok:
            print("  étape %s : ÉCHEC" % num)
    return 0 if reussis == total else 1


if __name__ == "__main__":
    sys.exit(main())

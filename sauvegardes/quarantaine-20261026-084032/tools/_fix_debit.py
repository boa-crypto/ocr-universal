import io

p = "/home/user/ocr-universal/src/unocr/api.py"
src = io.open(p, encoding="utf-8").read()

ancien = '''@app.middleware("http")
async def _limitation_debit(request, call_next):
    """Refuse le depassement, avec la date de retry disponible.

    Volontairement en memoire et par adresse cliente : cela protege d'une
    boucle de reimport accidentelle, pas d'un attaquant distribue. Le journal
    le dit, plutôt que de laisser croire a une protection absolue.
    """
    chemin = request.url.path
    if chemin.startswith("/api/") and chemin not in _DEBIT_EXEMPT:
        client = request.client.host if request.client else "inconnu"
        autorise, attente = _compteur.autorise(client)
        if not autorise:
            log.warning("dépassement de débit pour %s sur %s (attente %.1fs)",
                        client, chemin, attente)
            return JSONResponse(
                {"detail": "trop de requêtes, réessayer plus tard",
                 "retry_after": round(attente, 1)},
                status_code=429,
                headers={"Retry-After": str(int(attente) + 1)})
    return await call_next(request)'''

nouveau = '''#: methodes soumises a la limitation. Les lectures en sont exclues : l'interface
#: interroge /api/jobs/{id} en boucle pendant un traitement par lot, et brider
#: ce polling ferait echouer des traitements parfaitement legitimes. Ce qu'on
#: veut empecher, c'est l'empilement d'ecritures (reimports, transmissions).
_METHODES_LIMITEES = frozenset({"POST", "PUT", "PATCH", "DELETE"})


@app.middleware("http")
async def _limitation_debit(request, call_next):
    """Refuse le depassement, avec la date de retry disponible.

    Volontairement en memoire et par adresse cliente : cela protege d'une
    boucle de reimport accidentelle, pas d'un attaquant distribue. Le journal
    le dit, plutot que de laisser croire a une protection absolue.
    """
    chemin = request.url.path
    if (request.method in _METHODES_LIMITEES
            and chemin.startswith("/api/") and chemin not in _DEBIT_EXEMPT):
        client = request.client.host if request.client else "inconnu"
        autorise, attente = _compteur.autorise(client)
        if not autorise:
            log.warning("depassement de debit pour %s sur %s (attente %.1fs)",
                        client, chemin, attente)
            return JSONResponse(
                {"detail": "trop de requetes, reessayer plus tard",
                 "retry_after": round(attente, 1)},
                status_code=429,
                headers={"Retry-After": str(int(attente) + 1)})
    return await call_next(request)'''

assert src.count(ancien) == 1, src.count(ancien)
io.open(p, "w", encoding="utf-8").write(src.replace(ancien, nouveau, 1))
print("limitation restreinte aux ecritures")

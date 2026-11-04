"""Observabilité : identifiants de corrélation et limitation de débit.

Deux manques constatés à l'audit :

1. **Aucun identifiant de corrélation.** Une requête qui échoue ne peut pas
   être rattachée à ce que l'opérateur a fait, ni aux lignes de journal
   produites pendant son traitement. Un document de 40 pages génère des
   centaines de lignes : sans `request_id`, elles sont inexploitables.

2. **Aucune limitation de débit.** Une boucle de réimport peut saturer le
   magasin et le disque. Le moteur borne déjà les jobs concurrents
   (`jobs.workers`), mais rien n'empêche d'empiler les *demandes*.

Le choix retenu : un middleware unique, sans dépendance externe (le projet
tourne hors réseau). La limitation est **par adresse cliente**, en mémoire,
avec une fenêtre glissante — elle protège d'un abus, pas d'un attaquant
distribué, et le journal le dit.
"""
from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field

from .logging_setup import get_logger

log = get_logger("observabilite")

#: en-tête renvoyé au client, pour qu'il puisse citer l'identifiant
HEADER_CORRELATION = "X-Request-ID"


def nouvel_identifiant() -> str:
    """Identifiant court, lisible dans un journal et dicable au téléphone."""
    return uuid.uuid4().hex[:12]


@dataclass
class CompteurDebit:
    """Fenêtre glissante par client.

    Une fenêtre glissante plutôt qu'un compteur remis à zéro à l'heure :
    un compteur fixe laisse passer 2×la limite à cheval sur deux fenêtres.
    """
    limite: int = 60                 # requêtes…
    fenetre: float = 60.0            # …par fenêtre, en secondes
    evenements: dict[str, deque] = field(default_factory=lambda: defaultdict(deque))
    verrou: threading.Lock = field(default_factory=threading.Lock)
    actif: bool = True

    def autorise(self, cle: str) -> tuple[bool, float]:
        """(autorisé, secondes avant la prochaine place libre)."""
        if not self.actif:
            return True, 0.0
        maintenant = time.monotonic()
        with self.verrou:
            file = self.evenements[cle]
            while file and maintenant - file[0] > self.fenetre:
                file.popleft()
            if len(file) >= self.limite:
                attente = self.fenetre - (maintenant - file[0])
                return False, max(0.0, attente)
            file.append(maintenant)
            return True, 0.0

    def etat(self) -> dict:
        with self.verrou:
            return {"limite": self.limite, "fenetre_s": self.fenetre,
                    "clients_suivis": len(self.evenements), "actif": self.actif}

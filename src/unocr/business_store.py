"""Stockage local des modules métier, partagé entre instances du serveur.

Chaque objet est un document JSON validé par son modèle Pydantic. Les écritures
sont transactionnelles ; une lecture restitue une copie, donc une modification
non sauvegardée ne peut pas contaminer les lectures suivantes. Ce magasin ne
constitue pas un journal de transitions. Les routes peuvent grouper plusieurs
collections dans une transaction explicite.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
U = TypeVar("U", bound=BaseModel)


class BusinessStore(MutableMapping[str, T], Generic[T]):
    def __init__(self, path: Path, collection: str, model: type[T],
                 *, _connection: sqlite3.Connection | None = None):
        self.path = path
        self.collection = collection
        self.model = model
        self._connection = _connection
        if _connection is not None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS objects ("
                       "collection TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, "
                       "PRIMARY KEY (collection, id))")

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if self._connection is not None:
            yield self._connection
            return
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self) -> Iterator[BusinessStore[T]]:
        """Réserve l'écriture avant les contrôles ; rollback sur toute exception."""
        if self._connection is not None:
            yield self
            return
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            yield BusinessStore(self.path, self.collection, self.model, _connection=db)

    def related(self, collection: str, model: type[U]) -> BusinessStore[U]:
        """Autre collection dans la transaction courante, sans seconde connexion."""
        if self._connection is None:
            raise RuntimeError("related exige une transaction active")
        return BusinessStore(self.path, collection, model, _connection=self._connection)

    def __getitem__(self, key: str) -> T:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM objects WHERE collection=? AND id=?",
                             (self.collection, key)).fetchone()
        if row is None:
            raise KeyError(key)
        return self.model.model_validate_json(row[0])

    def __setitem__(self, key: str, value: T) -> None:
        payload = self.model.model_validate(value.model_dump()).model_dump_json()
        with self._connect() as db:
            db.execute("INSERT INTO objects(collection,id,payload) VALUES(?,?,?) "
                       "ON CONFLICT(collection,id) DO UPDATE SET payload=excluded.payload",
                       (self.collection, key, payload))

    def __delitem__(self, key: str) -> None:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM objects WHERE collection=? AND id=?",
                                (self.collection, key))
            if cursor.rowcount == 0:
                raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        with self._connect() as db:
            rows = db.execute("SELECT id FROM objects WHERE collection=? ORDER BY id",
                              (self.collection,)).fetchall()
        return iter(row[0] for row in rows)

    def __len__(self) -> int:
        with self._connect() as db:
            return db.execute("SELECT COUNT(*) FROM objects WHERE collection=?",
                              (self.collection,)).fetchone()[0]

    def values(self) -> list[T]:
        with self._connect() as db:
            rows = db.execute("SELECT payload FROM objects WHERE collection=? ORDER BY id",
                              (self.collection,)).fetchall()
        return [self.model.model_validate_json(row[0]) for row in rows]

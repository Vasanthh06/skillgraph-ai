"""User-scoped data access: the ONLY way application code touches user-owned tables.

A `UserScope` is built from the authenticated user's id. Every read injects `user_id == <that id>` and every
write forces `obj.user_id = <that id>`, so a handler cannot read or write another user's rows even by mistake.
Callers never pass a user id into queries. tests/test_isolation_static.py fails the build if API or service code
queries user-owned models directly instead of going through here.
"""
from __future__ import annotations

from typing import Any, TypeVar

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class NotOwned(Exception):
    """Raised when a record exists but belongs to someone else (surfaced to clients as 404)."""


class UserScope:
    def __init__(self, db: Session, user_id: str):
        if not user_id:
            raise ValueError("UserScope requires an authenticated user id")
        self.db, self.user_id = db, user_id

    # ---- reads ----
    def _guard(self, model: type) -> None:
        if not hasattr(model, "user_id"):
            raise TypeError(f"{model.__name__} is not a user-owned model")

    def query(self, model: type[T], *where: Any):
        self._guard(model)
        return select(model).where(model.user_id == self.user_id, *where)  # type: ignore[attr-defined]

    def all(self, model: type[T], *where: Any, order_by: Any = None, limit: int | None = None) -> list[T]:
        q = self.query(model, *where)
        if order_by is not None:
            q = q.order_by(*(order_by if isinstance(order_by, (list, tuple)) else [order_by]))
        if limit:
            q = q.limit(limit)
        return list(self.db.scalars(q))

    def first(self, model: type[T], *where: Any, order_by: Any = None) -> T | None:
        q = self.query(model, *where)
        if order_by is not None:
            q = q.order_by(*(order_by if isinstance(order_by, (list, tuple)) else [order_by]))
        return self.db.scalars(q.limit(1)).first()

    def count(self, model: type, *where: Any) -> int:
        self._guard(model)
        return self.db.scalar(select(func.count()).select_from(model).where(model.user_id == self.user_id, *where)) or 0  # type: ignore[attr-defined]

    # ---- writes ----
    def add(self, obj: T) -> T:
        self._guard(type(obj))
        obj.user_id = self.user_id  # type: ignore[attr-defined]  # ownership is forced, never trusted from the caller
        self.db.add(obj)
        return obj

    def delete_where(self, model: type, *where: Any) -> None:
        self._guard(model)
        self.db.execute(delete(model).where(model.user_id == self.user_id, *where))  # type: ignore[attr-defined]

    def upsert(self, model: type[T], keys: dict[str, Any], **values: Any) -> T:
        """Fetch-or-create the user's row identified by `keys`, then set `values`."""
        row = self.first(model, *[getattr(model, k) == v for k, v in keys.items()])
        if row is None:
            row = self.add(model(**keys))
        for k, v in values.items():
            setattr(row, k, v)
        return row

    def owned_child_ids(self, parent_model: type, parent_id: int) -> bool:
        """True only if `parent_id` is a row of `parent_model` owned by this user (guards child tables such as
        resume_skills and roadmap_items, which have no user_id of their own)."""
        return self.first(parent_model, parent_model.id == parent_id) is not None  # type: ignore[attr-defined]

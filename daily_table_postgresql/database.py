"""PostgreSQL persistence for Daily Table."""

from datetime import date
import os

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


def _setting(name):
    try:
        value = st.secrets.get(name)
    except (FileNotFoundError, KeyError):
        value = None
    return str(value) if value is not None else os.getenv(name)


def _database_url():
    url = _setting("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")

    # SQLAlchemy must be told to use psycopg 3 explicitly. These replacements
    # also accept the URLs commonly copied from managed PostgreSQL providers.
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


@st.cache_resource
def engine():
    return create_engine(
        _database_url(),
        pool_pre_ping=True,
        pool_recycle=300,
    )


def _date(value):
    return date.fromisoformat(value) if isinstance(value, str) else value


@st.cache_resource
def init_db():
    """Create the schema once and seed the 20 initial profiles."""
    statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id BIGSERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE,
            active BOOLEAN NOT NULL DEFAULT TRUE
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS menu (
            id BIGSERIAL PRIMARY KEY,
            menu_date DATE NOT NULL UNIQUE,
            main_dish TEXT NOT NULL,
            side_dish TEXT,
            salad TEXT,
            dessert TEXT,
            notes TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS ratings (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            menu_date DATE NOT NULL,
            food_choice SMALLINT NOT NULL CHECK (food_choice BETWEEN 1 AND 5),
            taste SMALLINT NOT NULL CHECK (taste BETWEEN 1 AND 5),
            cleanliness SMALLINT NOT NULL CHECK (cleanliness BETWEEN 1 AND 5),
            service SMALLINT NOT NULL CHECK (service BETWEEN 1 AND 5),
            comment VARCHAR(500),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, menu_date)
        )
        """,
        "CREATE INDEX IF NOT EXISTS ratings_menu_date_idx ON ratings(menu_date)",
        "ALTER TABLE menu ADD COLUMN IF NOT EXISTS dessert TEXT",
    ]

    with engine().begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        connection.execute(text("""
            INSERT INTO users(name)
            SELECT 'User ' || n FROM generate_series(1, 20) AS n
            ON CONFLICT (name) DO NOTHING
        """))


def users():
    with engine().connect() as connection:
        rows = connection.execute(text(
            "SELECT id, name FROM users WHERE active = TRUE ORDER BY name"
        )).mappings().all()
    return [dict(row) for row in rows]


def menu_between(start, end):
    with engine().connect() as connection:
        rows = connection.execute(text("""
            SELECT menu_date, main_dish, side_dish, salad, dessert, notes
            FROM menu
            WHERE menu_date BETWEEN :start AND :end
            ORDER BY menu_date
        """), {"start": _date(start), "end": _date(end)}).mappings().all()
    return {row["menu_date"].isoformat(): dict(row) for row in rows}


def rating_for(user_id, menu_date):
    with engine().connect() as connection:
        row = connection.execute(text("""
            SELECT food_choice, taste, cleanliness, service, comment
            FROM ratings
            WHERE user_id = :user_id AND menu_date = :menu_date
        """), {"user_id": user_id, "menu_date": _date(menu_date)}).mappings().first()
    return dict(row) if row else None


def save_rating(user_id, menu_date, vals, comment):
    food_choice, taste, cleanliness, service = vals
    with engine().begin() as connection:
        connection.execute(text("""
            INSERT INTO ratings(
                user_id, menu_date, food_choice, taste, cleanliness, service, comment
            ) VALUES (
                :user_id, :menu_date, :food_choice, :taste, :cleanliness, :service, :comment
            )
            ON CONFLICT (user_id, menu_date) DO UPDATE SET
                food_choice = EXCLUDED.food_choice,
                taste = EXCLUDED.taste,
                cleanliness = EXCLUDED.cleanliness,
                service = EXCLUDED.service,
                comment = EXCLUDED.comment,
                updated_at = CURRENT_TIMESTAMP
        """), {
            "user_id": user_id,
            "menu_date": _date(menu_date),
            "food_choice": food_choice,
            "taste": taste,
            "cleanliness": cleanliness,
            "service": service,
            "comment": comment,
        })


def save_menu(menu_date, main, side, salad, dessert, notes):
    with engine().begin() as connection:
        connection.execute(text("""
            INSERT INTO menu(menu_date, main_dish, side_dish, salad, dessert, notes)
            VALUES (:menu_date, :main, :side, :salad, :dessert, :notes)
            ON CONFLICT (menu_date) DO UPDATE SET
                main_dish = EXCLUDED.main_dish,
                side_dish = EXCLUDED.side_dish,
                salad = EXCLUDED.salad,
                dessert = EXCLUDED.dessert,
                notes = EXCLUDED.notes
        """), {
            "menu_date": _date(menu_date),
            "main": main,
            "side": side,
            "salad": salad,
            "dessert": dessert,
            "notes": notes,
        })


def stats_between(start, end):
    query = text("""
        SELECT
            CAST(r.menu_date AS TEXT) AS "Date",
            COUNT(*) AS "Responses",
            CAST(ROUND(AVG(r.food_choice), 2) AS DOUBLE PRECISION) AS "Food choice",
            CAST(ROUND(AVG(r.taste), 2) AS DOUBLE PRECISION) AS "Taste",
            CAST(ROUND(AVG(r.cleanliness), 2) AS DOUBLE PRECISION) AS "Cleanliness",
            CAST(ROUND(AVG(r.service), 2) AS DOUBLE PRECISION) AS "Service",
            CAST(ROUND(AVG((r.food_choice+r.taste+r.cleanliness+r.service)/4.0), 2) AS DOUBLE PRECISION) AS "Overall"
        FROM ratings r
        WHERE r.menu_date BETWEEN :start AND :end
        GROUP BY r.menu_date
        ORDER BY r.menu_date
    """)
    with engine().connect() as connection:
        return pd.read_sql_query(query, connection, params={"start": _date(start), "end": _date(end)})


def individuals_between(start, end):
    query = text("""
        SELECT
            CAST(r.menu_date AS TEXT) AS "Date",
            u.name AS "User",
            r.food_choice AS "Food choice",
            r.taste AS "Taste",
            r.cleanliness AS "Cleanliness",
            r.service AS "Service",
            CAST(ROUND((r.food_choice+r.taste+r.cleanliness+r.service)/4.0, 2) AS DOUBLE PRECISION) AS "Overall",
            COALESCE(r.comment, '') AS "Comment"
        FROM ratings r
        JOIN users u ON u.id = r.user_id
        WHERE r.menu_date BETWEEN :start AND :end
        ORDER BY r.menu_date DESC, u.name
    """)
    with engine().connect() as connection:
        return pd.read_sql_query(query, connection, params={"start": _date(start), "end": _date(end)})


def rename_profile(uid, new_name):
    with engine().begin() as connection:
        connection.execute(text(
            "UPDATE users SET name = :name WHERE id = :uid"
        ), {"name": new_name.strip(), "uid": uid})


def delete_rating(uid, menu_date):
    with engine().begin() as connection:
        connection.execute(text("""
            DELETE FROM ratings
            WHERE user_id = :uid AND menu_date = :menu_date
        """), {"uid": uid, "menu_date": _date(menu_date)})


__all__ = [
    "IntegrityError", "delete_rating", "individuals_between", "init_db",
    "menu_between", "rating_for", "rename_profile", "save_menu",
    "save_rating", "stats_between", "users",
]

import os
from datetime import date

import pandas as pd
import pytest
from sqlalchemy import create_engine, inspect, text

from load_postgres import (
    compute_and_store_daily_metrics,
    create_tables_if_not_exist,
    get_database_url,
    load_sales_data,
)


@pytest.fixture(scope="module")
def engine():
    required = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        pytest.skip("Variables d'environnement PostgreSQL manquantes: %s" % ", ".join(missing))

    engine = create_engine(get_database_url())
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def cleanup_tables(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS sales_daily_metrics"))
        conn.execute(text("DROP TABLE IF EXISTS sales_raw"))
    yield
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS sales_daily_metrics"))
        conn.execute(text("DROP TABLE IF EXISTS sales_raw"))


def test_create_tables_if_not_exist(engine):
    create_tables_if_not_exist(engine)
    inspector = inspect(engine)

    assert inspector.has_table("sales_raw")
    assert inspector.has_table("sales_daily_metrics")


def test_load_sales_data_idempotence(engine):
    create_tables_if_not_exist(engine)
    df = pd.DataFrame(
        [
            {
                "date": "2026-01-01",
                "produit_id": "p1",
                "produit_nom": "Produit A",
                "quantite": 2,
                "prix_unitaire": 10.0,
                "magasin_id": "m1",
            },
            {
                "date": "2026-01-01",
                "produit_id": "p2",
                "produit_nom": "Produit B",
                "quantite": 1,
                "prix_unitaire": 20.0,
                "magasin_id": "m1",
            },
        ]
    )

    load_sales_data(engine, df)
    load_sales_data(engine, df)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM sales_raw"))
        assert result.scalar_one() == 2


def test_compute_and_store_daily_metrics(engine):
    create_tables_if_not_exist(engine)
    df = pd.DataFrame(
        [
            {
                "date": "2026-01-01",
                "produit_id": "p1",
                "produit_nom": "Produit A",
                "quantite": 2,
                "prix_unitaire": 10.0,
                "magasin_id": "m1",
            },
            {
                "date": "2026-01-01",
                "produit_id": "p2",
                "produit_nom": "Produit B",
                "quantite": 1,
                "prix_unitaire": 20.0,
                "magasin_id": "m1",
            },
        ]
    )

    load_sales_data(engine, df)
    compute_and_store_daily_metrics(engine, date(2026, 1, 1))

    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT ca_total, panier_moyen, top_produit_id, top_produit_nom FROM sales_daily_metrics WHERE date = :date"
            ),
            {"date": date(2026, 1, 1)},
        ).mappings().one()

    assert row["ca_total"] == 40.0
    assert row["panier_moyen"] == 20.0
    assert row["top_produit_id"] == "p2"
    assert row["top_produit_nom"] == "Produit B"

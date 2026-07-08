import logging
import os
from datetime import date as date_class

import pandas as pd
from sqlalchemy import (
    Column,
    Date,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

logger = logging.getLogger(__name__)
metadata = MetaData()

sales_raw = Table(
    "sales_raw",
    metadata,
    Column("date", Date, nullable=False),
    Column("produit_id", String, nullable=False),
    Column("produit_nom", String, nullable=False),
    Column("quantite", Integer, nullable=False),
    Column("prix_unitaire", Float, nullable=False),
    Column("magasin_id", String, nullable=False),
    UniqueConstraint("date", "produit_id", "magasin_id", name="uq_sales_raw"),
)

sales_daily_metrics = Table(
    "sales_daily_metrics",
    metadata,
    Column("date", Date, primary_key=True, nullable=False),
    Column("ca_total", Float, nullable=False),
    Column("panier_moyen", Float, nullable=False),
    Column("top_produit_id", String, nullable=True),
    Column("top_produit_nom", String, nullable=True),
)


def get_database_url() -> str:
    host = os.environ["DB_HOST"]
    name = os.environ["DB_NAME"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]
    return f"postgresql+psycopg2://{user}:{password}@{host}/{name}"


def get_engine():
    url = get_database_url()
    return create_engine(url)


def create_tables_if_not_exist(engine):
    logger.info("Création des tables PostgreSQL si nécessaire")
    metadata.create_all(engine)


def load_sales_data(engine, df: pd.DataFrame):
    if df.empty:
        logger.info("Aucune donnée à charger dans sales_raw")
        return

    records = df.to_dict(orient="records")
    stmt = pg_insert(sales_raw).values(records).on_conflict_do_nothing(
        index_elements=["date", "produit_id", "magasin_id"]
    )

    with engine.begin() as conn:
        result = conn.execute(stmt)
        logger.info("Insertion en bloc terminée : %d lignes traitées", result.rowcount)


def _normalize_date(value) -> date_class:
    if isinstance(value, date_class):
        return value
    return pd.to_datetime(value).date()


def compute_and_store_daily_metrics(engine, date):
    sql_date = _normalize_date(date)
    with engine.begin() as conn:
        sales_stmt = select(
            (sales_raw.c.quantite * sales_raw.c.prix_unitaire).label("ligne_montant")
        ).where(sales_raw.c.date == sql_date)
        sales_rows = conn.execute(sales_stmt).all()

        if not sales_rows:
            ca_total = 0.0
            panier_moyen = 0.0
            top_produit_id = None
            top_produit_nom = None
        else:
            lignes = [row.ligne_montant for row in sales_rows]
            ca_total = float(sum(lignes))
            panier_moyen = float(ca_total / len(lignes)) if lignes else 0.0

            top_stmt = select(
                sales_raw.c.produit_id,
                sales_raw.c.produit_nom,
                (sales_raw.c.quantite * sales_raw.c.prix_unitaire).label("revenu_produit"),
            ).where(sales_raw.c.date == sql_date)
            top_stmt = top_stmt.group_by(
                sales_raw.c.produit_id,
                sales_raw.c.produit_nom,
            ).order_by((sales_raw.c.quantite * sales_raw.c.prix_unitaire).desc()).limit(1)
            top_row = conn.execute(top_stmt).first()
            top_produit_id = top_row.produit_id if top_row is not None else None
            top_produit_nom = top_row.produit_nom if top_row is not None else None

        insert_stmt = pg_insert(sales_daily_metrics).values(
            date=sql_date,
            ca_total=ca_total,
            panier_moyen=panier_moyen,
            top_produit_id=top_produit_id,
            top_produit_nom=top_produit_nom,
        ).on_conflict_do_update(
            index_elements=["date"],
            set_=dict(
                ca_total=ca_total,
                panier_moyen=panier_moyen,
                top_produit_id=top_produit_id,
                top_produit_nom=top_produit_nom,
            ),
        )
        conn.execute(insert_stmt)
        logger.info("Métriques journalières stockées pour %s", sql_date)

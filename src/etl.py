import argparse
import logging
import sys

import pandas as pd
from load_postgres import (
    compute_and_store_daily_metrics,
    create_tables_if_not_exist,
    get_engine,
    load_sales_data,
)
from cleaning import clean_sales_data

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def main():
    configure_logging()
    parser = argparse.ArgumentParser(description="Pipeline ETL des ventes quotidiennes")
    parser.add_argument("--input", required=True, help="Chemin vers le fichier CSV source")
    args = parser.parse_args()

    try:
        logger.info("Lecture du CSV %s", args.input)
        raw_df = pd.read_csv(args.input)

        logger.info("Nettoyage des données")
        cleaned_df = clean_sales_data(raw_df)

        logger.info("Initialisation de la base de données PostgreSQL")
        engine = get_engine()
        create_tables_if_not_exist(engine)

        logger.info("Chargement des ventes brutes")
        load_sales_data(engine, cleaned_df)

        if cleaned_df["date"].empty:
            logger.info("Aucune date disponible pour calculer les métriques journalières")
        else:
            target_date = cleaned_df["date"].iloc[0]
            logger.info("Calcul des métriques journalières pour %s", target_date)
            compute_and_store_daily_metrics(engine, target_date)

        logger.info("Pipeline terminé avec succès")
        sys.exit(0)
    except Exception:
        logger.exception("Erreur pendant l'exécution du pipeline ETL")
        sys.exit(1)


if __name__ == "__main__":
    main()

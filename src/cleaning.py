import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def clean_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie les données de vente CSV et retourne un DataFrame prêt à être chargé."""
    input_df = df.copy()
    original_count = len(input_df)

    cleaned = input_df.drop_duplicates()
    dropped = original_count - len(cleaned)
    if dropped:
        logger.info("Suppression de %d doublons exacts", dropped)

    cleaned["produit_nom"] = cleaned["produit_nom"].fillna("")
    cleaned.loc[cleaned["produit_nom"].astype(str).str.strip() == "", "produit_nom"] = "Inconnu"

    required_fields = ["date", "produit_id", "magasin_id"]
    missing_required = cleaned[required_fields].isna() | cleaned[required_fields].astype(str).apply(lambda x: x.str.strip() == "")
    missing_required_rows = missing_required.any(axis=1)
    if missing_required_rows.any():
        rejected = len(cleaned[missing_required_rows])
        logger.warning("Rejet de %d lignes avec des champs requis manquants", rejected)
        cleaned = cleaned.loc[~missing_required_rows]

    cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce")
    invalid_date = cleaned["date"].isna()
    if invalid_date.any():
        rejected = len(cleaned[invalid_date])
        logger.warning("Rejet de %d lignes avec une date invalide", rejected)
        cleaned = cleaned.loc[~invalid_date]

    cleaned["quantite"] = pd.to_numeric(cleaned["quantite"], errors="coerce", downcast="integer")
    cleaned["prix_unitaire"] = pd.to_numeric(cleaned["prix_unitaire"], errors="coerce")

    invalid_numeric = cleaned["quantite"].isna() | cleaned["prix_unitaire"].isna()
    if invalid_numeric.any():
        rejected = len(cleaned[invalid_numeric])
        logger.warning("Rejet de %d lignes avec des valeurs numériques invalides", rejected)
        cleaned = cleaned.loc[~invalid_numeric]

    non_positive = (cleaned["quantite"] <= 0) | (cleaned["prix_unitaire"] <= 0)
    if non_positive.any():
        rejected = len(cleaned[non_positive])
        logger.warning("Rejet de %d lignes avec quantite<=0 ou prix_unitaire<=0", rejected)
        cleaned = cleaned.loc[~non_positive]

    cleaned = cleaned.copy()
    cleaned["quantite"] = cleaned["quantite"].astype(int)
    cleaned["prix_unitaire"] = cleaned["prix_unitaire"].astype(float)

    logger.info("Nettoyage terminé : %d lignes restantes", len(cleaned))
    return cleaned

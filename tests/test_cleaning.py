import pandas as pd
import pytest

from cleaning import clean_sales_data


def test_clean_sales_data_retient_les_donnees_valides():
    df = pd.DataFrame(
        [
            {
                "date": "2026-01-01",
                "produit_id": "p1",
                "produit_nom": "Produit A",
                "quantite": 5,
                "prix_unitaire": 10.0,
                "magasin_id": "m1",
            }
        ]
    )

    cleaned = clean_sales_data(df)

    assert len(cleaned) == 1
    assert cleaned.iloc[0]["produit_nom"] == "Produit A"
    assert cleaned.iloc[0]["quantite"] == 5
    assert cleaned.iloc[0]["prix_unitaire"] == 10.0
    assert cleaned.iloc[0]["date"].year == 2026


def test_clean_sales_data_supprime_les_doublons_exacts():
    df = pd.DataFrame(
        [
            {
                "date": "2026-01-01",
                "produit_id": "p1",
                "produit_nom": "Produit A",
                "quantite": 5,
                "prix_unitaire": 10.0,
                "magasin_id": "m1",
            },
            {
                "date": "2026-01-01",
                "produit_id": "p1",
                "produit_nom": "Produit A",
                "quantite": 5,
                "prix_unitaire": 10.0,
                "magasin_id": "m1",
            },
        ]
    )

    cleaned = clean_sales_data(df)
    assert len(cleaned) == 1


def test_clean_sales_data_rejette_quantite_negative_et_prix_zero():
    df = pd.DataFrame(
        [
            {
                "date": "2026-01-01",
                "produit_id": "p1",
                "produit_nom": "Produit A",
                "quantite": -1,
                "prix_unitaire": 10.0,
                "magasin_id": "m1",
            },
            {
                "date": "2026-01-01",
                "produit_id": "p2",
                "produit_nom": "Produit B",
                "quantite": 3,
                "prix_unitaire": 0,
                "magasin_id": "m1",
            },
        ]
    )

    cleaned = clean_sales_data(df)
    assert cleaned.empty


def test_clean_sales_data_rejette_les_lignes_sans_produit_id_ou_date():
    df = pd.DataFrame(
        [
            {
                "date": "",
                "produit_id": "p1",
                "produit_nom": "Produit A",
                "quantite": 1,
                "prix_unitaire": 10.0,
                "magasin_id": "m1",
            },
            {
                "date": "2026-01-01",
                "produit_id": "",
                "produit_nom": "Produit B",
                "quantite": 1,
                "prix_unitaire": 20.0,
                "magasin_id": "m1",
            },
            {
                "date": "2026-01-01",
                "produit_id": "p2",
                "produit_nom": "Produit C",
                "quantite": 1,
                "prix_unitaire": 20.0,
                "magasin_id": "m1",
            },
        ]
    )

    cleaned = clean_sales_data(df)
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["produit_id"] == "p2"


def test_clean_sales_data_remplace_nom_produit_manquant_par_inconnu():
    df = pd.DataFrame(
        [
            {
                "date": "2026-01-01",
                "produit_id": "p1",
                "produit_nom": None,
                "quantite": 2,
                "prix_unitaire": 5.0,
                "magasin_id": "m1",
            }
        ]
    )

    cleaned = clean_sales_data(df)
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["produit_nom"] == "Inconnu"

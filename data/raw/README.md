# Fichiers Raw - Données Sources

Fichiers sources pour générer les données consolidées.

## Archive Principale

**`jeu_de_donnees.zip`** (télécharger depuis `notebooks/intro/Introduction-Datathon.ipynb`)
- URL: `https://d38aa0udflevgr.cloudfront.net/datathon/jeu_de_donnees.zip`
- Contient: CSV S&P 500, directives réglementaires, 10-K filings

## Fichiers CSV (pour générer `company_universe.json`)

1. `2025-08-15_composition_sp500.csv`
2. `2025-09-26_stocks-performance.csv`

**Utilisation** : Notebooks `extract_key_market_data.ipynb` → `generate_company_universe.ipynb`

**Note** : Une fois `company_universe.json` généré, ces CSV ne sont plus nécessaires pour l'app (garder le zip pour référence).

## Structure

```
data/raw/
├── jeu_de_donnees.zip          # Archive originale
├── *.csv                       # CSV extraits
└── directives/                # 6 documents réglementaires
```


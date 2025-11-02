# 📁 Structure des Données

## Organisation

- **`raw/`** : Fichiers sources originaux (CSV)
  - `2025-08-15_composition_sp500.csv` : Composition S&P 500
  - `2025-09-26_stocks-performance.csv` : Métriques de performance

- **`generated/`** : Données générées par les scripts
  - `key_market_data/` : Key Market Data fusionnés (JSON + CSV)

**NOTE** : `extracted_data_points/` et `fillings/` restent à la racine du projet
car des scripts d'extraction peuvent être en cours d'exécution.

## Génération des Données

1. **Key Market Data** :
   ```bash
   python scripts/generate_key_market_data.py
   ```
   → Génère `data/generated/key_market_data/all_market_data.json`

2. **Data Points 10-K** :
   → Utiliser le notebook `extract_data_points_10k.ipynb`
   → Génère `extracted_data_points/{TICKER}_data_points.json` (à la racine)

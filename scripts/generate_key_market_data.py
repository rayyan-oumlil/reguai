"""
Script pour générer les Key Market Data avec ratios améliorés
Fusionne composition S&P 500 + métriques de performance + yfinance
FILTRE: Garde uniquement les entreprises qui ont un 10-K dans fillings/
RÉSULTAT: Un seul fichier JSON (pas de CSV)
"""

import pandas as pd
import json
import time
from pathlib import Path
from typing import Dict, Optional
import yfinance as yf
from tqdm import tqdm


def load_and_merge_data():
    """Charge et fusionne les deux CSV sources, filtre par fillings"""
    # Charger composition S&P 500
    composition_df = pd.read_csv('data/raw/2025-08-15_composition_sp500.csv')
    
    # Convertir Weight et Price (format européen avec virgule)
    if 'Weight' in composition_df.columns:
        composition_df['Weight'] = composition_df['Weight'].astype(str).str.replace(',', '.').astype(float)
    if 'Price' in composition_df.columns:
        composition_df['Price'] = composition_df['Price'].astype(str).str.replace(',', '.').astype(float)
    
    # Charger métriques de performance
    performance_df = pd.read_csv('data/raw/2025-09-26_stocks-performance.csv')
    
    # Normaliser les colonnes pour la fusion
    if 'Symbol' in composition_df.columns:
        composition_df = composition_df.rename(columns={'Symbol': 'Ticker'})
    if 'Symbol' in performance_df.columns:
        performance_df = performance_df.rename(columns={'Symbol': 'Ticker'})
    
    # Fusionner sur Ticker (S&P 500 comme base)
    merged_df = pd.merge(
        composition_df,
        performance_df[['Ticker', 'Company Name', 'Market Cap', 'Revenue', 'Op. Income', 'Net Income', 'EPS', 'FCF']],
        on='Ticker',
        how='left',
        suffixes=('', '_perf')
    )
    
    # FILTRER: Garder uniquement les entreprises qui ont un 10-K dans fillings/
    fillings_dir = Path('data/raw/fillings')
    if fillings_dir.exists():
        available_tickers = [d.name for d in fillings_dir.iterdir() if d.is_dir()]
        merged_df = merged_df[merged_df['Ticker'].isin(available_tickers)].copy()
        print(f"✅ Filtrage: {len(merged_df)} entreprises avec 10-K disponibles")
    else:
        print("⚠️ Dossier fillings/ non trouvé, pas de filtrage")
    
    print(f"✅ Fusionnée : {len(merged_df)} entreprises")
    return merged_df


def create_market_data_structure(row: pd.Series) -> Dict:
    """
    Crée une structure JSON enrichie pour les données de marché d'une entreprise
    Calcule plusieurs ratios financiers + inclut secteur/industrie depuis yfinance
    """
    # Gérer company_name : priorité à Long Name (yfinance), puis Company (S&P 500), puis Company Name (performance)
    company_name = None
    if pd.notna(row.get('Long Name')):
        company_name = str(row['Long Name']).strip()
    elif pd.notna(row.get('Company')):
        company_name = str(row['Company']).strip()
    elif pd.notna(row.get('Company Name')):
        company_name = str(row['Company Name']).strip()
    
    data = {
        "ticker": str(row['Ticker']).upper() if pd.notna(row.get('Ticker')) else None,
        "company_name": company_name,
        "sector": str(row['Sector']) if pd.notna(row.get('Sector')) else None,
        "industry": str(row['Industry']) if pd.notna(row.get('Industry')) else None,
        "is_sp500": True,  # Toutes sont dans S&P 500 (filtré au départ)
        "sp500_weight": float(row['Weight']) if pd.notna(row.get('Weight')) else None,
        "current_price": float(row['Price']) if pd.notna(row.get('Price')) else None,
        "market_cap": float(row['Market Cap']) if pd.notna(row.get('Market Cap')) else None,
        "revenue": float(row['Revenue']) if pd.notna(row.get('Revenue')) else None,
        "operating_income": float(row['Op. Income']) if pd.notna(row.get('Op. Income')) else None,
        "net_income": float(row['Net Income']) if pd.notna(row.get('Net Income')) else None,
        "eps": float(row['EPS']) if pd.notna(row.get('EPS')) else None,
        "free_cash_flow": float(row['FCF']) if pd.notna(row.get('FCF')) else None,
    }
    
    # === RATIOS FINANCIERS ===
    
    # 1. Profit Margin (Net Income / Revenue)
    if data['revenue'] and data['net_income'] and data['revenue'] != 0:
        data['profit_margin'] = round(data['net_income'] / data['revenue'], 4)
    else:
        data['profit_margin'] = None
    
    # 2. Operating Margin (Operating Income / Revenue)
    if data['revenue'] and data['operating_income'] and data['revenue'] != 0:
        data['operating_margin'] = round(data['operating_income'] / data['revenue'], 4)
    else:
        data['operating_margin'] = None
    
    # 3. P/E Ratio (Price / EPS)
    if data['current_price'] and data['eps'] and data['eps'] != 0:
        data['pe_ratio'] = round(data['current_price'] / data['eps'], 2)
    else:
        data['pe_ratio'] = None
    
    # 4. Price to Sales (Market Cap / Revenue)
    if data['market_cap'] and data['revenue'] and data['revenue'] != 0:
        data['price_to_sales'] = round(data['market_cap'] / data['revenue'], 2)
    else:
        data['price_to_sales'] = None
    
    # 5. FCF Margin (Free Cash Flow / Revenue)
    if data['revenue'] and data['free_cash_flow'] and data['revenue'] != 0:
        data['fcf_margin'] = round(data['free_cash_flow'] / data['revenue'], 4)
    else:
        data['fcf_margin'] = None
    
    # 6. FCF Yield (Free Cash Flow / Market Cap)
    if data['market_cap'] and data['free_cash_flow'] and data['market_cap'] != 0:
        data['fcf_yield'] = round(data['free_cash_flow'] / data['market_cap'], 4)
    else:
        data['fcf_yield'] = None
    
    # 7. Earnings Yield (EPS / Price) - inverse du P/E
    if data['current_price'] and data['eps'] and data['current_price'] != 0:
        data['earnings_yield'] = round(data['eps'] / data['current_price'], 4)
    else:
        data['earnings_yield'] = None
    
    # 8. Market Cap / Net Income (inverse du P/E, mais avec Market Cap)
    if data['market_cap'] and data['net_income'] and data['net_income'] != 0:
        data['market_cap_to_earnings'] = round(data['market_cap'] / data['net_income'], 2)
    else:
        data['market_cap_to_earnings'] = None
    
    # 9. Operating Efficiency (Operating Income / Net Income)
    if data['operating_income'] and data['net_income'] and data['net_income'] != 0:
        data['operating_efficiency'] = round(data['operating_income'] / data['net_income'], 2)
    else:
        data['operating_efficiency'] = None
    
    # 10. Cash Conversion (Free Cash Flow / Net Income)
    if data['net_income'] and data['free_cash_flow'] and data['net_income'] != 0:
        data['cash_conversion'] = round(data['free_cash_flow'] / data['net_income'], 2)
    else:
        data['cash_conversion'] = None
    
    return data


def enrich_with_yfinance(merged_df: pd.DataFrame) -> pd.DataFrame:
    """Enrichit le DataFrame avec secteurs et industries depuis yfinance"""
    def normalize_ticker_for_yfinance(ticker: str) -> str:
        if pd.isna(ticker):
            return None
        return str(ticker).replace(",", "-")
    
    sector_dict = {}
    industry_dict = {}
    company_long_name_dict = {}
    
    print("\n🔍 Récupération des secteurs via yfinance...")
    unique_tickers = merged_df['Ticker'].dropna().unique()
    print(f"   Tickers à traiter: {len(unique_tickers)}")
    
    for ticker in tqdm(unique_tickers, desc="Récupération secteurs"):
        try:
            yf_ticker = normalize_ticker_for_yfinance(ticker)
            if not yf_ticker:
                continue
            
            company = yf.Ticker(yf_ticker)
            info = company.info
            
            sector_dict[ticker] = info.get("sector", "Unknown")
            industry_dict[ticker] = info.get("industry", "Unknown")
            company_long_name_dict[ticker] = info.get("longName", None)
            
            time.sleep(0.5)  # Rate limiting
            
        except Exception as e:
            sector_dict[ticker] = "Unknown"
            industry_dict[ticker] = "Unknown"
            company_long_name_dict[ticker] = None
    
    # Ajouter les colonnes
    merged_df['Sector'] = merged_df['Ticker'].map(sector_dict)
    merged_df['Industry'] = merged_df['Ticker'].map(industry_dict)
    merged_df['Long Name'] = merged_df['Ticker'].map(company_long_name_dict)
    
    print("✅ Enrichissement yfinance terminé")
    return merged_df


def generate_key_market_data(output_dir: str = "data/generated/key_market_data"):
    """
    Génère UN SEUL fichier all_market_data.json avec toutes les Key Market Data
    (mergées + yfinance) pour les entreprises avec 10-K uniquement
    """
    # Créer le dossier de sortie
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Charger et fusionner les données (déjà filtré par fillings)
    merged_df = load_and_merge_data()
    
    # Enrichir avec yfinance (secteurs)
    merged_df = enrich_with_yfinance(merged_df)
    
    # Appliquer à toutes les lignes
    all_market_data = {}
    for idx, row in merged_df.iterrows():
        ticker = str(row['Ticker']).upper() if pd.notna(row.get('Ticker')) else None
        if ticker and ticker.strip():
            all_market_data[ticker] = create_market_data_structure(row)
    
    # Sauvegarder le fichier JSON (SEUL fichier généré)
    output_file = output_path / "all_market_data.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_market_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Fichier JSON sauvegardé: {output_file}")
    print(f"📊 Total: {len(all_market_data)} entreprises (avec 10-K)")
    print(f"   - Avec secteur: {sum(1 for v in all_market_data.values() if v.get('sector') and v.get('sector') != 'Unknown')}")
    print(f"   - Avec données Performance: {sum(1 for v in all_market_data.values() if v.get('market_cap'))}")
    
    return all_market_data


if __name__ == "__main__":
    print("📊 Génération des Key Market Data (JSON uniquement, avec 10-K uniquement)...\n")
    market_data = generate_key_market_data()
    
    # Afficher un exemple
    if 'AAPL' in market_data:
        print("\n📊 Exemple (AAPL):")
        print(json.dumps(market_data['AAPL'], indent=2, ensure_ascii=False))

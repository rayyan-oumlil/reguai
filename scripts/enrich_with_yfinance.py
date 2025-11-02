"""
Script pour enrichir les données avec Yahoo Finance (yfinance)
Enrichit les entreprises avec prix actuels, beta, volatilité, P/E Ratio, etc.
Peut aussi ajouter Weight S&P 500 depuis CSV ou calcul approximatif.

Métriques incluses :
- Prix actuel vs prix CSV (variation)
- Beta (volatilité)
- P/E Ratio (Price-to-Earnings Ratio) : Indique combien les investisseurs sont prêts à payer 
  pour chaque dollar de bénéfices. Utilisé pour évaluer si une action est surévaluée ou sous-évaluée.
  Calcul : Prix de marché / Bénéfice par action (EPS)
- Market Cap, Volume, 52-week High/Low
- Facteur de volatilité (basé sur Beta)
"""

import yfinance as yf
import time
import pandas as pd
from typing import Dict, Optional, List
from pathlib import Path
import json
from tqdm import tqdm

# Cache pour CSV S&P 500
_SP500_CACHE = None


def load_sp500_composition() -> Optional[pd.DataFrame]:
    """
    Charge le CSV S&P 500 une fois et le met en cache
    """
    global _SP500_CACHE
    if _SP500_CACHE is None:
        csv_path = Path('data/raw/2025-08-15_composition_sp500.csv')
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            if 'Symbol' in df.columns:
                df = df.rename(columns={'Symbol': 'Ticker'})
            if 'Weight' in df.columns:
                df['Weight'] = df['Weight'].astype(str).str.replace(',', '.').astype(float)
            _SP500_CACHE = df.set_index('Ticker')
        else:
            _SP500_CACHE = pd.DataFrame()
    return _SP500_CACHE


def get_sp500_weight(ticker: str) -> Optional[float]:
    """
    Récupère le Weight S&P 500 pour un ticker depuis le CSV
    
    Args:
        ticker: Symbole boursier (ex: "AAPL")
    
    Returns:
        Weight S&P 500 (ex: 0.0597) ou None si non trouvé
    """
    sp500_df = load_sp500_composition()
    if sp500_df.empty:
        return None
    
    ticker_upper = ticker.upper()
    if ticker_upper in sp500_df.index:
        return float(sp500_df.loc[ticker_upper, 'Weight'])
    return None


def calculate_approximate_weight(ticker: str, market_cap: float) -> Optional[float]:
    """
    Calcule un Weight approximatif : (Market Cap entreprise) / (Market Cap total S&P 500)
    
    Note: Approximation, pas exact. Le vrai Weight dépend de la capitalisation flottante.
    
    Args:
        ticker: Symbole boursier
        market_cap: Market Cap de l'entreprise
    
    Returns:
        Weight approximatif ou None
    """
    # On aurait besoin du Market Cap total du S&P 500 pour calculer
    # Pour l'instant, on retourne None car on n'a pas cette info
    # Pourrait être récupéré via API ou calculé depuis tous les tickers S&P 500
    return None


def enrich_ticker_with_yfinance(ticker: str, csv_price: float, include_sp500_weight: bool = True) -> Dict:
    """
    Enrichit une entreprise avec données Yahoo Finance
    
    Args:
        ticker: Symbole boursier (ex: "AAPL")
        csv_price: Prix depuis CSV (15 août 2025)
    
    Returns:
        Dict avec prix actuel, beta, etc.
    """
    try:
        stock = yf.Ticker(ticker)
        
        # Prix actuel
        history = stock.history(period='1d')
        if not history.empty:
            current_price = float(history['Close'][0])
        else:
            current_price = csv_price
        
        # Informations complémentaires
        info = stock.info
        
        # Beta (volatilité) - valeur par défaut 1.0 si non disponible
        beta = info.get('beta', 1.0)
        if beta is None:
            beta = 1.0
        
        # Autres métriques
        market_cap = info.get('marketCap', 0)
        volume = info.get('volume', 0)
        week_52_high = info.get('fiftyTwoWeekHigh', 0)
        week_52_low = info.get('fiftyTwoWeekLow', 0)
        
        # P/E Ratio (Price-to-Earnings Ratio)
        # Indique combien les investisseurs sont prêts à payer pour chaque dollar de bénéfices
        # Utilisé pour évaluer si une action est surévaluée ou sous-évaluée
        trailing_pe = info.get('trailingPE')  # P/E basé sur les bénéfices passés
        forward_pe = info.get('forwardPE')  # P/E basé sur les bénéfices futurs estimés
        
        # Calculer P/E si EPS disponible et P/E non fourni
        pe_ratio = trailing_pe or forward_pe
        if not pe_ratio:
            eps = info.get('trailingEps') or info.get('forwardEps')
            if eps and eps > 0 and current_price > 0:
                pe_ratio = current_price / eps
        
        # Calcul variation prix
        price_change_pct = 0.0
        if csv_price > 0:
            price_change_pct = ((current_price - csv_price) / csv_price) * 100
        
        # Ajuster risque selon volatilité
        if beta > 1.5:
            volatility_factor = 1.3  # +30% si très volatil
            volatility_risk = "Élevée"
        elif beta > 1.2:
            volatility_factor = 1.15  # +15% si volatil
            volatility_risk = "Modérée-Élevée"
        elif beta < 0.8:
            volatility_factor = 0.9  # -10% si peu volatil
            volatility_risk = "Faible"
        else:
            volatility_factor = 1.0
            volatility_risk = "Normale"
        
        result = {
            'current_price': round(current_price, 2),
            'csv_price': round(csv_price, 2),
            'price_change_pct': round(price_change_pct, 2),
            'beta': round(beta, 2),
            'market_cap': market_cap,
            'volume': volume,
            'week_52_high': round(week_52_high, 2) if week_52_high else 0,
            'week_52_low': round(week_52_low, 2) if week_52_low else 0,
            'pe_ratio': round(pe_ratio, 2) if pe_ratio else None,  # P/E Ratio
            'trailing_pe': round(trailing_pe, 2) if trailing_pe else None,
            'forward_pe': round(forward_pe, 2) if forward_pe else None,
            'volatility_factor': round(volatility_factor, 3),
            'volatility_risk': volatility_risk,
            'enriched_at': pd.Timestamp.now().isoformat(),
            'success': True
        }
        
        # Ajouter Weight S&P 500 depuis CSV si demandé
        if include_sp500_weight:
            sp500_weight = get_sp500_weight(ticker)
            if sp500_weight is not None:
                result['sp500_weight'] = round(sp500_weight, 6)
                result['is_sp500'] = True
            else:
                result['is_sp500'] = False
        
        return result
    except Exception as e:
        print(f"⚠️ Erreur pour {ticker}: {e}")
        return {
            'current_price': csv_price,
            'csv_price': csv_price,
            'price_change_pct': 0.0,
            'beta': 1.0,
            'pe_ratio': None,
            'trailing_pe': None,
            'forward_pe': None,
            'volatility_factor': 1.0,
            'volatility_risk': "Non disponible",
            'success': False,
            'error': str(e)
        }


def enrich_multiple_tickers(tickers: List[str], csv_prices: Dict[str, float], 
                           delay: float = 0.5, max_tickers: Optional[int] = None) -> Dict[str, Dict]:
    """
    Enrichit plusieurs tickers avec délais pour éviter rate limiting
    
    Args:
        tickers: Liste de tickers
        csv_prices: Dict {ticker: prix_csv}
        delay: Délai entre requêtes (secondes)
        max_tickers: Limiter le nombre de tickers (None = tous)
    
    Returns:
        Dict {ticker: données enrichies}
    """
    results = {}
    
    # Limiter le nombre si spécifié
    if max_tickers:
        tickers = tickers[:max_tickers]
    
    print(f"📊 Enrichissement de {len(tickers)} entreprises avec Yahoo Finance...")
    
    for ticker in tqdm(tickers, desc="Enrichissement"):
        csv_price = csv_prices.get(ticker, 0)
        if csv_price > 0:
            results[ticker] = enrich_ticker_with_yfinance(ticker, csv_price)
            time.sleep(delay)  # Éviter rate limiting
        else:
            results[ticker] = {
                'success': False,
                'error': 'Prix CSV non disponible'
            }
    
    successful = sum(1 for r in results.values() if r.get('success', False))
    print(f"\n✅ {successful}/{len(tickers)} enrichissements réussis")
    
    return results


def enrich_from_key_market_data(key_market_data: Dict, 
                                limit_to_high_risk: bool = True,
                                max_tickers: int = 50) -> Dict[str, Dict]:
    """
    Enrichit depuis Key Market Data existant
    
    Args:
        key_market_data: Dict des Key Market Data (format JSON)
        limit_to_high_risk: Si True, seulement entreprises avec données (priorité)
        max_tickers: Nombre maximum de tickers à enrichir
    
    Returns:
        Dict {ticker: données enrichies}
    """
    # Extraire tickers et prix CSV
    csv_prices = {}
    tickers_list = []
    
    for ticker, data in key_market_data.items():
        stock_price = data.get('market_data', {}).get('stock_price', 0)
        if stock_price > 0:
            csv_prices[ticker] = stock_price
            tickers_list.append(ticker)
    
    # Limiter si nécessaire
    if limit_to_high_risk:
        # Prioriser les entreprises qui ont déjà des data points (plus d'info)
        # Pour l'instant, prendre les premiers
        tickers_list = tickers_list[:max_tickers]
    
    return enrich_multiple_tickers(tickers_list, csv_prices, delay=0.5)


def enrich_company_universe(company_universe: Dict, 
                           limit_top_n: int = 50) -> Dict:
    """
    Enrichit le Company Universe existant avec yfinance
    
    Args:
        company_universe: Dict du Company Universe
        limit_top_n: Nombre maximum d'entreprises à enrichir (prioriser)
    
    Returns:
        Company Universe enrichi
    """
    enriched = company_universe.copy()
    
    # Extraire tickers avec prix CSV
    csv_prices = {}
    tickers_to_enrich = []
    
    for ticker, data in company_universe.items():
        # Essayer différentes structures possibles
        csv_price = 0
        if 'market_data' in data:
            csv_price = data['market_data'].get('stock_price', 0)
        elif 'key_market_data' in data:
            csv_price = data['key_market_data'].get('stock_price', 0)
        
        if csv_price > 0:
            csv_prices[ticker] = csv_price
            tickers_to_enrich.append(ticker)
    
    # Limiter aux top N
    tickers_to_enrich = tickers_to_enrich[:limit_top_n]
    
    print(f"📊 Enrichissement de {len(tickers_to_enrich)} entreprises...")
    
    # Enrichir
    enrichment_results = enrich_multiple_tickers(
        tickers_to_enrich, 
        csv_prices, 
        delay=0.5
    )
    
    # Ajouter au Company Universe
    for ticker, enrichment in enrichment_results.items():
        if ticker in enriched:
            if 'market_data' not in enriched[ticker]:
                enriched[ticker]['market_data'] = {}
            
            enriched[ticker]['market_data']['realtime'] = enrichment
    
    return enriched


if __name__ == "__main__":
    # Exemple d'utilisation
    print("🚀 Test d'enrichissement Yahoo Finance")
    
    # Test avec quelques tickers
    test_tickers = ["AAPL", "MSFT", "GOOGL"]
    test_prices = {"AAPL": 180.50, "MSFT": 420.30, "GOOGL": 150.25}
    
    results = enrich_multiple_tickers(test_tickers, test_prices, delay=0.5)
    
    print("\n📊 Résultats:")
    for ticker, data in results.items():
        print(f"\n{ticker}:")
        print(f"  Prix CSV: ${data.get('csv_price', 0):.2f}")
        print(f"  Prix actuel: ${data.get('current_price', 0):.2f}")
        print(f"  Variation: {data.get('price_change_pct', 0):+.2f}%")
        print(f"  Beta: {data.get('beta', 1.0):.2f}")
        print(f"  P/E Ratio: {data.get('pe_ratio', 'N/A')}")
        print(f"  Facteur volatilité: {data.get('volatility_factor', 1.0):.3f}")


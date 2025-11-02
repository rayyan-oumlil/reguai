# 📊 Utilisation des CSV Market Data - POLYFINANCES Datathon

## 📋 Contexte du Projet

**Objectif** : Transformer la complexité réglementaire en opportunité d'aide à la décision pour la gestion de portefeuilles S&P 500.

**Les CSV Market Data servent à** :
1. ✅ **Comprendre la composition du portefeuille** (S&P 500)
2. ✅ **Analyser l'exposition financière** par entreprise
3. ✅ **Calculer l'impact réglementaire** sur chaque entreprise
4. ✅ **Mesurer les risques** par secteur/pays
5. ✅ **Générer des recommandations** de réallocation

---

## 📁 Les Deux CSV Fournis

### 1. `2025-08-15_composition_sp500.csv`
**Date** : 15 août 2025  
**Contenu** : Composition officielle du S&P 500

**Colonnes importantes** :
- `Symbol` (Ticker) : AAPL, MSFT, etc.
- `Company` : Nom de l'entreprise
- `Weight` : **Poids dans l'indice S&P 500** (ex: 0.0597 = 5.97%)
  - ⚠️ **CRITIQUE** : Utilisé pour calculer l'impact sur le portefeuille global
  - Exemple : Si AAPL (5.97%) est impacté, ça affecte 5.97% du portefeuille
- `Price` : Prix de l'action au 15 août 2025

**Utilisation dans le projet** :
- ✅ Identifier les entreprises du S&P 500
- ✅ Calculer l'impact pondéré sur le portefeuille (Weight × Impact entreprise)
- ✅ Comprendre la concentration du portefeuille

---

### 2. `2025-09-26_stocks-performance.csv`
**Date** : 26 septembre 2025  
**Contenu** : Métriques financières de performance

**Colonnes importantes** :
- `Symbol` (Ticker)
- `Company Name`
- `Market Cap` : Capitalisation boursière
- `Revenue` : Chiffre d'affaires annuel
- `Net Income` : Bénéfice net
- `EPS` : Earnings Per Share (Bénéfice par action)
- `FCF` : Free Cash Flow (Trésorerie libre)
- `Op. Income` : Revenu opérationnel

**Utilisation dans le projet** :
- ✅ **Analyser la santé financière** de chaque entreprise
- ✅ **Calculer l'impact financier** d'une réglementation :
  - Exemple : Taxe de 10% sur Revenue → Impact = Revenue × 0.10
  - Exemple : Augmentation coûts de 5% → Impact = Op. Income × 0.05
- ✅ **Comparer les entreprises** (ratios financiers)
- ✅ **Identifier les plus vulnérables** (marges faibles, dépendance secteur)

---

## 🎯 Comment Utiliser Ces CSV dans le Projet

### Étape 1 : Créer Key Market Data (FAIT ✅)
**Objectif** : Fusionner et structurer les données

```python
# Structure attendue par ticker
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "sp500_weight": 0.0597,  # Depuis CSV composition
  "current_price": 233.28,  # Depuis CSV composition
  "market_cap": 3791126029400.0,  # Depuis CSV performance
  "revenue": 408625000000.0,
  "net_income": 99280000000.0,
  "eps": 6.59,
  "free_cash_flow": 96184000000.0,
  # Ratios calculés
  "profit_margin": 0.243,
  "pe_ratio": 35.4,
  # etc.
}
```

**Fichier généré** : `data/generated/key_market_data/all_market_data.json`

---

### Étape 2 : Calculer l'Impact Réglementaire

**Exemple concret** : Directive européenne impose une taxe de 5% sur les revenus des entreprises tech

```python
# Pour chaque entreprise du S&P 500
for ticker, market_data in key_market_data.items():
    # 1. Vérifier si l'entreprise est concernée (géographie, secteur)
    if is_affected_by_regulation(market_data, regulation):
        
        # 2. Calculer l'impact financier
        revenue = market_data['revenue']
        impact_revenue = revenue * 0.05  # Taxe de 5%
        
        # 3. Calculer l'impact sur le bénéfice net
        profit_margin = market_data['profit_margin']
        impact_net_income = impact_revenue * profit_margin
        
        # 4. Calculer l'impact sur le portefeuille (pondéré par Weight)
        sp500_weight = market_data.get('sp500_weight', 0)
        portfolio_impact = impact_net_income * sp500_weight
        
        # 5. Calculer un score de risque
        risk_score = calculate_risk_score(
            impact_revenue,
            impact_net_income,
            market_data['profit_margin'],
            market_data.get('beta', 1.0)  # Volatilité depuis yfinance
        )
```

---

### Étape 3 : Agréger par Secteur/Pays

**Identifier les concentrations de risque** :

```python
# Par secteur
risk_by_sector = {}
for ticker, market_data in key_market_data.items():
    sector = market_data.get('sector', 'Unknown')  # Depuis 10-K Data Points
    impact = calculate_impact(market_data, regulation)
    
    if sector not in risk_by_sector:
        risk_by_sector[sector] = {
            'total_impact': 0,
            'companies_count': 0,
            'weight_in_portfolio': 0
        }
    
    risk_by_sector[sector]['total_impact'] += impact['net_income_impact']
    risk_by_sector[sector]['weight_in_portfolio'] += market_data.get('sp500_weight', 0)
    risk_by_sector[sector]['companies_count'] += 1
```

---

### Étape 4 : Générer des Recommandations

**Basé sur les données Market Data** :

1. **Rotation sectorielle** :
   - Identifier secteurs à risque élevé (Weight élevé + Impact élevé)
   - Proposer réduction de Weight dans ces secteurs
   - Proposer augmentation dans secteurs moins risqués

2. **Remplacement de titres** :
   - Entreprises avec Weight élevé + Impact élevé → Remplacer par alternatives moins risquées
   - Utiliser Market Cap, Revenue, Profit Margin pour trouver des alternatives similaires

3. **Réallocation géographique** :
   - Basé sur géographie extraite des 10-K Data Points
   - Entreprises exposées à une zone réglementaire → Réduire Weight

---

## 🔍 Exemples Concrets d'Utilisation

### Exemple 1 : Taxe sur Semi-conducteurs

**Scénario** : Taxe de 100% sur semi-conducteurs importés aux USA

```python
# Utiliser Market Data pour identifier les entreprises concernées
affected_companies = []

for ticker, market_data in key_market_data.items():
    # Vérifier via 10-K Data Points si entreprise dépend de semi-conducteurs
    data_points = get_10k_data_points(ticker)
    supply_chain = data_points.get('supply_chain', [])
    
    if 'semiconductors' in supply_chain or 'TSMC' in supply_chain:
        # Calculer impact
        revenue = market_data['revenue']
        operating_income = market_data['operating_income']
        
        # Impact sur les coûts (augmentation)
        cost_increase = calculate_cost_increase(market_data, 1.0)  # 100% taxe
        
        # Impact sur le bénéfice net
        impact = operating_income * cost_increase
        
        # Score de risque pondéré
        risk_score = (impact / revenue) * 100  # % d'impact
        risk_score *= market_data.get('sp500_weight', 0)  # Pondéré par Weight
        
        affected_companies.append({
            'ticker': ticker,
            'impact_net_income': impact,
            'risk_score': risk_score,
            'sp500_weight': market_data['sp500_weight']
        })
```

---

### Exemple 2 : Directive Européenne sur Tech

**Scénario** : Directive (UE) impose restrictions sur data privacy

```python
# Identifier entreprises tech avec présence en UE
for ticker, market_data in key_market_data.items():
    data_points = get_10k_data_points(ticker)
    geography = data_points.get('geography', {})
    
    # Vérifier présence en UE
    if geography.get('eu_presence', False):
        sector = data_points.get('sector', '')
        
        # Si tech + présence UE → Impact
        if 'technology' in sector.lower() or 'software' in sector.lower():
            revenue = market_data['revenue']
            eu_revenue_pct = geography.get('eu_revenue_percentage', 0)
            
            # Impact estimé : 10% de réduction sur revenus UE
            eu_revenue = revenue * (eu_revenue_pct / 100)
            impact_revenue = eu_revenue * 0.10
            
            # Impact pondéré sur portefeuille
            portfolio_impact = impact_revenue * market_data.get('sp500_weight', 0)
```

---

## 📊 Métriques Clés à Extraire des CSV

### Pour l'Analyse d'Impact :

1. **Market Cap** → Taille de l'entreprise (impact global)
2. **Revenue** → Base pour calculer impact de taxes/réductions
3. **Net Income** → Impact sur bénéfices
4. **Profit Margin** → Vulnérabilité aux réductions de revenus
5. **FCF** → Capacité à absorber les coûts
6. **Weight S&P 500** → **CRITIQUE** pour impact portefeuille

### Pour les Recommandations :

1. **Weight S&P 500** → Identifier positions importantes
2. **Profit Margin** → Identifier entreprises fragiles
3. **Market Cap** → Trouver alternatives similaires
4. **Sector** (depuis 10-K) → Rotation sectorielle

---

## ⚠️ Points d'Attention

1. **Dates différentes** :
   - CSV Composition : 15 août 2025
   - CSV Performance : 26 septembre 2025
   - ⚠️ Les prix peuvent avoir changé
   - ✅ Utiliser Market Cap de septembre (plus récent)

2. **Weight S&P 500** :
   - ✅ **CRITIQUE** pour calculer impact sur portefeuille
   - Peut avoir changé entre août et septembre
   - Utiliser Weight d'août comme référence (officiel)

3. **Calculs d'impact** :
   - Toujours pondérer par `sp500_weight` pour impact portefeuille
   - Utiliser `revenue` ou `net_income` selon le type de réglementation

---

## 🎯 Résumé : Ce qu'il faut faire

1. ✅ **Fusionner les deux CSV** → `all_market_data.json` (FAIT)
2. ✅ **Enrichir avec yfinance** → Prix actuels, Beta (EN COURS)
3. ⚠️ **Utiliser pour calcul d'impact** :
   - Pour chaque réglementation
   - Identifier entreprises concernées (via 10-K Data Points)
   - Calculer impact financier (Revenue, Net Income)
   - Pondérer par Weight S&P 500 pour impact portefeuille
4. ⚠️ **Générer recommandations** :
   - Rotation sectorielle basée sur Weight + Impact
   - Remplacement titres basé sur Market Cap + Impact
   - Réallocation basée sur géographie (10-K)

---

## 📝 Prochaines Étapes

1. ✅ Key Market Data créé
2. ⚠️ **À faire** : Modélisation d'impact réglementaire (`impact_analysis.py`)
3. ⚠️ **À faire** : Générer recommandations (`recommendations.py`)
4. ⚠️ **À faire** : Visualiser dans Streamlit avec Weight et Impact


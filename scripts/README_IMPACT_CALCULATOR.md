# Impact Calculator - Architecture 3-Tiers de Valuation

## Vue d'ensemble

Le `impact_calculator.py` implémente une architecture complète en 3-tiers pour le calcul d'impact réglementaire sur les entreprises du S&P 500. Il fournit une évaluation holistique de l'exposition réglementaire jusqu'à l'impact sur la valorisation financière.

### Architecture Complète
1. **Tier 1**: Impact Orchestrator & Matching Pairs (Exposition)
2. **Tier 2**: Quant Engine - Multi-Source Processing (Impact Quantitatif)
3. **Tier 3**: DCF Valuation & Final Risk Score (Valorisation)

## Architecture 3-Tiers

### Tier 1 : Impact Orchestrator & Matching Pairs

**Classe : `ImpactOrchestrator`**

- Coordonne le processus d'analyse d'impact complet
- Charge les données (company universe, documents réglementaires)
- Utilise AWS Comprehend pour l'extraction d'entités
- Orchestre la création des matching pairs

**Responsabilités :**
- Chargement des données sources
- Analyse avec AWS Comprehend (entities, key phrases)
- Coordination entre les différents composants
- Extraction du texte depuis les documents réglementaires

### Tier 2 : Matching Pairs Engine (Logique de Matching)

**Classe : `MatchingPairsEngine`**

- Implémente toute la logique de matching entre regulations et companies
- Crée des paires (regulation, company, exposure_score)
- Calcule les scores d'exposition

**Méthodes de matching implémentées :**

1. **`_match_by_country`** : Matching par pays/zones géographiques
   - Vérifie si l'entreprise opère dans les pays mentionnés dans la réglementation
   - Supporte les régions (NA, EU) et les pays spécifiques
   - Score max : 25 points

2. **`_match_by_sector`** : Matching par secteur
   - Vérifie si l'entreprise est dans un secteur impacté
   - Matching exact, partiel, et par mots-clés
   - Score max : 30 points

3. **`_match_by_name`** : Matching par nom (fuzzy matching)
   - Vérifie si l'entreprise est directement mentionnée
   - Utilise `SequenceMatcher` pour le fuzzy matching
   - Matching exact, ticker, fuzzy, et word overlap
   - Score max : 20 points

4. **`_match_by_dependencies`** : Matching par dépendances
   - Vérifie si la chaîne d'approvisionnement est affectée
   - Analyse les dépendances, fournisseurs, et localisations de fabrication
   - Score max : 10 points

5. **`_match_by_segments`** : Matching par segments d'affaires
   - Vérifie l'overlap entre segments business et secteurs réglementés
   - Score max : 10 points

6. **`_match_by_regulatory_risk`** : Matching par risques réglementaires
   - Vérifie l'alignement avec les risques réglementaires existants
   - Score max : 5 points

### Tier 2 : Quant Engine (Traitement Multi-Sources)

**Architecture : Ensemble de processeurs coordonnés**

Le Tier 2 implémente le **Quant Engine** qui traite chaque matching pair à travers plusieurs sources de données pour calculer un impact quantitatif.

#### 1. FinancialDataProcessor - Company Universe DB → SageMaker FinBERT

**Classe : `FinancialDataProcessor`**

Analyse la capacité financière et la résilience des entreprises.

**Métriques analysées :**
- **Liquidity Ratio** : Ratio cash flow libre / revenus
- **Profitability Ratio** : Ratio revenu net / revenus
- **Cash Conversion** : Efficacité de conversion en cash
- **Financial Health Score** (0-100) : Score global de santé financière

**Fonctionnalités :**
- Estime la capacité d'absorption des coûts réglementaires
- Calcule les coûts potentiels vs capacité annuelle
- Classe la force financière (Strong/Moderate/Weak/Critical)

#### 2. RegulatoryDataProcessor - Regulation Table → SageMaker LegalBERT

**Classe : `RegulatoryDataProcessor`**

Analyse la sévérité et l'impact réglementaire.

**Métriques calculées :**
- **Financial Severity** (0-100) : Basé sur les pénalités et seuils monétaires
- **Operational Severity** (0-100) : Basé sur la complexité opérationnelle
- **Compliance Complexity** (0-100) : Basé sur les exigences de conformité
- **Overall Severity** : Score combiné pondéré

**Classification :**
- High Impact (≥75)
- Moderate Impact (50-74)
- Low Impact (25-49)
- Minimal Impact (<25)

#### 3. MarketDataEnricher - Yahoo Finance API → Market Data Processor

**Classe : `MarketDataEnricher`**

Enrichit avec des données de marché en temps réel.

**Données collectées :**
- Prix actuel et market cap
- Volatilité annualisée (1 an)
- Évolution des prix (30 jours)
- Volume et tendance de trading
- Beta et niveau de risque

#### 4. QuantEngine - Orchestrateur Principal

**Classe : `QuantEngine`**

Coordonne le traitement multi-sources et calcule l'impact quantitatif final.

**Pipeline :**
1. Analyse financière → Capacity assessment
2. Analyse réglementaire → Severity assessment
3. Enrichissement marché → Risk assessment
4. Calcul impact final → Quantitative impact score

**Impact Assessment :**
- **Quantitative Impact Score** (0-100) : Score global d'impact
- **Risk Level** : Critical/High/Moderate/Low
- **Factors** : Vulnérabilité financière + Sévérité réglementaire

### Tier 3 : DCF Valuation & Final Risk Score

**Architecture : Valuation Engine avec 3 sub-tiers**

Le Tier 3 implémente une évaluation financière complète de l'impact réglementaire sur la valorisation des entreprises.

#### 3.1. Cash Flow Impact (DCF Tier 1)

**Classe : `DCFValuationEngine._calculate_fcf_impact`**

Calcule l'impact sur le Free Cash Flow.

**Métriques :**
- **Annual FCF Impact** : Impact annuel sur le cash flow libre
- **FCF Impact per Share** : Impact par action
- **FCF Impact Percentage** : Impact relatif en % du FCF actuel

**Scenarios :**
- Conservative: 50% de l'impact
- Base Case: 100%
- Aggressive: 200%

#### 3.2. Risk Premium Adjustment (DCF Tier 2)

**Classe : `DCFValuationEngine._calculate_discount_rate_adjustment`**

Ajuste le taux d'actualisation basé sur le risque réglementaire (CAPM).

**Métriques :**
- **Base Discount Rate** : Taux d'actualisation de base (CAPM)
- **Regulatory Risk Premium** : Premium de risque réglementaire (0-3%)
- **Adjusted Discount Rate** : Taux d'actualisation ajusté
- **Discount Rate Change** : Changement en basis points

**Méthodologie :**
- Taux sans risque : 3%
- Prime de risque marché : 6%
- Ajustement : Sévérité réglementaire × 3%

#### 3.3. DCF Valuation & Price Impact (DCF Tier 3)

**Classe : `DCFValuationEngine._calculate_dcf_valuation`**

Calcule l'impact final sur la valorisation et le prix de l'action.

**Métriques :**
- **NPV Cash Flow Impact** : Valeur actuelle nette de l'impact sur FCF
- **NPV Terminal Value** : Valeur terminale actualisée
- **Total Valuation Impact** : Impact total sur la valorisation
- **Price Impact Percentage** : Impact en % sur le prix de l'action

**Hypothèses :**
- Taux de croissance perpétuelle : 3%
- Période de projection : 5 ans
- Modèle Gordon Growth pour valeur terminale

#### Final Risk Scorer

**Classe : `FinalRiskScorer`**

Combine tous les tiers en un score de risque synthétique final.

**Composants (pondération) :**
- **Exposure Score (30%)** : Exposition géographique/sectorielle
- **Quantitative Impact (40%)** : Sévérité de l'impact financier
- **Price Impact (30%)** : Impact sur valorisation
- **Portfolio Weight** : Multiplicateur basé sur poids S&P 500

**Classification :**
- Critical (≥75)
- High (60-74)
- Moderate (40-59)
- Low (20-39)
- Minimal (<20)

**Facteurs de risque :**
- Exposition géographique
- Dépendance sectorielle
- Sensibilité réglementaire
- Poids dans portefeuille S&P 500

## Structure des Données

### Données Company Universe (Entrée)

Pour chaque entreprise S&P 500 :
- **Market Data** : Secteur, industrie, métriques financières
- **Geography** : Pays/zones d'opérations (has_na, has_eu, countries list)
- **Segments** : Segments d'affaires
- **Supply Chain** : Dépendances, fournisseurs, localisations de fabrication
- **Regulatory Risks** : Risques réglementaires existants mentionnés dans 10-K

### Données Document Réglementaire (Entrée)

- **Métadonnées** : Titre, pays, date d'entrée en vigueur, catégorie
- **Affected Sectors** : Secteurs impactés
- **Affected Entities** : Entités concernées
- **Geographic Scope** : Pays/zones concernés (extrait depuis Comprehend)
- **Measures** : Taxes, restrictions, seuils monétaires
- **Key Requirements** : Exigences clés

### Résultat : Matching Pairs (Sortie)

Chaque paire contient :
```json
{
  "regulation_id": "document_id",
  "regulation_title": "Title",
  "regulation_country": "Country",
  "company_ticker": "TICKER",
  "company_name": "Company Name",
  "exposure_score": 45.5,
  "matching_details": {
    "by_country": {
      "matched": true,
      "score": 25.0,
      "matched_countries": ["EU"],
      "match_type": "region_eu"
    },
    "by_sector": {
      "matched": true,
      "score": 20.0,
      "matched_sectors": ["Financial Services"]
    },
    "by_name": {
      "matched": false,
      "score": 0.0,
      "matched_names": [],
      "match_type": null
    },
    "by_dependencies": {...},
    "by_segments": {...},
    "by_regulatory_risk": {...}
  }
}
```

## Usage

### Basic Usage

```bash
python scripts/impact_calculator.py
```

### Custom Parameters

```bash
python scripts/impact_calculator.py \
  --directives_dir data/generated/extracted_directives \
  --company_universe data/generated/company_universe/company_universe.json \
  --output data/generated/impact_analysis/matching_pairs.json \
  --threshold 0.15 \
  --region us-east-1
```

### Enable Tier 2: Quant Engine

Pour activer l'analyse multi-sources (Quant Engine), ajoutez le flag `--quant-engine` :

```bash
# Tier 1 + Tier 2: Avec analyse quantitative
python scripts/impact_calculator.py --quant-engine

# Limiter le nombre de pairs pour tester (utile pour développement)
python scripts/impact_calculator.py --quant-engine --limit-pairs 10
```

**Note** : Le Quant Engine est optionnel car il peut être plus lent (appels API Yahoo Finance, calculs supplémentaires). Pour un matching rapide, utilisez uniquement Tier 1.

### Parameters

- `--directives_dir` : Répertoire contenant les directives extraites
- `--company_universe` : Fichier JSON du company universe
- `--output` : Chemin de sortie pour les matching pairs
- `--threshold` : Seuil d'exposition (0.0-1.0, défaut: 0.1 = 10%)
- `--region` : Région AWS pour Comprehend (défaut: us-east-1)
- `--quant-engine` : Active Tier 2: Quant Engine (analyse multi-sources)
- `--limit-pairs` : Limite le nombre de pairs à traiter (utile pour tests)

## Logique de Matching Détaillée

### 1. Matching par Pays (`_match_by_country`)

**Critères :**
- Régions : NA (North America), EU (European Union)
- Pays spécifiques : China, Japan, UK, Canada, Germany, France, etc.
- Localisations mentionnées dans le document (via Comprehend)

**Scores :**
- Région match (NA/EU) : 25 points
- Pays spécifique : 20 points
- Mention de localisation : 5 points par localisation
- **Total max : 25 points**

### 2. Matching par Secteur (`_match_by_sector`)

**Critères :**
- Match exact secteur/industrie : 20 points
- Match partiel (contains) : 15 points
- Match industrie : 10 points
- Overlap de mots-clés (≥2 mots communs) : 5 points par secteur

**Scores :**
- **Total max : 30 points** (cumulatif mais capé)

### 3. Matching par Nom (`_match_by_name`)

**Critères :**
- Match exact : 20 points
- Match ticker : 20 points
- Fuzzy matching (similarity > 0.8) : 18 points
- Fuzzy partial (similarity > 0.6) : 12 points
- Word overlap (≥3 mots communs) : 10 points

**Scores :**
- **Total max : 20 points**

**Technique de fuzzy matching :**
- Utilise `difflib.SequenceMatcher` pour calculer la similarité
- Ratio de similarité entre 0.0 et 1.0

### 4. Matching par Dépendances (`_match_by_dependencies`)

**Critères :**
- Analyse de la chaîne d'approvisionnement
- Overlap de mots-clés entre secteurs réglementés et dépendances
- Mentions directes de secteurs dans les dépendances

**Scores :**
- Word overlap (≥3 mots) : 10 points
- Mention directe : 8 points
- **Total max : 10 points**

### 5. Matching par Segments (`_match_by_segments`)

**Critères :**
- Overlap entre segments business et secteurs réglementés

**Scores :**
- 5 points par segment matché
- **Total max : 10 points**

### 6. Matching par Risques Réglementaires (`_match_by_regulatory_risk`)

**Critères :**
- Alignement entre catégorie de réglementation et risques existants
- Keywords : environmental, tax, trade, privacy, labor, financial

**Scores :**
- **Total max : 5 points**

## Calcul du Score d'Exposition Final

```
Exposure Score = min(
    by_country_score +
    by_sector_score +
    by_name_score +
    by_dependencies_score +
    by_segments_score +
    by_regulatory_risk_score,
    100
)
```

## Exemple de Sortie

### Tier 1 Seulement (Matching Pairs)

Le fichier de sortie contient :
1. **Summary** : Statistiques globales
2. **Regulations** : Groupé par régulation, chaque régulation contient :
   - Métadonnées de la régulation
   - Liste des entreprises matchées avec leurs scores et détails

```json
{
  "analysis_date": "2025-11-02T14:49:02",
  "total_pairs": 1796,
  "total_regulations": 6,
  "has_quantitative_analysis": false,
  "regulations": {...},
  "summary_stats": {
    "avg_exposure_score": 35.2,
    "max_exposure_score": 60.0,
    "min_exposure_score": 10.0
  }
}
```

### Tier 1 + Tier 2 + Tier 3 (Complete Analysis)

Avec `--quant-engine`, le fichier inclut des analyses complètes :

```json
{
  "analysis_date": "2025-11-02T14:49:02",
  "total_pairs": 1796,
  "total_regulations": 6,
  "has_quantitative_analysis": true,
  "regulations": {
    "regulation_id": {
      "companies": [
        {
          "ticker": "AAPL",
          "company_name": "Apple Inc.",
          "exposure_score": 45.5,
          "matching_details": {...},
          "quantitative_analysis": {
            "financial_analysis": {
              "financial_health_score": 75.3,
              "can_absorb_impact": true,
              "financial_strength": "Strong",
              "regulatory_cost_capacity": {...}
            },
            "regulatory_analysis": {
              "overall_severity": 68.5,
              "regulatory_classification": "High Impact",
              "financial_severity": 72.0,
              "operational_severity": 65.0
            },
            "market_data": {
              "volatility_annual": 0.2450,
              "price_change_30d": 5.2,
              "risk_level": "Moderate",
              "beta": 1.15
            }
          },
          "impact_assessment": {
            "quantitative_impact_score": 58.2,
            "risk_level": "High",
            "factors": {
              "financial_vulnerability": 24.7,
              "regulatory_severity": 68.5
            }
          },
          "valuation_impact": {
            "tier_1_cash_flow_impact": {
              "annual_fcf_impact": 250000000,
              "fcf_impact_per_share": 0.15,
              "fcf_impact_percentage": 2.5
            },
            "tier_2_discount_rate_adjustment": {
              "base_discount_rate": 9.0,
              "regulatory_risk_premium": 2.05,
              "adjusted_discount_rate": 11.05,
              "discount_rate_change_bps": 205
            },
            "tier_3_dcf_valuation": {
              "npv_cash_flow_impact": -1234567890,
              "npv_terminal_value": -9876543210,
              "total_valuation_impact": -11111111100,
              "price_impact_percentage": -2.5,
              "impact_driver": "cash_flow_and_discount_rate"
            }
          },
          "final_risk_score": {
            "final_risk_score": 48.5,
            "risk_category": "Moderate",
            "risk_components": {
              "exposure_score": 45.5,
              "quantitative_impact_score": 58.2,
              "price_impact_normalized": 5.0,
              "portfolio_weight": 0.0597
            },
            "risk_factors": {
              "geographic_exposure": true,
              "sector_dependency": true,
              "regulatory_sensitivity": true,
              "sp500_weight": 0.0597
            }
          }
        }
      ]
    }
  },
  "summary_stats": {
    "avg_exposure_score": 35.2,
    "quantitative": {
      "avg_impact_score": 42.8,
      "max_impact_score": 78.5,
      "min_impact_score": 15.3
    }
  },
  "has_dcf_valuation": true,
  "has_final_risk_score": true
}
```

## Différences avec `impact_orchestrator.py`

- **`impact_orchestrator.py`** : Analyse complète avec Comprehend, génère des fichiers par directive
- **`impact_calculator.py`** : Focus sur le matching et création de paires regulation-company avec architecture 3-tiers explicite

Les deux peuvent être utilisés complémentairement.

## Requirements

### Dépendances

- `boto3` : Pour AWS Comprehend et SageMaker
- `yfinance` : Pour données de marché via Yahoo Finance API
- `pandas` : Pour manipulation de données
- `python-dateutil` : Pour parsing de dates
- `difflib` : Pour fuzzy matching (inclus dans Python standard library)
- `math` : Pour calculs (inclus dans Python standard library)

### Installation

```bash
pip install -r requirements.txt
```

## Notes

### Tier 1 (Matching Pairs)
- Les scores sont additifs mais chaque dimension a un maximum
- Le score total est capé à 100
- Seules les paires avec score ≥ threshold sont incluses dans les résultats

### Tier 2 (Quant Engine)
- Nécessite une connexion internet pour Yahoo Finance API
- Le cache des données de marché dure 24 heures par défaut
- Les calculs SageMaker (FinBERT/LegalBERT) sont prêts pour intégration mais non actifs par défaut
- L'impact quantitatif est calculé comme : (vulnérabilité financière × 0.4) + (sévérité réglementaire × 0.6)

### Architecture Complète 3-Tiers

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            TIER 1: Impact Orchestrator                              │
│  [Regulatory Documents] → [AWS Comprehend] → [Matching Pairs Engine] → [Pairs]     │
│                                                                                      │
│  Output: Exposure Score (0-100) basé sur:                                          │
│  - Matching pays/zones géographiques                                               │
│  - Matching secteurs                                                               │
│  - Matching nom (fuzzy)                                                            │
│  - Matching dépendances chaîne d'approvisionnement                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                                  ↓ (si --quant-engine)
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            TIER 2: Quant Engine                                     │
│  [Quantitative Analysis] ← [Financial Processor] [Regulatory Processor]            │
│                    ↑                               [Market Enricher]               │
│                    └─────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  Output: Quantitative Impact Score (0-100)                                        │
│  - Financial Health Score & Cost Capacity                                          │
│  - Regulatory Severity & Classification                                            │
│  - Market Risk Assessment                                                          │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                                          ↓ (automatique si Tier 2)
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            TIER 3: DCF Valuation                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  3.1: FCF    │  │  3.2: Risk   │  │  3.3: DCF    │  │ Final Risk   │         │
│  │   Impact     │→ │   Premium    │→ │  Valuation   │→ │   Scorer     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                                      │
│  Output: Final Risk Score (0-100)                                                   │
│  - Cash Flow Impact per Share                                                       │
│  - Discount Rate Adjustment                                                         │
│  - Price Impact %                                                                   │
│  - Portfolio Weight Multiplier                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```


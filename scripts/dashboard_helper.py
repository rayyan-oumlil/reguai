"""
Helper functions for Dashboard data loading in Streamlit app.
Handles loading S&P 500 composition and stock performance data from S3 or local files.
"""

import pandas as pd
import os
import csv
import streamlit as st
from pathlib import Path
import boto3
from botocore.exceptions import ClientError


@st.cache_data
def load_sp500_composition():
    """Charge la composition du S&P 500 depuis S3 ou local"""
    filename = '2025-08-15_composition_sp500.csv'
    s3_key = f'data/raw/{filename}'
    
    print(f"🔄 [LOG] Tentative de chargement: {filename}")
    
    # MÉTHODE 1: Depuis S3 (priorité)
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if bucket_name:
        print(f"☁️ [LOG] S3_BUCKET_NAME détecté: {bucket_name}")
        print(f"☁️ [LOG] Tentative chargement depuis S3: s3://{bucket_name}/{s3_key}")
        try:
            s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'us-west-2'))
            obj = s3.get_object(Bucket=bucket_name, Key=s3_key)
            df = pd.read_csv(obj['Body'])
            print(f"✅ [LOG] SUCCÈS - Données chargées depuis S3: {bucket_name}/{s3_key}")
            # Convertir Weight et Price de string (format européen) en float
            if 'Weight' in df.columns:
                df['Weight'] = df['Weight'].astype(str).str.replace(',', '.').astype(float)
            if 'Price' in df.columns:
                df['Price'] = df['Price'].astype(str).str.replace(',', '.').astype(float)
            return df
        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"❌ [LOG] ERREUR S3 ({error_code}): {e}")
        except Exception as e:
            print(f"❌ [LOG] ERREUR S3 (autre): {e}")
    else:
        print("ℹ️ [LOG] S3_BUCKET_NAME non configuré - utilisation locale uniquement")
    
    # MÉTHODE 2: Depuis fichiers locaux (fallback)
    print(f"📁 [LOG] Tentative chargement depuis fichiers locaux...")
    possible_paths = [
        'data/raw/2025-08-15_composition_sp500.csv',
        '2025-08-15_composition_sp500.csv',
        '../data/raw/2025-08-15_composition_sp500.csv'
    ]
    
    for csv_path in possible_paths:
        try:
            full_path = Path(csv_path).resolve()
            if full_path.exists():
                print(f"✅ [LOG] SUCCÈS - Fichier trouvé localement: {full_path}")
                df = pd.read_csv(csv_path)
                # Convertir Weight et Price de string (format européen) en float
                if 'Weight' in df.columns:
                    df['Weight'] = df['Weight'].astype(str).str.replace(',', '.').astype(float)
                if 'Price' in df.columns:
                    df['Price'] = df['Price'].astype(str).str.replace(',', '.').astype(float)
                return df
            else:
                print(f"❌ [LOG] Fichier non trouvé: {full_path}")
        except Exception as e:
            print(f"❌ [LOG] Erreur lecture {csv_path}: {e}")
            continue
    
    print(f"❌ [LOG] ÉCHEC - Fichier non trouvé ni S3 ni local")
    return None


@st.cache_data
def load_stocks_performance():
    """Charge les métriques de performance depuis S3 ou local"""
    filename = '2025-09-26_stocks-performance.csv'
    s3_key = f'data/raw/{filename}'
    
    print(f"🔄 [LOG] Tentative de chargement: {filename}")
    
    # MÉTHODE 1: Depuis S3 (priorité)
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if bucket_name:
        print(f"☁️ [LOG] S3_BUCKET_NAME détecté: {bucket_name}")
        print(f"☁️ [LOG] Tentative chargement depuis S3: s3://{bucket_name}/{s3_key}")
        try:
            s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'us-west-2'))
            obj = s3.get_object(Bucket=bucket_name, Key=s3_key)
            # Le CSV a un format bizarre: ligne 1 vide, ligne 2 mal formatée
            # Parser correctement le CSV
            csv_content = obj['Body'].read().decode('utf-8')
            lines = csv_content.strip().split('\n')
            
            # Skip ligne 1 (vide/BOM) et ligne 2 (mal formatée avec NVDA)
            # Les vraies données commencent à partir de la ligne 3 (index 2)
            # Structure réelle des colonnes: Symbol, Company Name, Market Cap, Revenue, Op. Income, Net Income, EPS, FCF
            headers = ['Symbol', 'Company Name', 'Market Cap', 'Revenue', 'Op. Income', 'Net Income', 'EPS', 'FCF']
            
            # Parser à partir de la ligne 3 (les données réelles commencent là)
            data_lines = lines[2:] if len(lines) > 2 else []
            
            # Parser CSV
            reader = csv.reader(data_lines)
            rows = []
            for row in reader:
                if len(row) > 0:  # Ignorer lignes vides
                    rows.append(row)
            
            # Créer DataFrame
            df = pd.DataFrame(rows)
            
            # Renommer colonnes (prendre les 8 premières colonnes principales)
            if len(df.columns) >= 8:
                df.columns = headers + [f'Extra_{i}' for i in range(8, len(df.columns))]
            elif len(df.columns) >= 2:
                df.columns = ['Symbol', 'Company Name'] + [f'Col_{i}' for i in range(2, len(df.columns))]
            
            # Convertir les colonnes numériques (Market Cap, Revenue, EPS, FCF, etc.)
            numeric_cols = ['Market Cap', 'Revenue', 'Op. Income', 'Net Income', 'EPS', 'FCF']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            print(f"✅ [LOG] SUCCÈS - Données chargées depuis S3: {bucket_name}/{s3_key} ({len(df)} lignes)")
            print(f"✅ [LOG] Colonnes disponibles: {list(df.columns[:8])}")
            # Note: CSV contient plus que S&P 500, sera filtré dans dashboard
            return df
        except ClientError as e:
            error_code = e.response['Error']['Code']
            print(f"❌ [LOG] ERREUR S3 ({error_code}): {e}")
        except Exception as e:
            print(f"❌ [LOG] ERREUR S3 (autre): {e}")
    else:
        print("ℹ️ [LOG] S3_BUCKET_NAME non configuré - utilisation locale uniquement")
    
    # MÉTHODE 2: Depuis fichiers locaux (fallback)
    print(f"📁 [LOG] Tentative chargement depuis fichiers locaux...")
    possible_paths = [
        'data/raw/2025-09-26_stocks-performance.csv',
        '2025-09-26_stocks-performance.csv',
        '../data/raw/2025-09-26_stocks-performance.csv'
    ]
    
    for csv_path in possible_paths:
        try:
            full_path = Path(csv_path).resolve()
            if full_path.exists():
                print(f"✅ [LOG] SUCCÈS - Fichier trouvé localement: {full_path}")
                # Le CSV a un format bizarre: ligne 1 vide, ligne 2 mal formatée
                with open(csv_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Skip ligne 1 (vide/BOM) et ligne 2 (mal formatée avec NVDA)
                # Les vraies données commencent à partir de la ligne 3
                # Structure: Symbol, Company Name, Market Cap, Revenue, Op. Income, Net Income, EPS, FCF
                headers = ['Symbol', 'Company Name', 'Market Cap', 'Revenue', 'Op. Income', 'Net Income', 'EPS', 'FCF']
                data_lines = lines[2:] if len(lines) > 2 else []
                
                # Parser CSV
                reader = csv.reader(data_lines)
                rows = []
                for row in reader:
                    if len(row) > 0:  # Ignorer lignes vides
                        rows.append(row)
                
                # Créer DataFrame
                df = pd.DataFrame(rows)
                
                # Renommer colonnes
                if len(df.columns) >= 8:
                    df.columns = headers + [f'Extra_{i}' for i in range(8, len(df.columns))]
                elif len(df.columns) >= 2:
                    df.columns = ['Symbol', 'Company Name'] + [f'Col_{i}' for i in range(2, len(df.columns))]
                
                # Convertir les colonnes numériques (Market Cap, Revenue, EPS, FCF, etc.)
                numeric_cols = ['Market Cap', 'Revenue', 'Op. Income', 'Net Income', 'EPS', 'FCF']
                for col in numeric_cols:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
                print(f"✅ [LOG] CSV chargé: {len(df)} lignes (contient toutes entreprises, sera filtré)")
                print(f"✅ [LOG] Colonnes disponibles: {list(df.columns[:8])}")
                # Note: CSV contient plus que S&P 500, sera filtré dans dashboard
                return df
            else:
                print(f"❌ [LOG] Fichier non trouvé: {full_path}")
        except Exception as e:
            print(f"❌ [LOG] Erreur lecture {csv_path}: {e}")
            continue
    
    print(f"❌ [LOG] ÉCHEC - Fichier non trouvé ni S3 ni local")
    return None


@st.cache_data
def load_company_universe():
    """Charge company_universe.json depuis local ou S3 (source principale pour le dashboard)"""
    import json
    
    company_universe_path = Path('data/generated/company_universe/company_universe.json')
    s3_key = 'data/generated/company_universe/company_universe.json'
    
    # MÉTHODE 1: Depuis S3 (priorité)
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if bucket_name:
        try:
            s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'us-west-2'))
            obj = s3.get_object(Bucket=bucket_name, Key=s3_key)
            company_universe = json.loads(obj['Body'].read().decode('utf-8'))
            print(f"✅ [LOG] Company Universe chargé depuis S3: {bucket_name}/{s3_key} ({len(company_universe)} entreprises)")
            return company_universe
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code != 'NoSuchKey':  # Si pas dans S3, essayer local
                print(f"⚠️ [LOG] Erreur S3 pour company_universe ({error_code}): {e}")
        except Exception as e:
            print(f"⚠️ [LOG] Erreur S3 company_universe: {e}")
    
    # MÉTHODE 2: Depuis local (fallback)
    if company_universe_path.exists():
        try:
            with open(company_universe_path, 'r', encoding='utf-8') as f:
                company_universe = json.load(f)
            print(f"✅ [LOG] Company Universe chargé depuis local: {len(company_universe)} entreprises")
            return company_universe
        except Exception as e:
            print(f"⚠️ [LOG] Erreur chargement company_universe: {e}")
            return None
    else:
        print(f"ℹ️ [LOG] Company Universe non trouvé: {company_universe_path}")
        return None


@st.cache_data
def company_universe_to_dataframes(company_universe: dict):
    """
    Convertit company_universe.json en DataFrames pour le dashboard
    
    Retourne:
    - composition_df: DataFrame avec Weight, Price, Symbol, Company (pour S&P 500)
    - performance_df: DataFrame avec Market Cap, Revenue, EPS, FCF, etc. (données de marché)
    """
    if not company_universe:
        return None, None
    
    # Préparer les données
    composition_rows = []
    performance_rows = []
    
    for ticker, company_data in company_universe.items():
        market_data = company_data.get('market_data', {})
        data_points = company_data.get('data_points', {})
        
        # Composition S&P 500
        sector_value = market_data.get('sector', 'Unknown')
        if sector_value is None or sector_value == '':
            sector_value = 'Unknown'
            
        composition_rows.append({
            'Symbol': ticker,
            'Company': market_data.get('company_name', data_points.get('company_name', ticker)),
            'Weight': market_data.get('sp500_weight', 0.0),
            'Price': market_data.get('current_price', 0.0),
            'Sector': sector_value,
            'Industry': market_data.get('industry', 'Unknown')
        })
        
        # Performance (Market Data + 10-K enrichi)
        performance_rows.append({
            'Symbol': ticker,
            'Company Name': market_data.get('company_name', data_points.get('company_name', ticker)),
            'Market Cap': market_data.get('market_cap', 0.0),
            'Revenue': market_data.get('revenue', 0.0),
            'Op. Income': market_data.get('operating_income', 0.0),
            'Net Income': market_data.get('net_income', 0.0),
            'EPS': market_data.get('eps', 0.0),
            'FCF': market_data.get('free_cash_flow', 0.0),
            'P/E Ratio': market_data.get('pe_ratio', None),
            'Profit Margin': market_data.get('profit_margin', None),
            'Sector': sector_value,  # Même valeur que dans composition
            'Industry': market_data.get('industry', 'Unknown'),
            # Données 10-K
            'Has NA Operations': data_points.get('geography', {}).get('has_na', False),
            'Has EU Operations': data_points.get('geography', {}).get('has_eu', False),
            'Num Segments': len(data_points.get('segments', [])),
            'Company Type': data_points.get('company_type', 'Unknown')
        })
    
    # Créer DataFrames
    composition_df = pd.DataFrame(composition_rows)
    performance_df = pd.DataFrame(performance_rows)
    
    # Convertir colonnes numériques
    numeric_cols_comp = ['Weight', 'Price']
    for col in numeric_cols_comp:
        if col in composition_df.columns:
            composition_df[col] = pd.to_numeric(composition_df[col], errors='coerce')
    
    numeric_cols_perf = ['Market Cap', 'Revenue', 'Op. Income', 'Net Income', 'EPS', 'FCF', 'P/E Ratio', 'Profit Margin']
    for col in numeric_cols_perf:
        if col in performance_df.columns:
            performance_df[col] = pd.to_numeric(performance_df[col], errors='coerce')
    
    print(f"✅ [LOG] Company Universe converti: {len(composition_df)} entreprises dans composition, {len(performance_df)} dans performance")
    print(f"✅ [LOG] Colonnes composition: {list(composition_df.columns)}")
    print(f"✅ [LOG] Colonnes performance: {list(performance_df.columns)}")
    
    return composition_df, performance_df


def render_dashboard_kpis(composition, performance, company_universe):
    """Affiche les KPIs principaux du dashboard"""
    import streamlit as st
    
    # Calculs préliminaires
    num_companies = len(composition) if composition is not None else 0
    
    # KPIs - 4 métriques essentielles
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Capitalisation totale
        if performance is not None and 'Market Cap' in performance.columns:
            total_market_cap = performance['Market Cap'].sum() / 1e12
            st.metric(
                "💰 Capitalisation totale",
                f"${total_market_cap:.2f}T",
                delta="Portefeuille S&P 500"
            )
        else:
            st.metric("💰 Capitalisation totale", "N/A")
    
    with col2:
        # Revenus totaux
        if performance is not None and 'Revenue' in performance.columns:
            total_revenue = performance['Revenue'].sum() / 1e12
            st.metric(
                "📈 Revenus annuels",
                f"${total_revenue:.2f}T",
                delta="Total combiné"
            )
        else:
            st.metric("📈 Revenus annuels", "N/A")
    
    with col3:
        # Secteurs
        if composition is not None and 'Sector' in composition.columns:
            num_sectors = composition['Sector'].nunique()
            st.metric(
                "🏢 Secteurs",
                num_sectors,
                delta=f"{num_companies} entreprises"
            )
        else:
            st.metric("🏢 Secteurs", "N/A")
    
    with col4:
        # Exposition UE
        if performance is not None and 'Has EU Operations' in performance.columns:
            eu_companies = performance['Has EU Operations'].sum()
            eu_percentage = (eu_companies / num_companies * 100) if num_companies > 0 else 0
            st.metric(
                "🇪🇺 Exposées UE",
                f"{eu_companies}",
                delta=f"{eu_percentage:.1f}%"
            )
        else:
            st.metric("🇪🇺 Exposées UE", "N/A")


def render_sector_treemap(performance):
    """Affiche le treemap de capitalisation par secteur"""
    import streamlit as st
    import plotly.express as px
    
    st.subheader("🎨 Vue d'Ensemble - Capitalisation par Secteur")
    
    if performance is not None and 'Market Cap' in performance.columns and 'Sector' in performance.columns:
        # Filtrer les lignes sans secteur valide
        performance_valid = performance[
            performance['Sector'].notna() & 
            (performance['Sector'] != 'Unknown') &
            (performance['Sector'] != '')
        ]
        
        if len(performance_valid) > 0:
            # Agréger par secteur
            sector_data = performance_valid.groupby('Sector', as_index=False).agg({
                'Market Cap': 'sum',
                'Symbol': 'count'
            }).rename(columns={'Symbol': 'Nombre'})
            sector_data['Market Cap (T$)'] = sector_data['Market Cap'] / 1e12
            sector_data = sector_data.sort_values('Market Cap', ascending=False)

            # Treemap avec Plotly Express
            fig_treemap = px.treemap(
                sector_data,
                path=['Sector'],
                values='Market Cap (T$)',
                color='Market Cap (T$)',
                color_continuous_scale='Viridis',
                hover_data=['Nombre'],
                title='Distribution de Capitalisation par Secteur',
                height=500
            )
            fig_treemap.update_traces(
                texttemplate='%{label}<br>$%{value:.2f}T<br>%{customdata[0]} entreprises',
                hovertemplate='<b>%{label}</b><br>Capitalisation: $%{value:.2f}T<br>Entreprises: %{customdata[0]}<extra></extra>'
            )
            st.plotly_chart(fig_treemap, use_container_width=True)
        else:
            print("⚠️ [LOG] Aucune donnée de secteur valide disponible")
    else:
        if performance is None:
            print("ℹ️ [LOG] Données de performance non disponibles")
        elif 'Sector' not in performance.columns:
            print("ℹ️ [LOG] Colonne 'Sector' non disponible dans performance")


def render_composition_charts(composition):
    """Affiche les graphiques de composition S&P 500"""
    import streamlit as st
    import plotly.express as px
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("Top 10 Entreprises par Poids")
        if composition is not None and 'Weight' in composition.columns:
            top10 = composition.nlargest(10, 'Weight')
            fig1 = px.bar(
                top10,
                x='Symbol',
                y='Weight',
                title='Top 10 - Poids dans le S&P 500',
                labels={'Weight': 'Poids (%)', 'Symbol': 'Symbole'},
                color='Weight',
                color_continuous_scale='Blues'
            )
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, width='stretch')
    
    with col_right:
        st.subheader("Distribution des Poids")
        if composition is not None and 'Weight' in composition.columns:
            fig2 = px.histogram(
                composition,
                x='Weight',
                nbins=50,
                title='Distribution des Poids dans le S&P 500',
                labels={'Weight': 'Poids (%)', 'count': "Nombre d'entreprises"}
            )
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, width='stretch')


def render_performance_table(performance, composition):
    """Affiche le tableau de performance des entreprises"""
    import streamlit as st
    import numpy as np
    
    st.subheader("💰 Métriques de Performance (Top 20)")
    if len(performance) > 0:
        # Plus besoin de filtrer : performance vient déjà de company_universe (500 entreprises S&P 500)
        performance_sp500 = performance.copy()
        
        # Vérifier les colonnes disponibles
        available_cols = performance_sp500.columns.tolist()
        
        # Colonnes souhaitées avec fallback
        desired_cols = ['Symbol', 'Company Name', 'Market Cap', 'Revenue', 'EPS', 'FCF']
        display_cols = [col for col in desired_cols if col in available_cols]
        
        # Debug: vérifier EPS
        if 'EPS' in available_cols:
            eps_non_null = performance_sp500['EPS'].notna().sum()
            print(f"✅ [LOG] EPS disponible: {eps_non_null}/{len(performance_sp500)} entreprises ont une valeur EPS")
        
        # Trier par Market Cap si disponible
        if 'Market Cap' in available_cols:
            top_performers = performance_sp500.nlargest(20, 'Market Cap')
        else:
            numeric_cols = performance_sp500.select_dtypes(include=[np.number]).columns.tolist()
            if numeric_cols:
                top_performers = performance_sp500.nlargest(20, numeric_cols[0])
            else:
                top_performers = performance_sp500.head(20)
        
        # Afficher avec les colonnes disponibles
        if display_cols:
            st.dataframe(
                top_performers[display_cols],
                width='stretch',
                height=400
            )
        else:
            st.dataframe(
                top_performers,
                width='stretch',
                height=400
            )
            print(f"ℹ️ [LOG] Colonnes disponibles: {', '.join(available_cols[:5])}...")


def render_composition_table(composition):
    """Affiche le tableau complet de composition avec recherche"""
    import streamlit as st
    
    st.subheader("📋 Composition Complète du S&P 500")
    search_term = st.text_input("🔍 Rechercher une entreprise", "")
    
    if search_term:
        filtered = composition[
            composition['Company'].str.contains(search_term, case=False) |
            composition['Symbol'].str.contains(search_term, case=False)
        ]
        st.dataframe(
            filtered.sort_values('Weight', ascending=False),
            width='stretch',
            height=400
        )
    else:
        st.dataframe(
            composition.sort_values('Weight', ascending=False),
            width='stretch',
            height=400
        )


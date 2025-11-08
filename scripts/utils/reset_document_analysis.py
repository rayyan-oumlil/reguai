#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de réinitialisation pour la page d'analyse de documents

Ce script permet de :
1. Optionnellement supprimer toutes les extractions
2. Optionnellement supprimer les analyses d'impact associées

Usage:
    python scripts/reset_document_analysis.py --clear-extractions # Supprime les extractions
    python scripts/reset_document_analysis.py --full-reset        # Réinitialisation complète
"""

import json
import argparse
import shutil
import sys
import io
from pathlib import Path
from typing import List, Optional

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Chemins
EXTRACTIONS_DIR = Path("data/generated/extracted_directives")
IMPACT_ANALYSIS_DIR = Path("data/generated/impact_analysis")


def clear_extractions(keep_all_directives: bool = False) -> int:
    """Supprime toutes les extractions sauf all_directives_extracted.json si demandé"""
    if not EXTRACTIONS_DIR.exists():
        print(f"[WARNING] Repertoire d'extractions n'existe pas: {EXTRACTIONS_DIR}")
        return 0
    
    deleted_count = 0
    kept_files = ['all_directives_extracted.json', 'directives_summary.csv'] if keep_all_directives else []
    
    for extraction_file in EXTRACTIONS_DIR.glob("*_extracted.json"):
        if keep_all_directives and extraction_file.name in kept_files:
            print(f"[CONSERVE] Conserve: {extraction_file.name}")
            continue
        
        try:
            extraction_file.unlink()
            deleted_count += 1
            print(f"[SUPPRIME] Supprime: {extraction_file.name}")
        except Exception as e:
            print(f"[ERREUR] Erreur suppression {extraction_file.name}: {e}")
    
    # Supprimer aussi le CSV de résumé si demandé
    if not keep_all_directives:
        csv_file = EXTRACTIONS_DIR / "directives_summary.csv"
        if csv_file.exists():
            try:
                csv_file.unlink()
                print(f"[SUPPRIME] Supprime: {csv_file.name}")
            except Exception as e:
                print(f"[ERREUR] Erreur suppression {csv_file.name}: {e}")
    
    return deleted_count


def clear_impact_analysis() -> int:
    """Supprime toutes les analyses d'impact"""
    if not IMPACT_ANALYSIS_DIR.exists():
        print(f"[WARNING] Repertoire d'analyses d'impact n'existe pas: {IMPACT_ANALYSIS_DIR}")
        return 0
    
    deleted_count = 0
    
    # Supprimer les fichiers individuels d'impact
    for impact_file in IMPACT_ANALYSIS_DIR.glob("*_impact.json"):
        try:
            impact_file.unlink()
            deleted_count += 1
            print(f"[SUPPRIME] Supprime: {impact_file.name}")
        except Exception as e:
            print(f"[ERREUR] Erreur suppression {impact_file.name}: {e}")
    
    # Supprimer matching_pairs.json
    matching_pairs = IMPACT_ANALYSIS_DIR / "matching_pairs.json"
    if matching_pairs.exists():
        try:
            matching_pairs.unlink()
            deleted_count += 1
            print(f"[SUPPRIME] Supprime: matching_pairs.json")
        except Exception as e:
            print(f"[ERREUR] Erreur suppression matching_pairs.json: {e}")
    
    # Garder impact_analysis_index.json car c'est juste un index
    # Mais on peut le réinitialiser aussi
    index_file = IMPACT_ANALYSIS_DIR / "impact_analysis_index.json"
    if index_file.exists():
        try:
            # Réinitialiser plutôt que supprimer
            with open(index_file, 'w') as f:
                json.dump({
                    "analysis_date": None,
                    "total_directives": 0,
                    "total_companies": 0,
                    "exposure_threshold": 0.5,
                    "directives": [],
                    "summary_stats": {
                        "total_matches": 0,
                        "total_filtered_matches": 0,
                        "avg_companies_per_directive": 0
                    }
                }, f, indent=2)
            deleted_count += 1
            print(f"[REINITIALISE] Reinitialise: impact_analysis_index.json")
        except Exception as e:
            print(f"[ERREUR] Erreur reinitalisation index: {e}")
    
    return deleted_count


def main():
    parser = argparse.ArgumentParser(
        description="Réinitialiser la page d'analyse de documents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s --clear-extractions      # Supprime les extractions
  %(prog)s --full-reset             # Réinitialisation complète
  %(prog)s --clear-extractions --keep-summary  # Garde all_directives_extracted.json
        """
    )
    
    parser.add_argument(
        '--clear-extractions',
        action='store_true',
        help='Supprimer toutes les extractions (force re-extraction)'
    )
    
    parser.add_argument(
        '--clear-impact',
        action='store_true',
        help='Supprimer les analyses d\'impact'
    )
    
    parser.add_argument(
        '--keep-summary',
        action='store_true',
        help='Garder all_directives_extracted.json et directives_summary.csv (avec --clear-extractions)'
    )
    
    parser.add_argument(
        '--full-reset',
        action='store_true',
        help='Réinitialisation complète (extractions + impact)'
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("REINITIALISATION DE L'ANALYSE DE DOCUMENTS")
    print("=" * 60)
    print()
    
    # Déterminer les actions
    if args.full_reset:
        clear_extracts = True
        clear_impact = True
        keep_summary = False
    else:
        clear_extracts = args.clear_extractions
        clear_impact = args.clear_impact
        keep_summary = args.keep_summary
    
    # 1. Supprimer les extractions si demandé
    if clear_extracts:
        print("ETAPE 1: Suppression des extractions...")
        deleted = clear_extractions(keep_all_directives=keep_summary)
        if deleted > 0:
            print(f"   [OK] {deleted} fichier(s) supprime(s)\n")
        else:
            print("   [INFO] Aucune extraction a supprimer\n")
    else:
        print("ETAPE 1: Conservation des extractions (utiliser --clear-extractions pour supprimer)\n")
    
    # 2. Supprimer les analyses d'impact si demandé
    if clear_impact:
        print("ETAPE 2: Suppression des analyses d'impact...")
        deleted = clear_impact_analysis()
        if deleted > 0:
            print(f"   [OK] {deleted} fichier(s) supprime(s)\n")
        else:
            print("   [INFO] Aucune analyse d'impact a supprimer\n")
    else:
        print("ETAPE 2: Conservation des analyses d'impact (utiliser --clear-impact pour supprimer)\n")
    
    print("=" * 60)
    print("[OK] REINITIALISATION TERMINEE")
    print("=" * 60)
    print()
    print("PROCHAINES ETAPES:")
    print("   1. Ouvrez l'application Streamlit")
    print("   2. Allez a la page 'Analyse de Documents'")
    if clear_extracts:
        print("   3. Vous pouvez recommencer les extractions")
    print()
    
    return 0


if __name__ == "__main__":
    exit(main())


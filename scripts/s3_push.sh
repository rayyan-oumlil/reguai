#!/bin/bash

# S3 Push Script
# Pushes local changes to S3, including deletions and file moves
# This uses --delete flag to ensure exact sync with local state

set -e

S3_BUCKET="s3://csv-file-store-70f60a80/dzd-dcu0rbu5jh57bk/3sh2ycptkh3t00/shared"
LOCAL_DIR="./"

echo "🚀 Pushing files to S3..."
echo "Source: $LOCAL_DIR"
echo "Destination: $S3_BUCKET"
echo ""
echo "⚠️  WARNING: This will:"
echo "   - Upload all new and modified files"
echo "   - DELETE files from S3 that don't exist locally"
echo "   - Make S3 state EXACTLY match local state"
echo ""

read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "❌ Push cancelled"
  exit 1
fi

.venv/bin/aws s3 sync "$LOCAL_DIR" "$S3_BUCKET" \
  --exclude ".venv/*" \
  --exclude ".venv/**" \
  --exclude ".venv" \
  --exclude "venv/*" \
  --exclude "venv/**" \
  --exclude "venv" \
  --exclude ".venv" \
  --exclude "jeu_de_donnees/*" \
  --exclude "jeu_de_donnees/**" \
  --exclude "jeu_de_donnees" \
  --exclude "fillings/*" \
  --delete \



echo ""
echo "✅ Push completed successfully!"
echo "S3 state now matches local state exactly"

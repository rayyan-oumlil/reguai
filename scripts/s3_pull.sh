#!/bin/bash

# S3 Pull Script
# Pulls all files from S3 bucket to local workspace
# Preserves directory structure

set -e

S3_BUCKET="s3://csv-file-store-70f60a80/dzd-dcu0rbu5jh57bk/3sh2ycptkh3t00/shared"
LOCAL_DIR="./"

echo "🔄 Pulling files from S3..."
echo "Source: $S3_BUCKET"
echo "Destination: $LOCAL_DIR"

aws s3 sync "$S3_BUCKET" "$LOCAL_DIR" \
  --exclude ".venv/*" \
  --exclude ".venv/**" \
  --exclude ".venv" \
  --exclude "jeu_de_donnees/*" \
  --exclude "jeu_de_donnees/**" \
  --exclude "jeu_de_donnees" \
  --exclude "fillings/*" \

echo "✅ Pull completed successfully!"
echo ""
echo "Next steps:"
echo "1. Run ./scripts/s3_organize.sh to reorganize files locally"
echo "2. Run ./scripts/s3_push.sh to push changes to S3"

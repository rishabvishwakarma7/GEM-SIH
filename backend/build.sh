#!/usr/bin/env bash
# Render build script — runs on every deploy
set -e

echo "==> Installing dependencies..."
pip install -r requirements.txt

echo "==> Running database migrations..."
python migrate_upgrade.py

echo "==> Seeding admin user (skipped if already exists)..."
python init_db.py

echo "==> Build complete."

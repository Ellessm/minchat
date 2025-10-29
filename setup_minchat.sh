#!/bin/bash
# MinChat macOS Setup Script (Apple Silicon / Python 3.11)

set -e  # stop on first error

echo "=== MinChat Setup Script ==="

# 1️⃣ Install Python 3.11 via Homebrew (skip if already installed)
if ! command -v python3.11 &>/dev/null; then
    echo "Installing Python 3.11 via Homebrew..."
    brew install python@3.11
fi

# 2️⃣ Create virtual environment
echo "Creating virtual environment..."
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate

# 3️⃣ Upgrade pip, setuptools, wheel
echo "Upgrading pip, setuptools, wheel..."
pip install --upgrade pip setuptools wheel

# 4️⃣ Install dependencies
echo "Installing backend dependencies..."
pip install -r requirements.txt

# 5️⃣ Initialize database (creates tables)
echo "Initializing SQLite database..."
python - <<EOF
from backend.database import Base, engine
from backend.models import User
Base.metadata.create_all(bind=engine)
print("Database initialized successfully.")
EOF

echo "Setup complete!"

echo "Starting backend..."
uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000

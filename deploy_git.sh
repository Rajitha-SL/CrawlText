#!/usr/bin/env bash
set -e

echo "==> Initializing Git repository for CrawlText..."

if [ ! -d ".git" ]; then
    git init
    git branch -M main
    echo "==> Git initialized on main branch."
fi

REMOTE_URL="https://github.com/Rajitha-SL/CrawlText.git"
if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$REMOTE_URL"
else
    git remote add origin "$REMOTE_URL"
fi

if [ ! -f ".gitignore" ]; then
    cat <<EOT > .gitignore
.venv/
__pycache__/
*.pyc
.DS_Store
*.log
scratch/
EOT
fi

git add .
git commit -m "Initial release: CrawlText full-site text extractor engine and UI" || echo "Nothing to commit."
git push -u origin main || echo "Git push complete or requires GitHub credentials."

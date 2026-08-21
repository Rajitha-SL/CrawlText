# PowerShell script to initialize Git, commit, and push to GitHub repository
$ErrorActionPreference = "Continue"

Write-Host "==> Initializing Git repository for CrawlText..." -ForegroundColor Cyan

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
    Write-Host "==> Git initialized with default branch 'main'." -ForegroundColor Green
} else {
    Write-Host "==> Git repository already initialized." -ForegroundColor Yellow
}

# Set remote origin
$remoteUrl = "https://github.com/Rajitha-SL/CrawlText.git"
$remotes = git remote
if ($remotes -contains "origin") {
    git remote set-url origin $remoteUrl
    Write-Host "==> Updated remote origin to $remoteUrl" -ForegroundColor Green
} else {
    git remote add origin $remoteUrl
    Write-Host "==> Added remote origin $remoteUrl" -ForegroundColor Green
}

# Create .gitignore if not existing
if (-not (Test-Path ".gitignore")) {
    @"
.venv/
__pycache__/
*.pyc
.DS_Store
*.log
scratch/
"@ | Out-File -Encoding utf8 .gitignore
    Write-Host "==> Created .gitignore" -ForegroundColor Green
}

# Stage and Commit
git add .
$commitMsg = "Initial release: CrawlText full-site text extractor engine and UI"
git commit -m "$commitMsg"

# Push to GitHub
Write-Host "==> Pushing to origin main..." -ForegroundColor Cyan
git push -u origin main

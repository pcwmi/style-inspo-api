#!/bin/bash
# Setup script for GitHub repository

set -e  # Exit on error

echo "🚀 Setting up GitHub repository for style-inspo-api"
echo ""

# Check if git is already initialized
if [ -d .git ]; then
    echo "⚠️  Git is already initialized"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "📦 Initializing git repository..."
    git init
fi

echo ""
echo "📝 Staging files..."
git add .

echo ""
echo "📊 Files to be committed:"
git status --short | head -20

echo ""
read -p "Create initial commit? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    git commit -m "Initial commit: FastAPI + Next.js migration

- FastAPI backend with RQ background jobs
- Next.js frontend with mobile-first design
- Full feature parity with Streamlit app
- Editorial magazine design system (DM Sans, Libre Baskerville)
- Mobile-optimized UX with safe-area support"
    
    echo ""
    echo "✅ Initial commit created!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Create a new repository on GitHub: https://github.com/new"
    echo "   - Name: style-inspo-api"
    echo "   - DO NOT initialize with README/gitignore"
    echo ""
    echo "2. Run these commands (replace YOUR_USERNAME):"
    echo "   git remote add origin https://github.com/YOUR_USERNAME/style-inspo-api.git"
    echo "   git branch -M main"
    echo "   git push -u origin main"
    echo ""
else
    echo "⏭️  Skipped commit. Run 'git commit' manually when ready."
fi


# Fix Git Remote and Push

Run these commands in order:

## Step 1: Check current remote
```bash
git remote -v
```

## Step 2: Remove existing remote (if it has wrong URL)
```bash
git remote remove origin
```

## Step 3: Add correct remote
```bash
git remote add origin https://github.com/pcwmi/style-inspo-api.git
```

## Step 4: Verify remote is set correctly
```bash
git remote -v
```
Should show:
```
origin  https://github.com/pcwmi/style-inspo-api.git (fetch)
origin  https://github.com/pcwmi/style-inspo-api.git (push)
```

## Step 5: Ensure branch is named 'main'
```bash
git branch -M main
```

## Step 6: Push to GitHub
```bash
git push -u origin main
```

If you get authentication errors, you may need to:
- Use a Personal Access Token instead of password
- Or set up SSH keys

Let me know if you encounter any errors!


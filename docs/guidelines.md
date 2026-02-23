# Deployment Guidelines

## 1. Local Development
All changes (code fixes, UI modifications, etc.) must first be done on this virtual machine (the local Mac environment). **Never** make changes directly on the production VPS (`144.217.12.20`).

## 2. Pushing to GitHub
Once changes are verified locally, they must be committed and pushed to the project's GitHub repository.
```bash
git add .
git commit -m "Description of changes"
git push origin main
```

## 3. Pulling on Production
Do not use `scp` or `rsync` to hack changes directly into production. Instead, SSH into the VPS and use Git to pull the latest changes.
```bash
ssh debian@144.217.12.20
cd ~/diary-bot
git pull origin main
docker compose build
docker compose up -d
```

## 4. Testing and Logging
Always check the logs after a deployment to ensure the bot is functioning correctly and the new environment variables or keys are picked up.
```bash
docker compose logs -f bot
```
*If a test suite is available (`pytest`), it should be run locally before step 2.*

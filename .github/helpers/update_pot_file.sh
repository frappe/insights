#!/bin/bash
set -e
cd ~ || exit

echo "Setting Up Bench..."

pip install frappe-bench
bench -v init frappe-bench --skip-assets --skip-redis-config-generation --python "$(which python)" --frappe-branch "${BASE_BRANCH}"

cd ./frappe-bench || exit

echo "Get Insights..."
bench get-app insights "${GITHUB_WORKSPACE}" --skip-assets 

echo "Generating POT file..."
bench generate-pot-file --app insights

cd ./apps/insights || exit

echo "Configuring git user..."
git config user.email "developers@erpnext.com"
git config user.name "frappe-pr-bot"

echo "Setting the correct git remote..."
git remote set-url upstream "https://x-access-token:${GH_TOKEN}@github.com/frappe/insights.git"

echo "Creating a new branch..."
isodate=$(date -u +"%Y-%m-%d")
branch_name="pot_${BASE_BRANCH}_${isodate}"
git checkout -b "${branch_name}"

echo "Commiting changes..."
git add insights/locale/main.pot
git commit -m "chore: update POT file"

git push -u upstream "${branch_name}"

echo "Creating a PR..."
gh pr create --fill --base "${BASE_BRANCH}" --head "${branch_name}" -R frappe/insights
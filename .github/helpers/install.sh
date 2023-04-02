#!/bin/bash
set -e
cd ~ || exit

echo "Setting Up Bench..."

pip install frappe-bench
bench -v init frappe-bench --skip-assets --python "$(which python)"
mariadb --host 127.0.0.1 --port 3306 -u root -pfrappe -e "SET GLOBAL character_set_server = 'utf8mb4'";
mariadb --host 127.0.0.1 --port 3306 -u root -pfrappe -e "SET GLOBAL collation_server = 'utf8mb4_unicode_ci'";
bench get-app insights "${GITHUB_WORKSPACE}" --skip-assets
bench -v setup requirements
cd ./frappe-bench || exit

echo "Setting Up Site..."

bench new-site --db-root-password frappe --admin-password frappe frappe-insights
bench --site frappe-insights add-to-hosts
bench --site frappe-insights install-app insights
bench build
cp "${GITHUB_WORKSPACE}/.github/helper/mariadb.json" ~/frappe-bench/sites/frappe-insights/site_config.json

echo "Setting Up Procfile..."

sed -i 's/^watch:/# watch:/g' Procfile
sed -i 's/^schedule:/# schedule:/g' Procfile
sed -i 's/^web: bench serve/web: bench serve --with-coverage/g' Procfile

echo "Starting Bench..."

bench start &> bench_start.log &
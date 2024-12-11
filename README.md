<div align="center" markdown="1">

<img src=".github/new-logo.svg" alt="Frappe Insights logo" width="100"/>
<h1>Frappe Insights</h1>

**Open Source Business Intelligence Tool**

![GitHub release (latest by date)](https://img.shields.io/github/v/release/frappe/insights)
[![codecov](https://codecov.io/github/frappe/insights/branch/develop/graph/badge.svg?token=8ZXHCY4G9U)](https://codecov.io/github/frappe/insights)

</div>


<div align="center">
	<img src=".github/hero-image.png?v=5" alt="Hero Image" width="72%" />
</div>
<br />
<div align="center">
    <a href="https://insightsdemo.frappe.cloud">Live Demo</a>
    -
    <a href="https://frappe.io/insights">Website</a>
    -
    <a href="https://docs.frappe.io/insights">Documentation</a>
</div>

## Frappe Insights
Insights is a 100% open-source BI tool designed to make data analysis and reporting more accessible to technical as well as non-technical users.

<details>
<summary>Screenshots</summary>

![Query Builder](.github/query-builder.png)
![Query Builder](.github/join-editor.png)
![Chart Builder](.github/chart-builder.png)
</details>

## Motivation
Building custom apps or creating structured data has been very easy with Frappe Framework. However, extracting information from these apps was not a very good experience. Users needed to know how to write SQL queries to create reports to gain valuable information from the data. So I wanted to improve the experience of building these reports and dashboards for everyone in our team.

## Key Features

- **Connect Multiple Sources**: You can integrate data from multiple databases, files and spreadsheets. Getting all your data into one place helps you analyse interconnected data.

- **Query Builder**: Frappe Insights a user-friendly query builder interface that allows users to create queries without any SQL knowledge. The interface provides a step-by-step approach for building queries, empowering users to easily select tables, add joins, apply filters, perform calculations, and more.

- **Visualizations and Dashboards**: You can visualize the query results using a variety of charts and graphs. Frappe Insights also suggests the best chart for a given result set. You can create dashboards using a drag-and-drop interface and add filters on the dashboard to apply to the charts.

- **Database Support**: Frappe Insights currently supports MySQL, PostgreSQL, DuckDB, and BigQuery databases. More database integrations are planned for the future.


## Under the Hood

- [**Frappe Framework**](https://github.com/frappe/frappe): A full-stack web application framework written in Python and Javascript. The framework provides a robust foundation for building web applications, including a database abstraction layer, user authentication, and a REST API.

- [**Frappe UI**](https://github.com/frappe/frappe-ui): A Vue-based UI library, to provide a modern user interface. The Frappe UI library provides a variety of components that can be used to build single-page applications on top of the Frappe Framework.

- [**Ibis**](https://github.com/ibis-project/ibis): A Python library to interact with SQL databases using a high-level API. Ibis provides a unified interface to interact with 20+ databases, allowing Frappe Insights to support multiple database backends.

- [**eCharts**](https://github.com/apache/echarts): A powerful charting library, to render charts and graphs. eCharts provides a variety of chart types and customization options, allowing Frappe Insights to provide a rich and interactive data visualization experience.


## Production Setup

### Managed Hosting

You can try [Frappe Cloud](https://frappecloud.com), a simple, user-friendly and sophisticated [open-source](https://github.com/frappe/press) platform to host Frappe applications with peace of mind.

It takes care of installation, setup, upgrades, monitoring, maintenance and support of your Frappe deployments. It is a fully featured developer platform with an ability to manage and control multiple Frappe deployments.

<div>
    <a href="https://frappecloud.com/insights/signup" target="_blank">
        <picture>
            <source media="(prefers-color-scheme: dark)" srcset="https://frappe.io/files/try-on-fc-white.png">
            <img src="https://frappe.io/files/try-on-fc-black.png" alt="Try on Frappe Cloud" height="28" />
        </picture>
    </a>
</div>

### Self Hosting

Follow these steps to set up Frappe Insights in production:

**Step 1**: Download the easy install script

```bash
wget https://frappe.io/easy-install.py
```

**Step 2**: Run the deployment command

```bash
python3 ./easy-install.py deploy \
    --project=insights_prod_setup \
    --email=your_email.example.com \
    --image=ghcr.io/frappe/insights \
    --version=stable \
    --app=insights \
    --sitename subdomain.domain.tld
```

Replace the following parameters with your values:
- `your_email.example.com`: Your email address
- `subdomain.domain.tld`: Your domain name where Insights will be hosted

The script will set up a production-ready instance of Frappe Insights with all the necessary configurations in about 5 minutes.

## Development Setup

### Docker

You need Docker, docker-compose and git setup on your machine. Refer [Docker documentation](https://docs.docker.com/). After that, follow below steps:

**Step 1**: Setup folder and download the required files

    mkdir frappe-insights
    cd frappe-insights

    # Download the docker-compose file
    wget -O docker-compose.yml https://raw.githubusercontent.com/frappe/insights/develop/docker/docker-compose.yml

    # Download the setup script
    wget -O init.sh https://raw.githubusercontent.com/frappe/insights/develop/docker/init.sh

**Step 2**: Run the container and daemonize it

    docker compose up -d

**Step 3**: The site [http://insights.localhost:8000/insights](http://insights.localhost:8000/insights) should now be available. The default credentials are:
- Username: Administrator
- Password: admin

### Local

To setup the repository locally follow the steps mentioned below:

1. Setup bench by following the [Installation Steps](https://frappeframework.com/docs/user/en/installation) and start the server
    ```
    bench start
    ```

2. In a separate terminal window, run the following commands:
    ```
    # Create a new site
    bench new-site insights.test

    # Map your site to localhost
    bench --site insights.test add-to-hosts
    ```

3. Get the Insights app and install it
    ```
    # Get the Insights app
    bench get-app https://github.com/frappe/insights

    # Install the app
    bench --site insights.test install-app insights
    ```

4. Open the URL `http://insights.test:8000/insights` in your browser, you should see the app running


### Frontend Development Setup

The Insights frontend is a Vue.js application located in the `frontend/src2` directory. Follow these steps to set up the frontend development environment:

1. Navigate to the Insights app directory:
    ```bash
    cd apps/insights
    ```

2. Install dependencies:
    ```bash
    yarn install
    ```

3. Add the following line in your site's `site_config.json` file
    ```json
    "ignore_csrf": 1
    ```

4. Start the development server:
    ```bash
    yarn dev
    ```

5. Access the development site:
   - Open `http://insights.localhost:8080/insights` in your browser
   - Any changes to files in `frontend/src2` will automatically reload in the browser


## Learn and connect

- [Telegram Public Group](https://t.me/frappeinsights)
- [Discuss Forum](https://discuss.frappe.io/c/insights/74)
- [Documentation](https://docs.frappe.io/insights)
- [YouTube](https://www.youtube.com/@frappetech)

<h2></h2>
<div align="center" style="padding-top: 0.75rem;">
	<a href="https://frappe.io" target="_blank">
		<picture>
			<source media="(prefers-color-scheme: dark)" srcset="https://frappe.io/files/Frappe-white.png">
			<img src="https://frappe.io/files/Frappe-black.png" alt="Frappe Technologies" height="28"/>
		</picture>
	</a>
</div>

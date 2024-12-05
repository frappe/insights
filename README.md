<div align="center" markdown="1">

<img src=".github/new-logo.svg" alt="Frappe Insights logo" width="100"/>
<h1>Frappe Insights</h1>

**Open Source Business Intelligence Tool**

![GitHub issues](https://img.shields.io/github/issues/frappe/insights)
![GitHub license](https://img.shields.io/github/license/frappe/insights)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/frappe/insights)
[![codecov](https://codecov.io/github/frappe/insights/branch/develop/graph/badge.svg?token=8ZXHCY4G9U)](https://codecov.io/github/frappe/insights)
[![unittests](https://github.com/frappe/insights/actions/workflows/server-tests.yml/badge.svg)](https://github.com/frappe/insights/actions/workflows/server-tests.yml)

</div>


<div align="center" style="padding-top: 1rem; padding-bottom: 1rem; display: flex; justify-content:center;">
	<img src=".github/hero-image.png?v=3" alt="Hero Image" width="72%" />
</div>

<div align="center" style="padding-top: 1rem; padding-bottom: 1rem; display: flex; justify-content:center;">
	<a href="https://insightsdemo.frappe.cloud">Live Demo</a>
	-
	<a href="https://frappe.io/insights">Website</a>
	-
	<a href="https://docs.frappe.io/insights">Documentation</a>
</div>

## Frappe Insights
Insights is a 100% open-source BI tool designed to make data analysis and reporting more accessible to technical as well as non-technical users.


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
		<img src=".github/try-on-fc.svg" alt="Try on Frappe Cloud" />
	</a>
</div>

### Self Hosting

Follow these steps to set up Frappe Insights in production:

**Step 1**: Download the easy install script

```bash
wget https://frappe.fyi/easy-install.py
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

> username: administrator <br/> password: admin

### Local

To setup the repository locally follow the steps mentioned below:

1. Install bench and setup a `frappe-bench` directory by following the [Installation Steps](https://frappeframework.com/docs/user/en/installation)
1. Start the server by running `bench start`
1. In a separate terminal window, create a new site by running `bench new-site insights.test`
1. Map your site to localhost with the command `bench --site insights.test add-to-hosts`
1. Get the Insights app. Run `bench get-app https://github.com/frappe/insights`
1. Run `bench --site insights.test install-app insights`.
1. Now open the URL `http://insights.test:8000/insights` in your browser, you should see the app running

## Learning and community

- [Telegram Public Group](https://t.me/frappeinsights)
- [Discuss Forum](https://discuss.frappe.io/c/insights/74)
- [Documentation](https://docs.frappe.io/insights)
- [YouTube](https://frappe.io)


<h2>&nbsp;</h2>

<div align="center">
<img src=".github/frappe-logo.svg" alt="Frappe Technologies" width="80"/>
</div>


<div align="center" markdown="1">

<img src=".github/new-logo.svg" alt="Frappe Insights logo" width="124"/>
<h1>Frappe Insights</h1>

**Simple. Crafted. Powerful. Data Analysis.**

![GitHub issues](https://img.shields.io/github/issues/frappe/insights)
![GitHub license](https://img.shields.io/github/license/frappe/insights)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/frappe/insights)
[![codecov](https://codecov.io/github/frappe/insights/branch/develop/graph/badge.svg?token=8ZXHCY4G9U)](https://codecov.io/github/frappe/insights)
[![unittests](https://github.com/frappe/insights/actions/workflows/server-tests.yml/badge.svg)](https://github.com/frappe/insights/actions/workflows/server-tests.yml)

</div>

<div align="center" style="max-height: 40px;">
	<a href="https://frappecloud.com/insights/signup">
		<img src="https://github.com/frappe/hrms/blob/develop/.github/try-on-f-cloud-button.svg" height="40">
	</a>
</div>

<div align="center" style="padding-top: 1rem; padding-bottom: 1rem; display: flex; justify-content:center;">
	<img src=".github/hero-image.png?v=3" alt="Hero Image" width="72%" />
</div>

<div align="center" style="padding-top: 1rem; padding-bottom: 1rem; display: flex; justify-content:center;">
	<a href="https://insightsdemo.frappe.cloud">Live Demo</a>
	-
	<a href="https://docs.frappeinsights.com">Documentation</a>
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


## Installation

### Managed Hosting

Get started with your personal or business site with a few clicks on [Frappe Cloud](https://frappecloud.com/insights/signup).

### Docker (Recommended)

You need Docker, docker-compose and git setup on your machine. Refer [Docker documentation](https://docs.docker.com/). After that, follow below steps:

**Step 1**: Setup folder and download the required files

    mkdir frappe-insights
    cd frappe-insights

**Step 2**: Download the required files

Docker Compose File:

    wget -O docker-compose.yml https://raw.githubusercontent.com/frappe/insights/develop/docker/docker-compose.yml

Frappe Insights bench setup script

    wget -O init.sh https://raw.githubusercontent.com/frappe/insights/develop/docker/init.sh

**Step 3**: Run the container and daemonize it

    docker compose up -d

**Step 4**: The site [http://insights.localhost:8000/insights](http://insights.localhost:8000/insights) should now be available. The default credentials are:

> username: administrator
> password: admin

### Local

To setup the repository locally follow the steps mentioned below:

1. Install bench and setup a `frappe-bench` directory by following the [Installation Steps](https://frappeframework.com/docs/user/en/installation)
1. Start the server by running `bench start`
1. In a separate terminal window, create a new site by running `bench new-site insights.test`
1. Map your site to localhost with the command `bench --site insights.test add-to-hosts`
1. Get the Insights app. Run `bench get-app https://github.com/frappe/insights`
1. Run `bench --site insights.test install-app insights`.
1. Now open the URL `http://insights.test:8000/insights` in your browser, you should see the app running

---
## Need help?

Join our [telegram group](https://t.me/frappeinsights) for instant help.

---

## License

[GNU Affero General Public License v3.0](license.txt)

<div align="center" markdown="1">

<img src=".github/logo.png" alt="Frappe Insights logo" width="384"/>

**Free and Open Source Data Analytics Tool for your Frappe Apps**

[![codecov](https://codecov.io/github/frappe/insights/branch/develop/graph/badge.svg?token=8ZXHCY4G9U)](https://codecov.io/github/frappe/insights)
[![unittest](https://github.com/frappe/insights/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/frappe/insights/actions/workflows/ci.yml)

</div>

<div align="center" style="padding-top: 1rem; padding-bottom: 1rem; display: flex; justify-content:center;">
	<img src=".github/hero-image.png" alt="Hero Image" width="72%" />
</div>

<div align="center" style="padding-top: 1rem; padding-bottom: 1rem; display: flex; justify-content:center;">
	<a href=".github/preview.gif">Preview</a>
	-
	<a href="https://frappeinsights.frappe.cloud/docs">Documentation</a>
</div>

## Features

- **Multiple Data Sources** - Connect to multiple data sources and query them at one place.
- **Complex Queries** - Write complex queries get the results in a tabular format.
- **Visualize Data** - Visualize your data in the form of charts.
- **Dashboards** - Create dashboards to automate tracking of important metrics.

## Installation
### Docker
You need Docker, docker-compose and git setup on your machine. Refer [Docker documentation](https://docs.docker.com/). After that, run the following commands:

```
git clone https://github.com/frappe/insights
cd insights/docker
docker-compose up
```

Wait for sometime until the setup script creates a site. After that you can
Open the URL `http://insights.test:8000/insights` in your browser, you should see the app running
should show up.

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
## Contributions and Community

There are many ways you can contribute even if you don't code:

1. You can start by giving a star to this repository!
1. If you find any issues, even if it is a typo, you can [raise an issue](https://github.com/frappe/insights/issues/new) to inform us.
1. You can join our [telegram group](https://t.me/frappeinsights) and share your thoughts.

---

## License

[GNU Affero General Public License v3.0](license.txt)

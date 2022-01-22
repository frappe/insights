from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in frappe_analytics/__init__.py
from frappe_analytics import __version__ as version

setup(
	name="frappe_analytics",
	version=version,
	description="Powerful Reporting Tool",
	author="Frappe Technologies Pvt. Ltd.",
	author_email="hello@frappe.io",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)

from setuptools import find_packages, setup

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in insights/__init__.py
from insights import __version__ as version

setup(
    name="insights",
    version=version,
    description="Powerful Reporting Tool for Frappe Apps",
    author="Frappe Technologies Pvt. Ltd.",
    author_email="hello@frappe.io",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)

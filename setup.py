
from setuptools import setup, find_packages

setup(
    name="skoolhud",
    version="0.1.0",
    description="HUD für Skool Communities",
    author="Niklas Schröer",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "typer>=0.9.0",
        "sqlalchemy>=2.0.0",
        "pydantic>=2.0.0",
        "python-dateutil>=2.8.2",
        "orjson>=3.8.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=4.9.0",
    ],
    entry_points={
        "console_scripts": [
            "skoolhud=skoolhud.cli:app",
        ],
    },
    python_requires=">=3.10",
)


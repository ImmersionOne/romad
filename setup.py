from setuptools import setup, find_packages

setup(
    name="romad",
    version="0.4.0",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "romad=romad.cli:main",
        ],
    },
    python_requires=">=3.8",
)

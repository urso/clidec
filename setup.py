from setuptools import setup, find_packages

with open("README.md", "r") as f:
    long_description = f.read()

setup(
    name="clidec",
    version="0.0.1",
    author="Steffen Siering",
    description="Build command line tools with sub-commands using decorators.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/urso/clidec",
    packages=find_packages(),
    install_requires=[],
)

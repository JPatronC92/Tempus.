from setuptools import setup, find_packages

setup(
    name="tempus-sdk",
    version="0.1.0",
    description="Official Python Client for the Tempus Decision Database",
    author="Tempus DDB",
    packages=find_packages(),
    install_requires=[], # Zero dependencies out of the box using built-in urllib
    python_requires=">=3.8",
)

from setuptools import setup, find_packages

with open("README.md", "r") as readme_file:
    readme = readme_file.read()

requirements = []

setup(
    name="supercfg",
    version="0.0.3",
    author="Igor Tavčar",
    author_email="igor.tavcar@gmail.com",
    description="A package to support INI conf language with support of int, float, bool, str, arrays, dicts, regex, "
                "field references and templating",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/IgorTavcar/supercfg",
    packages=find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
)

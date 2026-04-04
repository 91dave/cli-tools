#!/usr/bin/env python3
"""setup.py for cli-anything-icepanel

Install with: pip install -e .
"""

from setuptools import setup, find_namespace_packages

setup(
    name="cli-anything-icepanel",
    version="1.0.0",
    author="cli-anything contributors",
    description="CLI harness for IcePanel — architecture visualization via IcePanel REST API. Requires: IcePanel account + API key",
    long_description=open("cli_anything/icepanel/README.md", "r", encoding="utf-8").read()
    if __import__("os").path.exists("cli_anything/icepanel/README.md")
    else "CLI harness for IcePanel architecture visualization.",
    long_description_content_type="text/markdown",
    url="https://github.com/91dave/cli-tools",
    packages=find_namespace_packages(include=["cli_anything.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.10",
    install_requires=[
        "click>=8.0.0",
        "requests>=2.28.0",
        "prompt-toolkit>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cli-anything-icepanel=cli_anything.icepanel.icepanel_cli:main",
        ],
    },
    package_data={
        "cli_anything.icepanel": ["skills/*.md"],
    },
    include_package_data=True,
    zip_safe=False,
)

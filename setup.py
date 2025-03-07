from setuptools import setup, find_packages

try:
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()
except FileNotFoundError:
    long_description = ""

setup(
    name="rango-framework",
    version="0.1.0",
    author="Reshad",
    author_email="your.email@example.com",
    description="A lightweight Python web framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/rango",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'rango': [
            'templates/*',
            'templates/app/*',
            'templates/static/*',
            'templates/templates/*'
        ],
    },
    install_requires=[
        'aiohttp>=3.8.0',
        'click>=8.0.0',
        'gunicorn>=20.1.0',
        'python-dotenv>=0.19.0',
        'pytest>=6.0.0',
    ],
    entry_points={
        'console_scripts': [
            'rango=rango.cli:main',
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    python_requires=">=3.7",
) 
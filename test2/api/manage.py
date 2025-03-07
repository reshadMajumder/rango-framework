#!/usr/bin/env python
import click
import os
import sys
from app import app
from app.models import init_db

@click.group()
def cli():
    """Rango management script"""
    pass

@cli.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload/--no-reload', default=True, help='Enable auto-reload')
def runserver(host, port, reload):
    """Run the development server"""
    app.run(host=host, port=port, production=not reload)

@cli.command()
def shell():
    """Run a Python shell with the app context"""
    import code
    code.interact(local=locals())

@cli.command()
def initdb():
    """Initialize the database"""
    init_db()
    click.echo("Database initialized successfully!")

@cli.command()
def test():
    """Run the test suite"""
    import pytest
    sys.exit(pytest.main(['tests']))

if __name__ == '__main__':
    cli() 
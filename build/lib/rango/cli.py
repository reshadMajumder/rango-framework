import click
import os
import shutil
from pathlib import Path
import pkg_resources
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_template_dir():
    """Get the template directory with fallback options"""
    try:
        template_dir = pkg_resources.resource_filename('rango', 'templates')
        logger.debug(f"Template directory from pkg_resources: {template_dir}")
        if os.path.exists(template_dir):
            return template_dir
    except Exception as e:
        logger.warning(f"Error getting template dir from pkg_resources: {e}")

    # Fallback to direct path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(current_dir, 'templates')
    logger.debug(f"Fallback template directory: {template_dir}")
    return template_dir

TEMPLATE_DIR = get_template_dir()
logger.debug(f"Final template directory: {TEMPLATE_DIR}")
logger.debug(f"Python path: {sys.path}")

@click.group()
def cli():
    """Rango - A lightweight Python web framework"""
    pass

@cli.command()
@click.argument('project_name')
def startproject(project_name):
    """Create a new Rango project"""
    logger.debug(f"Starting project creation: {project_name}")
    logger.debug(f"Current working directory: {os.getcwd()}")
    
    try:
        # Create project directory
        project_dir = Path(project_name)
        logger.debug(f"Creating project directory: {project_dir.absolute()}")
        
        if project_dir.exists():
            click.echo(f"Error: Directory '{project_name}' already exists", err=True)
            return

        # Create directories
        project_dir.mkdir()
        (project_dir / 'app').mkdir()
        (project_dir / 'static').mkdir()
        (project_dir / 'templates').mkdir()
        (project_dir / 'tests').mkdir()
        
        # Copy template files
        template_files = {
            'manage.py': project_dir / 'manage.py',
            'requirements.txt': project_dir / 'requirements.txt',
            'app/__init__.py': project_dir / 'app' / '__init__.py',
            'app/routes.py': project_dir / 'app' / 'routes.py',
            'app/models.py': project_dir / 'app' / 'models.py',
            'app/settings.py': project_dir / 'app' / 'settings.py',
        }

        logger.debug(f"Template directory contents: {os.listdir(TEMPLATE_DIR)}")
        
        for template, dest in template_files.items():
            template_path = Path(TEMPLATE_DIR) / template
            logger.debug(f"Copying {template_path} to {dest}")
            if template_path.exists():
                shutil.copy2(template_path, dest)
            else:
                logger.warning(f"Template not found: {template_path}")
                dest.touch()

        # Make manage.py executable
        os.chmod(project_dir / 'manage.py', 0o755)

        click.echo(f"""
✨ Project '{project_name}' created successfully!

To get started:
   cd {project_name}
   pip install -r requirements.txt
   python manage.py runserver
""")
    except Exception as e:
        logger.exception("Error creating project")
        click.echo(f"Error: {str(e)}", err=True)
        if project_dir.exists():
            shutil.rmtree(project_dir)

@cli.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload/--no-reload', default=True, help='Enable auto-reload')
def runserver(host, port, reload):
    """Run the development server"""
    try:
        from .server import run_server
        run_server(host=host, port=port, reload=reload)
    except ImportError as e:
        click.echo(f"Error: Cannot find manage.py. Are you in the project directory? ({str(e)})", err=True)

def main():
    cli()

if __name__ == '__main__':
    main() 
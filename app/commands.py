import click
from flask.cli import AppGroup
from app import db
from app.database.models import Admin

# Create a CLI group so commands are namespaced under 'flask admin ...'
admin_cli = AppGroup('admin', help='Admin management commands.')

@admin_cli.command('create')
@click.option('--username', prompt=True, help='Username for the admin.')
@click.option('--email', prompt=True, help='Email address for the admin.')
@click.option(
    '--password',
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help='Password for the admin.'
)
def create_admin(username, email, password):
    """Create a new admin user from the terminal."""
    # Check if username or email already exists
    if Admin.query.filter_by(username=username).first():
        click.echo(click.style(f"Error: Username '{username}' already exists.", fg="red"))
        return

    if Admin.query.filter_by(email=email).first():
        click.echo(click.style(f"Error: Email '{email}' already exists.", fg="red"))
        return

    # Instantiate and set hashed password
    new_admin = Admin(username=username, email=email)
    new_admin.set_password(password)

    db.session.add(new_admin)
    db.session.commit()

    click.echo(click.style(f"Success! Admin '{username}' created successfully.", fg="green"))
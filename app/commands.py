"""
app/commands.py
Flask CLI commands for managing administrators and seeding RBAC roles.
"""
import click
from flask.cli import AppGroup
from app.extensions import db
from app.database.models import Admin
from app.auth.rbac import ALL_ADMIN_ROLES, ROLE_SUPER_ADMIN, normalize_role

# Create a CLI group so commands are namespaced under 'flask admin ...'
admin_cli = AppGroup('admin', help='Admin management and RBAC commands.')


@admin_cli.command('create')
@click.option('--username', prompt=True, help='Username for the admin.')
@click.option('--email', prompt=True, help='Email address for the admin.')
@click.option('--name', default='Administrator', help='Full name of the admin.')
@click.option(
    '--role',
    default=ROLE_SUPER_ADMIN,
    type=click.Choice(ALL_ADMIN_ROLES, case_sensitive=False),
    help='Role assigned to the admin.'
)
@click.option('--department', default='', help='Department (optional).')
@click.option(
    '--password',
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help='Password for the admin.'
)
def create_admin(username, email, name, role, department, password):
    """Create a new admin user with a specified RBAC role from the terminal."""
    norm_role = normalize_role(role)

    # Check if username or email already exists in SQLite
    if Admin.query.filter_by(username=username).first():
        click.echo(click.style(f"Error: Username '{username}' already exists.", fg="red"))
        return

    if Admin.query.filter_by(email=email.lower()).first():
        click.echo(click.style(f"Error: Email '{email}' already exists.", fg="red"))
        return

    # Instantiate and set hashed password
    new_admin = Admin(
        username=username,
        email=email.lower(),
        name=name,
        role=norm_role,
        department=department,
        is_active=True
    )
    new_admin.set_password(password)

    db.session.add(new_admin)
    db.session.commit()

    # Also sync to MongoDB if connected
    try:
        from app.database.mongo_models import MongoAdmin
        from app.database.mongodb import is_mongodb_connected
        if is_mongodb_connected():
            MongoAdmin.save_or_update({
                "username": username,
                "email": email.lower(),
                "name": name,
                "role": norm_role,
                "department": department,
                "is_active": True,
                "password": password
            })
    except Exception:
        pass

    click.echo(click.style(f"Success! Admin '{username}' [{norm_role}] created successfully.", fg="green"))


@admin_cli.command('seed')
def seed_admins_cmd():
    """Seeds all default RBAC admin accounts into SQLite and MongoDB."""
    from app.database.admin_seed import seed_admin_accounts
    stats = seed_admin_accounts()
    click.echo(click.style(f"Admin seeding complete: {stats}", fg="green"))


@admin_cli.command('list')
def list_admins_cmd():
    """List all registered administrators and their roles."""
    admins = Admin.query.order_by(Admin.id.asc()).all()
    if not admins:
        click.echo("No administrators found in database.")
        return

    click.echo("\n{:<6} {:<18} {:<28} {:<22} {:<8}".format("ID", "Username", "Email", "Role", "Active"))
    click.echo("-" * 86)
    for a in admins:
        click.echo("{:<6} {:<18} {:<28} {:<22} {:<8}".format(
            a.id, a.username, a.email, a.role, "Yes" if a.is_active else "No"
        ))
    click.echo("")
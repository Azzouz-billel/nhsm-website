"""Change a user's role from the command line (the only path to admin).

    python manage.py promote_user <username> admin
    python manage.py promote_user <username> approver
    python manage.py promote_user <username> student
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import Role


class Command(BaseCommand):
    help = "Set a user's role (student | approver | admin)."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("role", choices=[r.value for r in Role])

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist:
            raise CommandError(f"No user named '{options['username']}'.")

        user.role = options["role"]
        user.save(update_fields=["role"])
        self.stdout.write(
            self.style.SUCCESS(f"{user.username} is now a {user.get_role_display()}.")
        )

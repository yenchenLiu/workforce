import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from assignments.models import Position, Employee, Task, Assignment


class Command(BaseCommand):
    help = "Load demo seed data from JSON files in seed_data/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Delete existing data before loading.",
        )
        parser.add_argument(
            "--dir",
            default="seed_data",
            help="Directory containing JSON files (default: seed_data).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        base_dir = Path(options["dir"]).resolve()

        # 1. optional clean
        if options["truncate"]:
            self.stdout.write("Deleting existing records…")
            Assignment.objects.all().delete()
            Task.objects.all().delete()
            Employee.objects.all().delete()
            Position.objects.all().delete()

        # 2. load json helpers
        def load_json(name):
            path = base_dir / f"{name}.json"
            if not path.exists():
                raise CommandError(f"{path} not found")
            with open(path) as f:
                return json.load(f)

        positions = load_json("positions")
        employees = load_json("workers")
        tasks     = load_json("tasks")
        assigns   = load_json("assignments")

        # 3. create records (bulk for speed)
        Position.objects.bulk_create(
            [Position(id=p["id"], name=p["name"]) for p in positions],
            ignore_conflicts=True,
        )
        Employee.objects.bulk_create(
            [
                Employee(
                    id=e["id"],
                    name=e["name"],
                    position_id=e.get("position_id"),
                )
                for e in employees
            ],
            ignore_conflicts=True,
        )
        Task.objects.bulk_create(
            [
                Task(
                    id=t["id"],
                    position_id=t.get("position_id"),
                    duration=t["duration"],
                    date=t["date"],
                )
                for t in tasks
            ],
            ignore_conflicts=True,
        )
        Assignment.objects.bulk_create(
            [
                Assignment(
                    task_id=a["task_id"],
                    worker_id=a["worker_id"],
                    work_date=next(
                        t["date"] for t in tasks if t["id"] == a["task_id"]
                    ),
                    hours=next(
                        t["duration"] for t in tasks if t["id"] == a["task_id"]
                    ),
                )
                for a in assigns
            ],
            ignore_conflicts=True,
        )

        self.stdout.write(self.style.SUCCESS("✅  Seed data loaded successfully"))
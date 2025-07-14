from datetime import date, timedelta
from typing import DefaultDict
from collections import defaultdict
from .models import Assignment, Task
from .schemas import PositionHoursData, WorkerHoursData, AggregatedScheduleData


class WorkforceScheduleService:
    """Service class for workforce schedule operations."""

    @staticmethod
    def get_assignments_in_range(start_date: date, end_date: date):
        """Get all assignments within the specified date range."""
        return Assignment.objects.filter(
            work_date__gte=start_date,
            work_date__lte=end_date
        ).select_related('worker', 'task', 'task__position')

    @staticmethod
    def get_unassigned_tasks_in_range(start_date: date, end_date: date):
        """Get all tasks within the date range that don't have assignments."""
        assigned_task_ids = Assignment.objects.filter(
            work_date__gte=start_date,
            work_date__lte=end_date
        ).values_list('task_id', flat=True)

        return Task.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).exclude(
            id__in=assigned_task_ids
        ).select_related('position')

    @staticmethod
    def generate_date_columns(start_date: date, end_date: date) -> list[str]:
        """Generate list of date strings for table columns."""
        date_columns = []
        current_date = start_date
        while current_date <= end_date:
            date_columns.append(current_date.strftime('%d %b'))
            current_date += timedelta(days=1)
        return date_columns

    @staticmethod
    def aggregate_schedule_data(assignments, unassigned_tasks, date_columns: list[str]) -> AggregatedScheduleData:
        """Aggregate assignments and unassigned tasks into positions and workers data."""
        # Define constants
        UNASSIGNED_POSITION = "Unassigned"
        UNASSIGNED_TASKS = "Unassigned Tasks"

        # Nested mapping: position/worker -> {date_str -> hours}
        position_hours: DefaultDict[str, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))
        worker_hours: DefaultDict[str, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))
        workers_by_position = defaultdict(set)

        # Aggregate data from assignments
        for assignment in assignments:
            date_str = assignment.work_date.strftime('%d %b')

            # Determine position name - use "Unassigned" if no position
            if assignment.task.position:
                position_name = assignment.task.position.name
            else:
                position_name = UNASSIGNED_POSITION

            position_hours[position_name][date_str] += assignment.hours

            if assignment.worker:
                worker_name = assignment.worker.name
                worker_hours[worker_name][date_str] += assignment.hours
                workers_by_position[position_name].add(worker_name)

        # Aggregate unassigned tasks
        unassigned_tasks_by_position: DefaultDict[str, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))
        for task in unassigned_tasks:
            date_str = task.date.strftime('%d %b')

            if task.position:
                position_name = task.position.name
            else:
                position_name = UNASSIGNED_POSITION

            unassigned_tasks_by_position[position_name][date_str] += task.duration

        # Convert to schema objects
        positions = []
        workers_by_pos = {}

        # Process all positions (both assigned and unassigned)
        all_positions = set(position_hours.keys()) | set(unassigned_tasks_by_position.keys())

        for position_name in all_positions:
            # Fill missing dates with 0 for assigned hours
            assigned_daily_hours: dict[str, int] = position_hours.get(position_name, {})
            complete_hours = {date_col: assigned_daily_hours.get(date_col, 0) for date_col in date_columns}

            positions.append(PositionHoursData(
                name=position_name,
                daily_hours=complete_hours
            ))

            # Get workers for this position
            position_workers = []
            for worker_name in workers_by_position.get(position_name, set()):
                worker_daily_hours: dict[str, int] = worker_hours.get(worker_name, {})
                complete_worker_hours = {date_col: worker_daily_hours.get(date_col, 0) for date_col in date_columns}
                position_workers.append(WorkerHoursData(
                    name=worker_name,
                    daily_hours=complete_worker_hours
                ))

            # Add unassigned tasks row if there are any for this position
            unassigned_daily_hours: dict[str, int] = unassigned_tasks_by_position.get(position_name, {})
            if unassigned_daily_hours:
                complete_unassigned_hours = {date_col: unassigned_daily_hours.get(date_col, 0) for date_col in date_columns}
                position_workers.append(WorkerHoursData(
                    name=UNASSIGNED_TASKS,
                    daily_hours=complete_unassigned_hours
                ))

            workers_by_pos[position_name] = position_workers

        return AggregatedScheduleData(
            positions=positions,
            workers_by_position=workers_by_pos
        )

    @classmethod
    def get_workforce_schedule_data(cls, start_date: date, end_date: date) -> tuple[AggregatedScheduleData, list[str]]:
        """Main service method to get workforce schedule data."""
        # Get data from database
        assignments = cls.get_assignments_in_range(start_date, end_date)
        unassigned_tasks = cls.get_unassigned_tasks_in_range(start_date, end_date)
        date_columns = cls.generate_date_columns(start_date, end_date)

        # Aggregate and structure data
        schedule_data = cls.aggregate_schedule_data(assignments, unassigned_tasks, date_columns)

        return schedule_data, date_columns

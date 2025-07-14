from datetime import date, timedelta
from typing import DefaultDict
from inequality import gini  # type: ignore
from .models import Assignment, Task, Employee
from .schemas import (
    PositionHoursData, WorkerHoursData, AggregatedScheduleData,
    TaskAssignmentSchema, KPIMetricsSchema
)
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpBinary, PulpSolverError  # type: ignore
from collections import defaultdict


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

            position_name = assignment.task.position.name if assignment.task.position else UNASSIGNED_POSITION
            position_hours[position_name][date_str] += assignment.hours

            if assignment.worker:
                worker_name = assignment.worker.name
                worker_hours[worker_name][date_str] += assignment.hours
                workers_by_position[position_name].add(worker_name)

        # Aggregate unassigned tasks
        unassigned_tasks_by_position: DefaultDict[str, DefaultDict[str, int]] = defaultdict(lambda: defaultdict(int))
        for task in unassigned_tasks:
            date_str = task.date.strftime('%d %b')

            position_name = task.position.name if task.position else UNASSIGNED_POSITION
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


class TaskAssignmentService:
    """Service class for task assignment operations."""

    @staticmethod
    def assign_tasks_using_greedy(tasks, employees, max_hours_per_day=8):
        """
        Assign tasks to employees using greedy balanced approach.
        Groups by date and position, assigns to worker with least current load.
        """
        # Group tasks by date and position
        tasks_by_date_position = defaultdict(list)
        for task in tasks:
            position_name = task.position.name if task.position else "Unassigned"
            key = (task.date, position_name)
            tasks_by_date_position[key].append(task)

        # Group employees by position
        employees_by_position = defaultdict(list)
        for employee in employees:
            position_name = employee.position.name if employee.position else "Unassigned"
            employees_by_position[position_name].append(employee)

        # Track worker daily loads
        worker_daily_loads = defaultdict(lambda: defaultdict(int))
        assignments = []
        unassigned_tasks = []

        # Process each date-position group
        for (task_date, position_name), position_tasks in tasks_by_date_position.items():
            available_workers = employees_by_position.get(position_name, [])

            if not available_workers:
                # No workers for this position
                unassigned_tasks.extend(position_tasks)
                continue

            # Sort tasks by duration (descending) for better packing
            position_tasks.sort(key=lambda t: t.duration)

            for task in position_tasks:
                # Find worker with minimum load who can still take this task
                best_worker = None
                min_load = float('inf')

                for worker in available_workers:
                    current_load = worker_daily_loads[worker.id][task_date]
                    if current_load + task.duration <= max_hours_per_day:
                        if current_load < min_load:
                            min_load = current_load
                            best_worker = worker

                if best_worker:
                    # Assign task to best worker
                    worker_daily_loads[best_worker.id][task_date] += task.duration
                    assignments.append({
                        'task': task,
                        'worker': best_worker,
                        'work_date': task_date,
                        'hours': task.duration
                    })
                else:
                    # No available worker for this task
                    unassigned_tasks.append(task)

        return assignments, unassigned_tasks, worker_daily_loads


    @staticmethod
    def assign_tasks_using_lp(tasks, employees, max_hours_per_day=8):
        """Assign tasks using Linear Programming optimization via pulp."""

        task_lookup = {task.id: task for task in tasks}
        employee_lookup = {emp.id: emp for emp in employees}

        # Define LP problem
        problem = LpProblem("Task_Assignment", LpMaximize)

        # Create variables: x[task_id][emp_id] = 1 if assigned
        x = {}
        for task in tasks:
            task_pos = task.position.id if task.position else "Unassigned"
            for emp in employees:
                emp_pos = emp.position.id if emp.position else "Unassigned"
                if task_pos == emp_pos:
                    var_name = f"x_{task.id}_{emp.id}"
                    x[(task.id, emp.id)] = LpVariable(var_name, cat=LpBinary)

        # Objective: Maximize total assigned task duration
        problem += lpSum(x[t, e] * task_lookup[t].duration for (t, e) in x)

        # Constraint: Each task assigned to at most one employee
        for task in tasks:
            problem += lpSum(x.get((task.id, e.id), 0) for e in employees) <= 1

        # Constraint: Each employee cannot exceed max hours per day
        dates = sorted(set(task.date for task in tasks))
        for emp in employees:
            for d in dates:
                relevant_tasks = [task for task in tasks if task.date == d and (task.id, emp.id) in x]
                problem += lpSum(x[(t.id, emp.id)] * t.duration for t in relevant_tasks) <= max_hours_per_day

        try:
            problem.solve()
        except PulpSolverError as e:
            raise RuntimeError("Failed to solve LP problem") from e

        assignments = []
        unassigned_tasks = []
        worker_daily_loads = defaultdict(lambda: defaultdict(int))

        # Parse result
        assigned_task_ids = set()
        for (t_id, e_id), var in x.items():
            if var.value() == 1:
                task = task_lookup[t_id]
                emp = employee_lookup[e_id]
                assignments.append({
                    'task': task,
                    'worker': emp,
                    'work_date': task.date,
                    'hours': task.duration
                })
                worker_daily_loads[emp.id][task.date] += task.duration
                assigned_task_ids.add(t_id)

        for task in tasks:
            if task.id not in assigned_task_ids:
                unassigned_tasks.append(task)

        return assignments, unassigned_tasks, worker_daily_loads

    @staticmethod
    def calculate_kpi_metrics(assignments, unassigned_tasks,
                              worker_daily_loads, employees,
                              max_hours_per_day: int = 8):
        """Calculate KPI metrics for task assignment."""
        total_workers = len(employees)
        total_tasks = len(assignments) + len(unassigned_tasks)
        total_assigned_hours = sum(a['hours'] for a in assignments)
        unassigned_hours = sum(t.duration for t in unassigned_tasks)

        distinct_dates = {
            d for daily in worker_daily_loads.values() for d in daily.keys()
        }
        num_days = len(distinct_dates) or 1

        max_possible_hours = (total_workers * max_hours_per_day * num_days) or 1
        utilization_rate = total_assigned_hours / max_possible_hours

        max_worker_load = 0
        worker_loads = []
        for worker in employees:
            worker_max_daily = 0
            worker_total = 0
            for daily_load in worker_daily_loads[worker.id].values():
                worker_max_daily = max(worker_max_daily, daily_load)
                worker_total += daily_load
            max_worker_load = max(max_worker_load, worker_max_daily)
            worker_loads.append(worker_total)

        gini_coefficient = TaskAssignmentService._calculate_gini_coefficient(worker_loads)

        return KPIMetricsSchema(
            utilization_rate=round(utilization_rate, 3),
            max_worker_load=max_worker_load,
            unassigned_hours=unassigned_hours,
            gini_coefficient=round(gini_coefficient, 3),
            total_workers=total_workers,
            total_tasks=total_tasks,
            total_assigned_hours=total_assigned_hours
        )
    @staticmethod
    def _calculate_gini_coefficient(values):
        """Calculate Gini coefficient for a list of values."""
        if not values or len(values) == 1:
            return 0.0
        return gini.Gini(values).g

    @classmethod
    def create_task_assignments(cls, start_date: date, end_date: date, method: str = 'lp'):
        """
        Main service method to create task assignments.
        Fetches tasks and employees within date range and assigns them optimally.
        """
        # Get tasks in date range
        tasks = list(Task.objects.filter(
            date__gte=start_date,
            date__lte=end_date
        ).select_related('position'))

        # Get all employees
        employees = list(Employee.objects.all().select_related('position'))

        # Perform assignment
        if method == 'greedy':
            assignments, unassigned_tasks, worker_daily_loads = cls.assign_tasks_using_greedy(tasks, employees)
        else:
            # Default to LP method
            assignments, unassigned_tasks, worker_daily_loads = cls.assign_tasks_using_lp(tasks, employees)

        # Calculate KPIs
        kpi_metrics = cls.calculate_kpi_metrics(assignments, unassigned_tasks, worker_daily_loads, employees)

        # Convert assignments to schema format
        assignment_schemas = []
        for assignment in assignments:
            task = assignment['task']
            worker = assignment['worker']
            assignment_schemas.append(TaskAssignmentSchema(
                task_id=task.id,
                worker_id=worker.id,
                worker_name=worker.name,
                position_name=task.position.name if task.position else "Unassigned",
                work_date=assignment['work_date'].strftime('%Y-%m-%d'),
                hours=assignment['hours']
            ))

        # Create summary statistics
        summary = {
            'assigned_tasks': len(assignments),
            'unassigned_tasks': len(unassigned_tasks),
            'unassigned_task_ids': [task.id for task in unassigned_tasks],
            'total_positions': len(
                set(emp.position.name if emp.position else "Unassigned" for emp in employees)
            )
        }

        return assignment_schemas, kpi_metrics, summary

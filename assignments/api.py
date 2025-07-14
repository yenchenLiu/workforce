from ninja import NinjaAPI, Swagger
from datetime import date
from .services import WorkforceScheduleService, TaskAssignmentService
from .schemas import WorkforceScheduleRowSchema, WorkforceScheduleResponseSchema, TaskAssignmentResponseSchema

api = NinjaAPI(docs=Swagger(settings={"persistAuthorization": True}))

@api.get("/workforce-schedule", response=WorkforceScheduleResponseSchema)
def get_workforce_schedule(request, start_date: date | None = None, end_date: date | None = None):
    """
    Get workforce schedule data formatted for frontend table display.
    Returns positions and workers with their daily hour totals.
    """
    # Set default dates
    if not start_date:
        start_date = date.today()
    if not end_date:
        end_date = start_date

    # Get data using service
    schedule_data, date_columns = WorkforceScheduleService.get_workforce_schedule_data(start_date, end_date)

    # Build response data
    result_data = []

    for position in schedule_data.positions:
        # Add position row
        result_data.append(WorkforceScheduleRowSchema(
            name=position.name,
            type="position",
            daily_hours=position.daily_hours
        ))

        # Add worker rows for this position
        workers = schedule_data.workers_by_position.get(position.name, [])
        for worker in workers:
            result_data.append(WorkforceScheduleRowSchema(
                name=worker.name,
                type="worker",
                daily_hours=worker.daily_hours
            ))

    return WorkforceScheduleResponseSchema(
        data=result_data,
        date_columns=date_columns
    )

@api.post("/assign-tasks", response=TaskAssignmentResponseSchema)
def assign_tasks(request, start_date: date, end_date: date):
    """
    Assign tasks to workers using greedy balanced approach.
    Returns task assignments and KPI metrics.

    Strategy:
    - Groups tasks by date and position
    - Uses greedy algorithm to assign tasks to workers with least current load
    - Respects position matching and 8-hour daily capacity constraints

    KPIs returned:
    - utilization_rate: Total assigned hours / (workers × 8 hours)
    - max_worker_load: Highest daily load across all workers
    - unassigned_hours: Total hours of tasks that couldn't be assigned
    - gini_coefficient: Measures workload distribution equality (0 = perfectly equal)
    """
    # Get assignment data using service
    assignment_schemas, kpi_metrics, summary = TaskAssignmentService.create_task_assignments(start_date, end_date)

    return TaskAssignmentResponseSchema(
        assignments=assignment_schemas,
        kpi_metrics=kpi_metrics,
        summary=summary
    )

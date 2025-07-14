from ninja import Schema


class WorkforceScheduleRowSchema(Schema):
    """Single row in the workforce schedule table (position or worker)."""
    name: str
    type: str  # 'position' or 'worker'
    daily_hours: dict[str, int]  # key is date string, value is total hours


class WorkforceScheduleResponseSchema(Schema):
    """Complete response schema for workforce schedule endpoint."""
    data: list[WorkforceScheduleRowSchema]
    date_columns: list[str]


class PositionHoursData(Schema):
    """Position daily hours data."""
    name: str
    daily_hours: dict[str, int]


class WorkerHoursData(Schema):
    """Worker daily hours data."""
    name: str
    daily_hours: dict[str, int]


class AggregatedScheduleData(Schema):
    """Aggregated schedule data container."""
    positions: list[PositionHoursData]
    workers_by_position: dict[str, list[WorkerHoursData]]


class TaskAssignmentSchema(Schema):
    """Schema for individual task assignment."""
    task_id: int
    worker_id: int
    worker_name: str
    position_name: str
    work_date: str
    hours: int


class KPIMetricsSchema(Schema):
    """Schema for KPI metrics."""
    utilization_rate: float
    max_worker_load: int
    unassigned_hours: int
    gini_coefficient: float
    total_workers: int
    total_tasks: int
    total_assigned_hours: int


class TaskAssignmentResponseSchema(Schema):
    """Response schema for task assignment endpoint."""
    assignments: list[TaskAssignmentSchema]
    kpi_metrics: KPIMetricsSchema
    summary: dict[str, int | list[int]]  # Summary statistics

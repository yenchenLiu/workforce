from ninja import Schema
from typing import List, Dict


class WorkforceScheduleRowSchema(Schema):
    """Single row in the workforce schedule table (position or worker)."""
    name: str
    type: str  # 'position' or 'worker'
    daily_hours: Dict[str, int]  # key is date string, value is total hours


class WorkforceScheduleResponseSchema(Schema):
    """Complete response schema for workforce schedule endpoint."""
    data: List[WorkforceScheduleRowSchema]
    date_columns: List[str]


class PositionHoursData(Schema):
    """Position daily hours data."""
    name: str
    daily_hours: Dict[str, int]


class WorkerHoursData(Schema):
    """Worker daily hours data."""
    name: str
    daily_hours: Dict[str, int]


class AggregatedScheduleData(Schema):
    """Aggregated schedule data container."""
    positions: List[PositionHoursData]
    workers_by_position: Dict[str, List[WorkerHoursData]]


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
    assignments: List[TaskAssignmentSchema]
    kpi_metrics: KPIMetricsSchema
    summary: Dict[str, int | list[int]]  # Summary statistics

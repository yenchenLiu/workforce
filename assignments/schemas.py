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

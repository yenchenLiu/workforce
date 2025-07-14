from django.db import models

class Position(models.Model):
    id   = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)

class Employee(models.Model):
    id        = models.BigAutoField(primary_key=True)
    name      = models.CharField(max_length=100)
    position  = models.ForeignKey(
        Position,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="employees"
    )

class Task(models.Model):
    id         = models.BigAutoField(primary_key=True)
    position   = models.ForeignKey(
        Position,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="tasks"
    )
    duration   = models.PositiveSmallIntegerField()
    date       = models.DateField(db_index=True)

class Assignment(models.Model):
    id        = models.BigAutoField(primary_key=True)
    worker    = models.ForeignKey(
        Employee,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="assignments"
    )
    task      = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="assignments"
    )
    work_date = models.DateField()
    hours     = models.PositiveSmallIntegerField()

    class Meta:
        unique_together = ("worker", "task")
        indexes = [
            models.Index(fields=["work_date"]),
            models.Index(fields=["worker", "work_date"]),
            models.Index(fields=["task"]),
        ]

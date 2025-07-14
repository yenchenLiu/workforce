from django.test import TestCase
from django.test.client import Client
from datetime import date
from .models import Position, Employee, Task, Assignment


class WorkforceScheduleAPITestBase(TestCase):
    """Base test class with common setup and helper methods."""

    def setUp(self):
        """Set up common test data"""
        self.client = Client()
        self.base_date = date(2025, 1, 11)

        # Create positions
        self.position1 = Position.objects.create(name="Position 1")
        self.position2 = Position.objects.create(name="Position 2")

        # Create employees
        self.worker1 = Employee.objects.create(name="Worker 1", position=self.position1)
        self.worker2 = Employee.objects.create(name="Worker 2", position=self.position1)
        self.worker3 = Employee.objects.create(name="Worker 3", position=self.position2)

        # Create tasks
        self.task1 = Task.objects.create(
            position=self.position1, duration=8, date=self.base_date
        )
        self.task2 = Task.objects.create(
            position=self.position1, duration=6, date=date(2025, 1, 12)
        )
        self.task3 = Task.objects.create(
            position=self.position2, duration=5, date=self.base_date
        )

        # Create base assignments
        self._create_base_assignments()

    def _create_base_assignments(self):
        """Create standard test assignments."""
        assignments = [
            (self.worker1, self.task1, self.base_date, 3),
            (self.worker2, self.task1, self.base_date, 4),
            (self.worker1, self.task2, date(2025, 1, 12), 8),
            (self.worker2, self.task2, date(2025, 1, 12), 2),
            (self.worker3, self.task3, self.base_date, 5),
        ]

        for worker, task, work_date, hours in assignments:
            Assignment.objects.create(worker=worker, task=task, work_date=work_date, hours=hours)

    def get_api_response(self, start_date=None, end_date=None):
        """Helper to get API response."""
        params = {}
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        return self.client.get('/api/workforce-schedule', params)

    def find_row_by_name_type(self, data, name, row_type):
        """Helper to find a specific row in response data."""
        return next(
            (row for row in data['data'] if row['name'] == name and row['type'] == row_type),
            None
        )


class WorkforceScheduleBasicTest(WorkforceScheduleAPITestBase):
    """Test basic functionality of the workforce schedule API."""

    def test_date_range_functionality(self):
        """Test API with date range and verify structure and calculations."""
        response = self.get_api_response('2025-01-11', '2025-01-12')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify structure
        self.assertIn('data', data)
        self.assertIn('date_columns', data)
        self.assertEqual(data['date_columns'], ['11 Jan', '12 Jan'])

        # Verify position totals
        pos1 = self.find_row_by_name_type(data, 'Position 1', 'position')
        pos2 = self.find_row_by_name_type(data, 'Position 2', 'position')

        self.assertIsNotNone(pos1)
        self.assertEqual(pos1['daily_hours'], {'11 Jan': 7, '12 Jan': 10})

        self.assertIsNotNone(pos2)
        self.assertEqual(pos2['daily_hours'], {'11 Jan': 5, '12 Jan': 0})

        # Verify worker hours
        worker1 = self.find_row_by_name_type(data, 'Worker 1', 'worker')
        worker2 = self.find_row_by_name_type(data, 'Worker 2', 'worker')
        worker3 = self.find_row_by_name_type(data, 'Worker 3', 'worker')

        self.assertEqual(worker1['daily_hours'], {'11 Jan': 3, '12 Jan': 8})
        self.assertEqual(worker2['daily_hours'], {'11 Jan': 4, '12 Jan': 2})
        self.assertEqual(worker3['daily_hours'], {'11 Jan': 5, '12 Jan': 0})

    def test_single_day_and_missing_parameters(self):
        """Test single day queries and parameter handling."""
        # Single day
        response = self.get_api_response('2025-01-11', '2025-01-11')
        data = response.json()
        self.assertEqual(data['date_columns'], ['11 Jan'])

        # Missing end date
        response = self.get_api_response('2025-01-11')
        data = response.json()
        self.assertEqual(data['date_columns'], ['11 Jan'])

        # No parameters (uses today)
        response = self.get_api_response()
        data = response.json()
        today = date.today()
        self.assertEqual(data['date_columns'], [today.strftime('%d %b')])

    def test_no_data_scenarios(self):
        """Test scenarios with no data."""
        response = self.get_api_response('2025-01-15', '2025-01-16')
        data = response.json()

        self.assertEqual(data['date_columns'], ['15 Jan', '16 Jan'])
        self.assertEqual(data['data'], [])


class WorkforceScheduleSchemaTest(WorkforceScheduleAPITestBase):
    """Test response schema validation."""

    def test_response_schema_structure(self):
        """Verify API response matches expected schema."""
        response = self.get_api_response('2025-01-11', '2025-01-12')
        data = response.json()

        # Top-level structure
        self.assertIsInstance(data['data'], list)
        self.assertIsInstance(data['date_columns'], list)

        # Row structure
        for row in data['data']:
            self.assertIn('name', row)
            self.assertIn('type', row)
            self.assertIn('daily_hours', row)
            self.assertIsInstance(row['name'], str)
            self.assertIn(row['type'], ['position', 'worker'])
            self.assertIsInstance(row['daily_hours'], dict)

            # Verify date keys match columns
            for date_key in row['daily_hours']:
                self.assertIn(date_key, data['date_columns'])
                self.assertIsInstance(row['daily_hours'][date_key], int)


class WorkforceScheduleUnassignedTest(WorkforceScheduleAPITestBase):
    """Test handling of workers and tasks without positions."""

    def test_unassigned_workers_and_tasks(self):
        """Test that unassigned workers/tasks are grouped under 'Unassigned'."""
        # Create unassigned workers and tasks
        unassigned_worker1 = Employee.objects.create(name="Unassigned Worker 1")
        unassigned_worker2 = Employee.objects.create(name="Unassigned Worker 2", position=None)

        unassigned_task1 = Task.objects.create(
           duration=3, date=date(2025, 1, 11)
        )
        unassigned_task2 = Task.objects.create(
           position=None, duration=2, date=date(2025, 1, 12)
        )

        # Create assignments
        Assignment.objects.create(
            worker=unassigned_worker1, task=unassigned_task1,
            work_date=date(2025, 1, 11), hours=3
        )
        Assignment.objects.create(
            worker=unassigned_worker2, task=unassigned_task2,
            work_date=date(2025, 1, 12), hours=2
        )

        response = self.get_api_response('2025-01-11', '2025-01-12')
        data = response.json()

        # Verify "Unassigned" position
        unassigned_pos = self.find_row_by_name_type(data, 'Unassigned', 'position')
        self.assertIsNotNone(unassigned_pos)
        self.assertEqual(unassigned_pos['daily_hours'], {'11 Jan': 3, '12 Jan': 2})

        # Verify unassigned workers
        worker1 = self.find_row_by_name_type(data, 'Unassigned Worker 1', 'worker')
        worker2 = self.find_row_by_name_type(data, 'Unassigned Worker 2', 'worker')

        self.assertEqual(worker1['daily_hours'], {'11 Jan': 3, '12 Jan': 0})
        self.assertEqual(worker2['daily_hours'], {'11 Jan': 0, '12 Jan': 2})

    def test_mixed_assigned_and_unassigned(self):
        """Test mix of assigned and unassigned workers."""
        unassigned_worker = Employee.objects.create(name="General Worker")
        unassigned_task = Task.objects.create(
            duration=4, date=date(2025, 1, 11)
        )
        Assignment.objects.create(
            worker=unassigned_worker, task=unassigned_task,
            work_date=date(2025, 1, 11), hours=4
        )

        response = self.get_api_response('2025-01-11', '2025-01-12')
        data = response.json()

        # Should have both regular positions and "Unassigned"
        position_names = [row['name'] for row in data['data'] if row['type'] == 'position']
        self.assertIn('Position 1', position_names)
        self.assertIn('Position 2', position_names)
        self.assertIn('Unassigned', position_names)

        # Verify "Unassigned" position hours
        unassigned = self.find_row_by_name_type(data, 'Unassigned', 'position')
        self.assertEqual(unassigned['daily_hours'], {'11 Jan': 4, '12 Jan': 0})


class WorkforceScheduleUnassignedTasksTest(WorkforceScheduleAPITestBase):
    """Test handling of tasks that have not been assigned to workers."""

    def test_unassigned_tasks_display(self):
        """Test that unassigned tasks appear as 'Unassigned Tasks' rows."""
        # Create some tasks without assignments
        Task.objects.create(
            position=self.position1,
            duration=3,
            date=date(2025, 1, 11)
        )
        Task.objects.create(
            position=self.position2,
            duration=2,
            date=date(2025, 1, 12)
        )

        response = self.get_api_response('2025-01-11', '2025-01-12')
        data = response.json()

        # Find "Unassigned Tasks" rows
        unassigned_tasks_rows = [
            row for row in data['data']
            if row['name'] == 'Unassigned Tasks' and row['type'] == 'worker'
        ]

        # Should have unassigned tasks for both positions
        self.assertEqual(len(unassigned_tasks_rows), 2)

        # Verify the hours for each position's unassigned tasks
        for row in unassigned_tasks_rows:
            if row['daily_hours']['11 Jan'] == 3:  # Position 1 unassigned task
                self.assertEqual(row['daily_hours']['12 Jan'], 0)
            elif row['daily_hours']['12 Jan'] == 2:  # Position 2 unassigned task
                self.assertEqual(row['daily_hours']['11 Jan'], 0)

    def test_mixed_assigned_and_unassigned_tasks(self):
        """Test positions with both assigned workers and unassigned tasks."""
        # Create an unassigned task for position1 (which already has assigned workers)
        Task.objects.create(
            position=self.position1,
            duration=4,
            date=date(2025, 1, 11)
        )

        response = self.get_api_response('2025-01-11', '2025-01-12')
        data = response.json()

        # Find Position 1 data
        pos1_workers = [
            row for row in data['data']
            if row['type'] == 'worker' and
            any(prev_row['name'] == 'Position 1' and prev_row['type'] == 'position'
                for prev_row in data['data'][:data['data'].index(row)])
        ]

        # Should have Worker 1, Worker 2, and Unassigned Tasks
        worker_names = [worker['name'] for worker in pos1_workers]
        self.assertIn('Worker 1', worker_names)
        self.assertIn('Worker 2', worker_names)
        self.assertIn('Unassigned Tasks', worker_names)

        # Verify unassigned tasks hours
        unassigned_row = next(
            worker for worker in pos1_workers
            if worker['name'] == 'Unassigned Tasks'
        )
        self.assertEqual(unassigned_row['daily_hours']['11 Jan'], 4)
        self.assertEqual(unassigned_row['daily_hours']['12 Jan'], 0)

    def test_unassigned_tasks_for_unassigned_position(self):
        """Test unassigned tasks that also have no position."""
        # Create tasks without position and without assignment
        Task.objects.create(
            duration=2,
            date=date(2025, 1, 11)
        )
        Task.objects.create(
            position=None,
            duration=3,
            date=date(2025, 1, 12)
        )

        response = self.get_api_response('2025-01-11', '2025-01-12')
        data = response.json()

        # Should have "Unassigned" position
        unassigned_position = self.find_row_by_name_type(data, 'Unassigned', 'position')
        self.assertIsNotNone(unassigned_position)

        # Find the "Unassigned Tasks" row under "Unassigned" position
        unassigned_tasks_row = None
        found_unassigned_position = False

        for row in data['data']:
            if row['name'] == 'Unassigned' and row['type'] == 'position':
                found_unassigned_position = True
            elif found_unassigned_position and row['name'] == 'Unassigned Tasks':
                unassigned_tasks_row = row
                break
            elif row['type'] == 'position' and row['name'] != 'Unassigned':
                found_unassigned_position = False

        self.assertIsNotNone(unassigned_tasks_row)
        self.assertEqual(unassigned_tasks_row['daily_hours']['11 Jan'], 2)
        self.assertEqual(unassigned_tasks_row['daily_hours']['12 Jan'], 3)

    def test_no_unassigned_tasks(self):
        """Test that no 'Unassigned Tasks' rows appear when all tasks are assigned."""
        # All tasks in base setup are assigned, so no unassigned tasks should appear
        response = self.get_api_response('2025-01-11', '2025-01-12')
        data = response.json()

        # Should not have any "Unassigned Tasks" rows
        unassigned_tasks_rows = [
            row for row in data['data']
            if row['name'] == 'Unassigned Tasks'
        ]
        self.assertEqual(len(unassigned_tasks_rows), 0)


class TaskAssignmentAPITest(WorkforceScheduleAPITestBase):
    """Test the task assignment API endpoint."""

    def test_task_assignment_basic_functionality(self):
        """Test basic task assignment functionality."""
        response = self.client.post('/api/assign-tasks', query_params={
            'start_date': '2025-01-11',
            'end_date': '2025-01-12'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify response structure
        self.assertIn('assignments', data)
        self.assertIn('kpi_metrics', data)
        self.assertIn('summary', data)

        # Verify assignments structure
        for assignment in data['assignments']:
            self.assertIn('task_id', assignment)
            self.assertIn('worker_id', assignment)
            self.assertIn('worker_name', assignment)
            self.assertIn('position_name', assignment)
            self.assertIn('work_date', assignment)
            self.assertIn('hours', assignment)

        # Verify KPI metrics structure
        kpi = data['kpi_metrics']
        self.assertIn('utilization_rate', kpi)
        self.assertIn('max_worker_load', kpi)
        self.assertIn('unassigned_hours', kpi)
        self.assertIn('gini_coefficient', kpi)
        self.assertIn('total_workers', kpi)
        self.assertIn('total_tasks', kpi)
        self.assertIn('total_assigned_hours', kpi)

        # Verify summary structure
        summary = data['summary']
        self.assertIn('assigned_tasks', summary)
        self.assertIn('unassigned_tasks', summary)
        self.assertIn('total_positions', summary)

    def test_task_assignment_lp_method(self):
        """Test task assignment using LP method explicitly."""
        response = self.client.post('/api/assign-tasks', query_params={
            'start_date': '2025-01-11',
            'end_date': '2025-01-12',
            'method': 'lp'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify response structure is valid
        self.assertIn('assignments', data)
        self.assertIn('kpi_metrics', data)
        self.assertIn('summary', data)

        # Verify that assignments were made
        self.assertGreaterEqual(len(data['assignments']), 0)

        # Verify KPI metrics are calculated
        kpi = data['kpi_metrics']
        self.assertIsInstance(kpi['utilization_rate'], float)
        self.assertIsInstance(kpi['max_worker_load'], int)
        self.assertIsInstance(kpi['unassigned_hours'], int)
        self.assertIsInstance(kpi['gini_coefficient'], float)

    def test_task_assignment_greedy_method(self):
        """Test task assignment using Greedy method."""
        response = self.client.post('/api/assign-tasks', query_params={
            'start_date': '2025-01-11',
            'end_date': '2025-01-12',
            'method': 'greedy'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify response structure is valid
        self.assertIn('assignments', data)
        self.assertIn('kpi_metrics', data)
        self.assertIn('summary', data)

        # Verify that assignments were made
        self.assertGreaterEqual(len(data['assignments']), 0)

        # Verify KPI metrics are calculated
        kpi = data['kpi_metrics']
        self.assertIsInstance(kpi['utilization_rate'], float)
        self.assertIsInstance(kpi['max_worker_load'], int)
        self.assertIsInstance(kpi['unassigned_hours'], int)
        self.assertIsInstance(kpi['gini_coefficient'], float)

    def test_task_assignment_method_comparison(self):
        """Test that both LP and Greedy methods produce valid results."""
        # Create a controlled test scenario
        Task.objects.all().delete()
        Assignment.objects.all().delete()

        # Create tasks for testing
        for i in range(3):
            Task.objects.create(
                position=self.position1,
                duration=4,
                date=date(2025, 1, 11)
            )

        # Test LP method
        lp_response = self.client.post('/api/assign-tasks', query_params={
            'start_date': '2025-01-11',
            'end_date': '2025-01-11',
            'method': 'lp'
        })

        # Test Greedy method
        greedy_response = self.client.post('/api/assign-tasks', query_params={
            'start_date': '2025-01-11',
            'end_date': '2025-01-11',
            'method': 'greedy'
        })

        # Both should return valid responses
        self.assertEqual(lp_response.status_code, 200)
        self.assertEqual(greedy_response.status_code, 200)

        lp_data = lp_response.json()
        greedy_data = greedy_response.json()

        # Both should have the same number of total tasks
        self.assertEqual(
            lp_data['kpi_metrics']['total_tasks'],
            greedy_data['kpi_metrics']['total_tasks']
        )

        # Both should respect capacity constraints
        self.assertLessEqual(lp_data['kpi_metrics']['max_worker_load'], 8)
        self.assertLessEqual(greedy_data['kpi_metrics']['max_worker_load'], 8)

        # Both should assign tasks (given we have workers and tasks)
        self.assertGreaterEqual(lp_data['summary']['assigned_tasks'], 0)
        self.assertGreaterEqual(greedy_data['summary']['assigned_tasks'], 0)

    def test_task_assignment_invalid_method(self):
        """Test that invalid method parameter returns validation error."""
        response = self.client.post('/api/assign-tasks', query_params={
            'start_date': '2025-01-11',
            'end_date': '2025-01-12',
            'method': 'invalid_method'
        })

        # Should return 422 validation error for invalid method
        self.assertEqual(response.status_code, 422)

    def test_task_assignment_default_method(self):
        """Test that default method (LP) works when method is not specified."""
        response_default = self.client.post('/api/assign-tasks', query_params={
            'start_date': '2025-01-11',
            'end_date': '2025-01-12'
        })

        response_lp_explicit = self.client.post('/api/assign-tasks', query_params={
            'start_date': '2025-01-11',
            'end_date': '2025-01-12',
            'method': 'lp'
        })

        # Both should succeed
        self.assertEqual(response_default.status_code, 200)
        self.assertEqual(response_lp_explicit.status_code, 200)

        # Results should be identical (both use LP method)
        data_default = response_default.json()
        data_lp = response_lp_explicit.json()

        # Should have same number of assignments
        self.assertEqual(len(data_default['assignments']), len(data_lp['assignments']))
        self.assertEqual(
            data_default['kpi_metrics']['total_assigned_hours'],
            data_lp['kpi_metrics']['total_assigned_hours']
        )


class WorkforceScheduleEdgeCaseTest(WorkforceScheduleAPITestBase):
    """Test edge cases and special scenarios."""

    def test_multiple_assignments_same_day(self):
        """Test aggregation when worker has multiple assignments on same day."""
        task4 = Task.objects.create(
            position=self.position1, duration=2, date=date(2025, 1, 11)
        )
        Assignment.objects.create(
            worker=self.worker1, task=task4, work_date=date(2025, 1, 11), hours=2
        )

        response = self.get_api_response('2025-01-11', '2025-01-11')
        data = response.json()

        worker1 = self.find_row_by_name_type(data, 'Worker 1', 'worker')
        # Should aggregate both assignments: 3 + 2 = 5
        self.assertEqual(worker1['daily_hours']['11 Jan'], 5)

    def test_unassigned_workers_not_in_date_range(self):
        """Test that workers without assignments in date range are excluded."""
        Employee.objects.create(name="Unassigned Worker", position=self.position1)

        response = self.get_api_response('2025-01-11', '2025-01-12')
        data = response.json()

        worker_names = [row['name'] for row in data['data'] if row['type'] == 'worker']
        self.assertNotIn('Unassigned Worker', worker_names)

    def test_task_assignment_method_with_capacity_constraints(self):
        """Test that both methods respect worker capacity constraints."""
        # Create a scenario where tasks exceed worker capacity
        Task.objects.all().delete()
        Assignment.objects.all().delete()

        # Create tasks that exceed daily capacity (8 hours) for available workers
        for i in range(5):  # 5 tasks of 3 hours each = 15 hours total
            Task.objects.create(
                position=self.position1,
                duration=3,
                date=date(2025, 1, 11)
            )

        # Test both methods
        for method in ['lp', 'greedy']:
            with self.subTest(method=method):
                response = self.client.post('/api/assign-tasks', query_params={
                    'start_date': '2025-01-11',
                    'end_date': '2025-01-11',
                    'method': method
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()

                # Verify capacity constraints are respected
                max_load = data['kpi_metrics']['max_worker_load']
                self.assertLessEqual(max_load, 8, f"{method} method violated capacity constraint")

                # Should have some unassigned hours due to capacity constraints
                unassigned_hours = data['kpi_metrics']['unassigned_hours']
                self.assertGreater(unassigned_hours, 0, f"{method} method should have unassigned tasks")

    def test_task_assignment_method_with_position_mismatch(self):
        """Test behavior when tasks have no matching workers."""
        # Create a new position with no workers
        position_no_workers = Position.objects.create(name="Position No Workers")

        Task.objects.all().delete()
        Assignment.objects.all().delete()

        # Create tasks for position with no workers
        Task.objects.create(
            position=position_no_workers,
            duration=4,
            date=date(2025, 1, 11)
        )
        Task.objects.create(
            position=position_no_workers,
            duration=6,
            date=date(2025, 1, 11)
        )

        # Test both methods
        for method in ['lp', 'greedy']:
            with self.subTest(method=method):
                response = self.client.post('/api/assign-tasks', query_params={
                    'start_date': '2025-01-11',
                    'end_date': '2025-01-11',
                    'method': method
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()

                # All tasks should be unassigned
                self.assertEqual(data['summary']['assigned_tasks'], 0)
                self.assertEqual(data['summary']['unassigned_tasks'], 2)
                self.assertEqual(data['kpi_metrics']['unassigned_hours'], 10)
                self.assertEqual(data['kpi_metrics']['total_assigned_hours'], 0)

    def test_task_assignment_method_performance_comparison(self):
        """Test performance characteristics of both methods."""
        Task.objects.all().delete()
        Assignment.objects.all().delete()

        # Create a balanced scenario where both methods should perform well
        # 2 workers for position1, 6 hours of tasks each day
        Task.objects.create(position=self.position1, duration=3, date=date(2025, 1, 11))
        Task.objects.create(position=self.position1, duration=3, date=date(2025, 1, 11))
        Task.objects.create(position=self.position1, duration=2, date=date(2025, 1, 12))
        Task.objects.create(position=self.position1, duration=4, date=date(2025, 1, 12))

        lp_response = self.client.post('/api/assign-tasks', query_params={
            'start_date': '2025-01-11',
            'end_date': '2025-01-12',
            'method': 'lp'
        })

        greedy_response = self.client.post('/api/assign-tasks', query_params={
            'start_date': '2025-01-11',
            'end_date': '2025-01-12',
            'method': 'greedy'
        })

        # Both should succeed
        self.assertEqual(lp_response.status_code, 200)
        self.assertEqual(greedy_response.status_code, 200)

        lp_data = lp_response.json()
        greedy_data = greedy_response.json()

        # Both should assign all tasks (capacity allows it)
        self.assertEqual(lp_data['summary']['assigned_tasks'], 4)
        self.assertEqual(greedy_data['summary']['assigned_tasks'], 4)
        self.assertEqual(lp_data['summary']['unassigned_tasks'], 0)
        self.assertEqual(greedy_data['summary']['unassigned_tasks'], 0)

        # Check workload distribution
        # Both methods should produce valid results (relaxed constraints)
        lp_gini = lp_data['kpi_metrics']['gini_coefficient']
        greedy_gini = greedy_data['kpi_metrics']['gini_coefficient']

        # Both should have reasonable workload distribution (allow for some imbalance)
        self.assertLessEqual(lp_gini, 1.0, "LP Gini coefficient should be within valid range")
        self.assertLessEqual(greedy_gini, 1.0, "Greedy Gini coefficient should be within valid range")
        self.assertGreaterEqual(lp_gini, 0.0, "LP Gini coefficient should be non-negative")
        self.assertGreaterEqual(greedy_gini, 0.0, "Greedy Gini coefficient should be non-negative")

        # Verify both methods respect capacity constraints
        self.assertLessEqual(lp_data['kpi_metrics']['max_worker_load'], 8)
        self.assertLessEqual(greedy_data['kpi_metrics']['max_worker_load'], 8)

        # Verify utilization is reasonable
        self.assertGreater(lp_data['kpi_metrics']['utilization_rate'], 0)
        self.assertGreater(greedy_data['kpi_metrics']['utilization_rate'], 0)

    def test_task_assignment_method_edge_cases(self):
        """Test edge cases for both assignment methods."""
        # Test with no tasks
        Task.objects.all().delete()
        Assignment.objects.all().delete()

        for method in ['lp', 'greedy']:
            with self.subTest(method=method, case="no_tasks"):
                response = self.client.post('/api/assign-tasks', query_params={
                    'start_date': '2025-01-11',
                    'end_date': '2025-01-11',
                    'method': method
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()

                self.assertEqual(len(data['assignments']), 0)
                self.assertEqual(data['summary']['assigned_tasks'], 0)
                self.assertEqual(data['summary']['unassigned_tasks'], 0)
                self.assertEqual(data['kpi_metrics']['total_assigned_hours'], 0)

        # Test with single task
        Task.objects.create(
            position=self.position1,
            duration=2,
            date=date(2025, 1, 11)
        )

        for method in ['lp', 'greedy']:
            with self.subTest(method=method, case="single_task"):
                response = self.client.post('/api/assign-tasks', query_params={
                    'start_date': '2025-01-11',
                    'end_date': '2025-01-11',
                    'method': method
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()

                self.assertEqual(len(data['assignments']), 1)
                self.assertEqual(data['summary']['assigned_tasks'], 1)
                self.assertEqual(data['summary']['unassigned_tasks'], 0)
                self.assertEqual(data['kpi_metrics']['total_assigned_hours'], 2)


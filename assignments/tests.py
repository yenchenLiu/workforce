from django.test import TestCase
from django.test.client import Client
from datetime import date
from .models import Position, Employee, Task, Assignment


class WorkforceScheduleAPITest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create positions
        self.position1 = Position.objects.create(name="Position 1")
        self.position2 = Position.objects.create(name="Position 2")

        # Create employees
        self.worker1 = Employee.objects.create(name="Worker 1", position=self.position1)
        self.worker2 = Employee.objects.create(name="Worker 2", position=self.position1)
        self.worker3 = Employee.objects.create(name="Worker 3", position=self.position2)

        # Create tasks
        self.task1 = Task.objects.create(
            name="Task 1",
            position=self.position1,
            duration=8,
            date=date(2025, 1, 11)
        )
        self.task2 = Task.objects.create(
            name="Task 2",
            position=self.position1,
            duration=6,
            date=date(2025, 1, 12)
        )
        self.task3 = Task.objects.create(
            name="Task 3",
            position=self.position2,
            duration=5,
            date=date(2025, 1, 11)
        )

        # Create assignments matching the example table
        Assignment.objects.create(
            worker=self.worker1,
            task=self.task1,
            work_date=date(2025, 1, 11),
            hours=3
        )
        Assignment.objects.create(
            worker=self.worker2,
            task=self.task1,
            work_date=date(2025, 1, 11),
            hours=4
        )
        Assignment.objects.create(
            worker=self.worker1,
            task=self.task2,
            work_date=date(2025, 1, 12),
            hours=8
        )
        Assignment.objects.create(
            worker=self.worker2,
            task=self.task2,
            work_date=date(2025, 1, 12),
            hours=2
        )
        Assignment.objects.create(
            worker=self.worker3,
            task=self.task3,
            work_date=date(2025, 1, 11),
            hours=5
        )

    def test_workforce_schedule_with_date_range(self):
        """Test the workforce schedule endpoint with specific date range"""
        response = self.client.get('/api/workforce-schedule', {
            'start_date': '2025-01-11',
            'end_date': '2025-01-12'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Verify response structure
        self.assertIn('data', data)
        self.assertIn('date_columns', data)

        # Verify date columns
        expected_dates = ['11 Jan', '12 Jan']
        self.assertEqual(data['date_columns'], expected_dates)

        # Find position and worker data
        position1_data = None
        position2_data = None
        worker1_data = None
        worker2_data = None
        worker3_data = None

        for row in data['data']:
            if row['name'] == 'Position 1' and row['type'] == 'position':
                position1_data = row
            elif row['name'] == 'Position 2' and row['type'] == 'position':
                position2_data = row
            elif row['name'] == 'Worker 1' and row['type'] == 'worker':
                worker1_data = row
            elif row['name'] == 'Worker 2' and row['type'] == 'worker':
                worker2_data = row
            elif row['name'] == 'Worker 3' and row['type'] == 'worker':
                worker3_data = row

        # Verify position totals
        self.assertIsNotNone(position1_data)
        self.assertEqual(position1_data['daily_hours']['11 Jan'], 7)  # 3 + 4
        self.assertEqual(position1_data['daily_hours']['12 Jan'], 10)  # 8 + 2

        self.assertIsNotNone(position2_data)
        self.assertEqual(position2_data['daily_hours']['11 Jan'], 5)
        self.assertEqual(position2_data['daily_hours']['12 Jan'], 0)

        # Verify worker hours
        self.assertIsNotNone(worker1_data)
        self.assertEqual(worker1_data['daily_hours']['11 Jan'], 3)
        self.assertEqual(worker1_data['daily_hours']['12 Jan'], 8)

        self.assertIsNotNone(worker2_data)
        self.assertEqual(worker2_data['daily_hours']['11 Jan'], 4)
        self.assertEqual(worker2_data['daily_hours']['12 Jan'], 2)

        self.assertIsNotNone(worker3_data)
        self.assertEqual(worker3_data['daily_hours']['11 Jan'], 5)
        self.assertEqual(worker3_data['daily_hours']['12 Jan'], 0)

    def test_workforce_schedule_single_day(self):
        """Test with single day date range"""
        response = self.client.get('/api/workforce-schedule', {
            'start_date': '2025-01-11',
            'end_date': '2025-01-11'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should only have one date column
        self.assertEqual(data['date_columns'], ['11 Jan'])

        # Check that all rows have data for only one date
        for row in data['data']:
            self.assertEqual(len(row['daily_hours']), 1)
            self.assertIn('11 Jan', row['daily_hours'])

    def test_workforce_schedule_no_data(self):
        """Test with date range that has no assignments"""
        response = self.client.get('/api/workforce-schedule', {
            'start_date': '2025-01-15',
            'end_date': '2025-01-16'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should have date columns but empty data
        self.assertEqual(data['date_columns'], ['15 Jan', '16 Jan'])
        self.assertEqual(data['data'], [])

    def test_workforce_schedule_default_dates(self):
        """Test endpoint without date parameters (uses today)"""
        response = self.client.get('/api/workforce-schedule')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should use today's date
        today = date.today()
        expected_date = today.strftime('%d %b')
        self.assertEqual(data['date_columns'], [expected_date])

    def test_workforce_schedule_missing_end_date(self):
        """Test with only start_date provided"""
        response = self.client.get('/api/workforce-schedule', {
            'start_date': '2025-01-11'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should use start_date as end_date too
        self.assertEqual(data['date_columns'], ['11 Jan'])

    def test_workforce_schedule_response_schema(self):
        """Test that response matches expected schema"""
        response = self.client.get('/api/workforce-schedule', {
            'start_date': '2025-01-11',
            'end_date': '2025-01-12'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check top-level structure
        self.assertIn('data', data)
        self.assertIn('date_columns', data)
        self.assertIsInstance(data['data'], list)
        self.assertIsInstance(data['date_columns'], list)

        # Check each data row structure
        for row in data['data']:
            self.assertIn('name', row)
            self.assertIn('type', row)
            self.assertIn('daily_hours', row)
            self.assertIsInstance(row['name'], str)
            self.assertIn(row['type'], ['position', 'worker'])
            self.assertIsInstance(row['daily_hours'], dict)

            # Check that daily_hours has correct date keys
            for date_key in row['daily_hours']:
                self.assertIn(date_key, data['date_columns'])
                self.assertIsInstance(row['daily_hours'][date_key], int)

    def test_workforce_schedule_with_unassigned_workers(self):
        """Test that workers without assignments in date range are not included"""
        # Create a worker with no assignments in our test date range
        Employee.objects.create(
            name="Unassigned Worker",
            position=self.position1
        )

        response = self.client.get('/api/workforce-schedule', {
            'start_date': '2025-01-11',
            'end_date': '2025-01-12'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Unassigned worker should not appear in results
        worker_names = [row['name'] for row in data['data'] if row['type'] == 'worker']
        self.assertNotIn('Unassigned Worker', worker_names)

    def test_workforce_schedule_multiple_assignments_same_day(self):
        """Test aggregation when worker has multiple assignments on same day"""
        # Add another assignment for worker1 on the same day
        task4 = Task.objects.create(
            name="Task 4",
            position=self.position1,
            duration=2,
            date=date(2025, 1, 11)
        )
        Assignment.objects.create(
            worker=self.worker1,
            task=task4,
            work_date=date(2025, 1, 11),
            hours=2
        )

        response = self.client.get('/api/workforce-schedule', {
            'start_date': '2025-01-11',
            'end_date': '2025-01-11'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Find worker1 data
        worker1_data = next(
            row for row in data['data']
            if row['name'] == 'Worker 1' and row['type'] == 'worker'
        )

        # Should aggregate both assignments: 3 + 2 = 5
        self.assertEqual(worker1_data['daily_hours']['11 Jan'], 5)

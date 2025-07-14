# Workforce Scheduling

[![codecov](https://codecov.io/gh/yenchenLiu/workforce/branch/main/graph/badge.svg)](https://codecov.io/gh/yenchenLiu/workforce)

This is a Django-based workforce scheduling application.

## System Requirements

- Python 3.12+
- Django 5.0+

## Setup and Installation

1.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2. **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Running the Application

1.  **Apply database migrations:**
    ```bash
    python manage.py migrate
    ```

2.  **Initialize the database with seed data:**
    ```bash
    python manage.py load_seed_data
    ```

3.  **Start the development server:**
    ```bash
    python manage.py runserver
    ```

The application will be available at `http://127.0.0.1:8000/`.

## Testing

To run the unit tests, use the following command:

```bash
python manage.py test
```

To generate a test coverage report, you can use the following commands:

```bash
coverage run --source='.' manage.py test
coverage report
```

## API Documentation

To view the API documentation, navigate to `http://127.0.0.1:8000/api/docs` in your browser.

## assign-tasks API

The `assign-tasks` API schedules tasks for workers. It can use one of two methods: Linear Programming (default) or a Greedy algorithm. The API returns the assignment results and relevant KPI data.

You can select the method using the `method` query parameter in your POST request to `/api/assign-tasks`.

-   `method=lp` (default): Uses linear programming to find an optimal task assignment. This method aims to maximize the total hours assigned to workers, subject to constraints like worker availability and skills.
-   `method=greedy`: Uses a greedy algorithm that assigns tasks one by one to the most suitable available worker. This method is faster but may not produce a globally optimal solution.
# Workforce Scheduling

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

The `assign-tasks` API uses linear programming to schedule tasks. It returns the assignment results and relevant KPI data.
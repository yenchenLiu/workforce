# Workforce Scheduling

This is a Django-based workforce scheduling application.

## Setup and Installation

1.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2**Install the required dependencies:**
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

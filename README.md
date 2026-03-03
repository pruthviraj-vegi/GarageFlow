# GarageFlow

GarageFlow is a Django-based management application for automotive workshops and garages. It streamlines job card creation, inventory management, customer tracking, and invoicing.

## Features

- **Job Cards**: Track vehicle repair and service details, manage statuses, and associate inventory items.
- **Inventory**: Manage parts and supplies with barcode support and quantity tracking.
- **Customers**: Maintain customer records and service histories.
- **Vehicles**: Track vehicle makes, models, and specifications.
- **Invoicing**: Generate invoices from completed job cards.

## Prerequisites

- Python 3.10+
- PostgreSQL (if using the production database configuration)

## Setup Instructions

1. **Clone the repository** (if you haven't already):

   ```bash
   git clone <repository-url>
   cd GarageFlow
   ```

2. **Set up a virtual environment**:

   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   Make sure you install the required packages. Include the database driver:

   ```bash
   pip install django python-decouple psycopg2-binary
   ```

4. **Configure Environment Variables**:
   Create a `.env` file in the project root (next to `manage.py`):

   ```ini
   DEBUG=True
   SECRET_KEY=your-secret-key-here
   DB_ENGINE=django.db.backends.postgresql
   DB_NAME=garageflow
   DB_USER=your_postgres_user
   DB_PASSWORD=your_postgres_password
   DB_HOST=localhost
   DB_PORT=5432
   ```

5. **Set up the Database**:
   Ensure PostgreSQL is running and the database matches your `.env` configuration, then run:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

6. **Create a Superuser** (optional but recommended):

   ```bash
   python manage.py createsuperuser
   ```

7. **Run the Development Server**:
   ```bash
   python manage.py runserver
   ```
   Access the application at `http://127.0.0.1:8000/`.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'psycopg2'`**: Ensure you have installed the PostgreSQL adapter. Run `pip install psycopg2-binary`.
- **`ImportError: cannot import name 'config' from 'decouple'`**: You may have installed the wrong decouple package. Run `pip uninstall decouple` followed by `pip install python-decouple`.

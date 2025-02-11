# Airflow DAGs Monitor

A web application that monitors Airflow DAGs across multiple environments and projects. The application shows a table with DAG statuses and updates automatically every 5 minutes.

## Features

- Monitors multiple Airflow instances across different environments (dev, qual, prod)
- Auto-refreshes data every 5 minutes
- Interactive table with sorting, filtering, and grouping
- Export data to CSV, Excel
- Color-coded status indicators
- Responsive design

## Prerequisites

- Python 3.7+
- pip (Python package manager)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd airflow-monitoring
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

The application reads project and environment information from `projects.csv`. This file contains the mapping of projects to their respective Airflow instances.

## Running the Application

1. Make sure you're in the project directory and your virtual environment is activated

2. Start the Flask application:
```bash
python airflow_monitor/app.py
```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

## Table Features

- **Grouping**: Results are grouped by Project and Environment
- **Filtering**: Each column has a filter option
- **Sorting**: Click on column headers to sort
- **Export**: Use the buttons to export to CSV or Excel
- **Status Colors**: 
  - Green: Success/Enabled
  - Red: Failed/Disabled

## Development

The application is built with:
- Flask (Backend)
- Bootstrap 5 (UI Framework)
- DataTables (Interactive Tables)
- APScheduler (Background Tasks)

## Project Structure

```
airflow-monitoring/
├── airflow_monitor/
│   ├── __init__.py
│   ├── app.py
│   ├── airflow_client.py
│   ├── templates/
│   │   └── index.html
│   └── static/
├── projects.csv
├── requirements.txt
└── README.md
``` 
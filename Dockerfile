FROM python:3.9-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY airflow_monitor/ ./airflow_monitor/
COPY projects.csv .

# Create necessary directories
RUN mkdir -p airflow_monitor/templates airflow_monitor/static

# Set environment variables
ENV FLASK_APP=airflow_monitor/app.py
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "airflow_monitor/app.py"] 
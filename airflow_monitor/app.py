from flask import Flask, render_template, jsonify
from flask_apscheduler import APScheduler
from airflow_client import AirflowClient
import os
import json
from datetime import datetime

app = Flask(__name__)
scheduler = APScheduler()

# Initialize the Airflow client with the CSV file
client = AirflowClient('projects.csv')

# Global variable to store the latest data
latest_data = []

def update_dag_data():
    """Background job to update DAG data"""
    global latest_data
    latest_data = client.get_all_projects_dags()
    app.logger.info(f"Updated DAG data at {datetime.now()}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/dags')
def get_dags():
    return jsonify(latest_data)

def create_app():
    # Create necessary directories
    os.makedirs('airflow_monitor/templates', exist_ok=True)
    os.makedirs('airflow_monitor/static', exist_ok=True)
    
    # Configure scheduler
    app.config['SCHEDULER_API_ENABLED'] = True
    scheduler.init_app(app)
    scheduler.add_job(id='update_dag_data', func=update_dag_data, 
                     trigger='interval', minutes=5)
    scheduler.start()
    
    # Initial data load
    update_dag_data()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True) 
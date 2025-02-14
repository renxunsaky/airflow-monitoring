from flask import Flask, render_template, jsonify
from flask_apscheduler import APScheduler
from airflow_client import AirflowClient
from vault_client import VaultClient
import os
import json
from datetime import datetime

app = Flask(__name__, static_folder='static')
scheduler = APScheduler()

# Default paths for local development
DEFAULT_STAGING_CERT_PATH = "certs/staging/client.crt"
DEFAULT_STAGING_KEY_PATH = "certs/staging/client.key"
DEFAULT_PROD_CERT_PATH = "certs/prod/client.crt"
DEFAULT_PROD_KEY_PATH = "certs/prod/client.key"

# Default Vault namespaces
DEFAULT_STAGING_NAMESPACE = "admin/staging"
DEFAULT_PROD_NAMESPACE = "admin/prod"

# Get configuration from environment or use defaults
STAGING_CERT_PATH = os.getenv('VAULT_STAGING_CERT_PATH', DEFAULT_STAGING_CERT_PATH)
STAGING_KEY_PATH = os.getenv('VAULT_STAGING_KEY_PATH', DEFAULT_STAGING_KEY_PATH)
PROD_CERT_PATH = os.getenv('VAULT_PROD_CERT_PATH', DEFAULT_PROD_CERT_PATH)
PROD_KEY_PATH = os.getenv('VAULT_PROD_KEY_PATH', DEFAULT_PROD_KEY_PATH)
STAGING_NAMESPACE = os.getenv('VAULT_STAGING_NAMESPACE', DEFAULT_STAGING_NAMESPACE)
PROD_NAMESPACE = os.getenv('VAULT_PROD_NAMESPACE', DEFAULT_PROD_NAMESPACE)

# Initialize the Vault client with both sets of credentials and namespaces
vault_client = VaultClient(
    staging_cert_path=STAGING_CERT_PATH,
    staging_key_path=STAGING_KEY_PATH,
    prod_cert_path=PROD_CERT_PATH,
    prod_key_path=PROD_KEY_PATH,
    staging_namespace=STAGING_NAMESPACE,
    prod_namespace=PROD_NAMESPACE
)

# Initialize the Airflow client with the CSV file and Vault client
client = AirflowClient('projects.csv', vault_client)

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
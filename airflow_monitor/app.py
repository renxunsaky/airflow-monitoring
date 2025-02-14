from flask import Flask, render_template, jsonify, send_from_directory
from flask_apscheduler import APScheduler
from airflow_client import AirflowClient
from vault_client import VaultClient
import os
import json
from datetime import datetime
import threading

app = Flask(__name__, 
    static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), 'static')))
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
last_update_time = None
data_lock = threading.Lock()  # Add thread safety

def update_dag_data():
    """Background job to update DAG data"""
    global latest_data, last_update_time
    try:
        new_data = client.get_all_projects_dags()
        with data_lock:
            latest_data = new_data
            last_update_time = datetime.now()
        app.logger.info(f"Updated DAG data at {last_update_time}")
    except Exception as e:
        app.logger.error(f"Error updating DAG data: {str(e)}")

def initial_data_load():
    """Initial data load in background"""
    app.logger.info("Starting initial data load...")
    update_dag_data()
    app.logger.info("Initial data load completed")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/dags')
def get_dags():
    global latest_data, last_update_time
    with data_lock:
        # If no data is available yet, trigger an update
        if not last_update_time:
            update_dag_data()
        # If data is older than 5 minutes, trigger background update
        elif (datetime.now() - last_update_time).total_seconds() > 300:
            threading.Thread(target=update_dag_data).start()
        return jsonify(latest_data)

# Add a route to serve static files directly
@app.route('/static/<path:filename>')
def static_files(filename):
    app.logger.info(f"Requesting static file: {filename}")
    app.logger.info(f"Static folder path: {app.static_folder}")
    try:
        return send_from_directory(app.static_folder, filename)
    except Exception as e:
        app.logger.error(f"Error serving static file: {str(e)}")
        return f"Error: {str(e)}", 404

def create_app():
    # Ensure the static directory exists
    static_dir = os.path.join(os.path.dirname(__file__), 'static')
    os.makedirs(static_dir, exist_ok=True)
    
    # Configure scheduler
    app.config['SCHEDULER_API_ENABLED'] = True
    scheduler.init_app(app)
    scheduler.add_job(id='update_dag_data', func=update_dag_data, 
                     trigger='interval', minutes=5)
    scheduler.start()
    
    # Start initial data load in background
    threading.Thread(target=initial_data_load).start()
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True) 
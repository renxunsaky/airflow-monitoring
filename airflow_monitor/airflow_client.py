import pandas as pd
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional
import logging
from vault_client import VaultClient
from croniter import croniter
import pendulum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AirflowClient:
    def __init__(self, csv_path: str, vault_client: VaultClient):
        self.environments_df = pd.read_csv(csv_path)
        self.session = requests.Session()
        self.vault_client = vault_client
        self.credentials_cache = {}
        self.version_cache = {}  # Cache for Airflow versions
    
    def get_airflow_url(self, ap_code: str, env: str, tenant_suffix: str) -> str:
        return f"https://astronomer-{ap_code}-{env}-{tenant_suffix}.data.cloud.net.intra"
    
    def get_credentials(self, project: str, environment: str) -> Dict[str, str]:
        """Get cached credentials or fetch new ones from Vault"""
        cache_key = f"{project}/{environment}"
        if cache_key not in self.credentials_cache:
            self.credentials_cache[cache_key] = self.vault_client.get_airflow_credentials(project, environment)
        return self.credentials_cache[cache_key]
    
    def get_airflow_version(self, base_url: str, credentials: Dict[str, str]) -> str:
        """Get Airflow version from API"""
        cache_key = base_url
        if cache_key not in self.version_cache:
            try:
                version_url = f"{base_url}/api/v1/version"
                response = self.session.get(
                    version_url,
                    auth=(credentials['username'], credentials['password'])
                )
                response.raise_for_status()
                version_data = response.json()
                self.version_cache[cache_key] = version_data.get('version', 'N/A')
            except Exception as e:
                logger.error(f"Error fetching Airflow version for {base_url}: {str(e)}")
                self.version_cache[cache_key] = 'N/A'
        return self.version_cache[cache_key]
    
    def get_expected_last_run_time(self, schedule: str, last_run_time: str) -> Optional[str]:
        """Calculate the expected last run time based on schedule and last run time"""
        try:
            if not schedule or not last_run_time:
                return None

            # Convert to pendulum datetime for better timezone handling
            last_run = pendulum.parse(last_run_time)
            
            # Create croniter instance
            cron = croniter(schedule, last_run)
            
            # Get the previous execution time according to schedule
            expected_last_run = cron.get_prev(datetime)
            
            return expected_last_run.isoformat()
            
        except Exception as e:
            logger.error(f"Error calculating expected last run time: {str(e)}")
            return None

    def get_dag_info(self, base_url: str, dag_id: str, project: str, environment: str) -> Dict:
        try:
            # Get credentials for authentication
            credentials = self.get_credentials(project, environment)
            
            # Get DAG details
            dag_url = f"{base_url}/api/v1/dags/{dag_id}"
            dag_response = self.session.get(
                dag_url,
                auth=(credentials['username'], credentials['password'])
            )
            dag_response.raise_for_status()
            dag_data = dag_response.json()

            # Get last DAG run
            dag_runs_url = f"{base_url}/api/v1/dags/{dag_id}/dagRuns?limit=1&order_by=-start_date"
            runs_response = self.session.get(
                dag_runs_url,
                auth=(credentials['username'], credentials['password'])
            )
            runs_response.raise_for_status()
            runs_data = runs_response.json()

            last_run = runs_data['dag_runs'][0] if runs_data['dag_runs'] else None
            schedule = dag_data.get('schedule_interval', None)
            last_run_time = last_run['start_date'] if last_run else None
            
            return {
                'dag_id': dag_id,
                'is_enabled': dag_data['is_paused'] == False,
                'last_run_time': last_run_time,
                'status': last_run['state'] if last_run else 'No runs',
                'version': self.get_airflow_version(base_url, credentials),
                'schedule': schedule,
                'expected_last_run_time': self.get_expected_last_run_time(schedule, last_run_time) if schedule and last_run_time else None
            }
        except Exception as e:
            logger.error(f"Error fetching DAG info for {dag_id}: {str(e)}")
            return {
                'dag_id': dag_id,
                'is_enabled': False,
                'last_run_time': None,
                'status': 'Error',
                'version': 'N/A',
                'schedule': None,
                'expected_last_run_time': None
            }

    def get_all_dags(self, project_row: pd.Series) -> List[Dict]:
        base_url = self.get_airflow_url(
            project_row['ap_code'],
            project_row['env'],
            project_row['airflow_tenant_suffix']
        )
        
        try:
            # Get credentials for authentication
            credentials = self.get_credentials(project_row['project_name'], project_row['env'])
            
            # Get list of DAGs
            dags_url = f"{base_url}/api/v1/dags"
            response = self.session.get(
                dags_url,
                auth=(credentials['username'], credentials['password'])
            )
            response.raise_for_status()
            dags_data = response.json()

            results = []
            for dag in dags_data['dags']:
                dag_info = self.get_dag_info(
                    base_url, 
                    dag['dag_id'],
                    project_row['project_name'],
                    project_row['env']
                )
                dag_info.update({
                    'project_name': project_row['project_name'],
                    'environment': project_row['env'],
                })
                results.append(dag_info)
            
            return results
        except Exception as e:
            logger.error(f"Error fetching DAGs for {project_row['project_name']}-{project_row['env']}: {str(e)}")
            return []

    def get_all_projects_dags(self) -> List[Dict]:
        all_dags = []
        for _, row in self.environments_df.iterrows():
            project_dags = self.get_all_dags(row)
            all_dags.extend(project_dags)
        return all_dags 
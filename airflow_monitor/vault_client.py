import hvac
import os
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class VaultClient:
    def __init__(self, staging_cert_path: str, staging_key_path: str, 
                 prod_cert_path: str, prod_key_path: str,
                 staging_namespace: str, prod_namespace: str):
        self.staging_cert_path = staging_cert_path
        self.staging_key_path = staging_key_path
        self.prod_cert_path = prod_cert_path
        self.prod_key_path = prod_key_path
        self.staging_namespace = staging_namespace
        self.prod_namespace = prod_namespace
        self.staging_client = None
        self.prod_client = None
        self.namespace_tokens = {}
        self._initialize_clients()

    def _initialize_clients(self):
        try:
            # Initialize staging Vault client
            self.staging_client = hvac.Client(
                url="https://vault.staging.net",
                cert=(self.staging_cert_path, self.staging_key_path),
                namespace=self.staging_namespace
            )
            self.staging_client.auth.cert.login()
            self.namespace_tokens[self.staging_namespace] = self.staging_client.adapter.token
            logger.info("Successfully authenticated to staging Vault")

            # Initialize production Vault client
            self.prod_client = hvac.Client(
                url="https://vault.group.net",
                cert=(self.prod_cert_path, self.prod_key_path),
                namespace=self.prod_namespace
            )
            self.prod_client.auth.cert.login()
            self.namespace_tokens[self.prod_namespace] = self.prod_client.adapter.token
            logger.info("Successfully authenticated to production Vault")
        except Exception as e:
            logger.error(f"Failed to initialize Vault clients: {str(e)}")
            raise

    def _get_client_for_environment(self, environment: str) -> hvac.Client:
        """Get the appropriate Vault client based on environment"""
        if environment.lower() in ['dev', 'qual']:
            return self.staging_client
        elif environment.lower() == 'prod':
            return self.prod_client
        else:
            raise ValueError(f"Unknown environment: {environment}")

    def get_airflow_credentials(self, project: str, environment: str) -> Dict[str, str]:
        """
        Get Airflow credentials from Vault for a specific project and environment
        """
        try:
            client = self._get_client_for_environment(environment)
            
            # Save current namespace and token
            original_namespace = client.adapter.namespace
            original_token = client.adapter.token
            
            # Update namespace and get or create token for it
            project_namespace = f"{project}/{environment}"
            client.adapter.namespace = project_namespace
            
            if project_namespace not in self.namespace_tokens:
                # Need to authenticate for this namespace
                client.auth.cert.login()
                self.namespace_tokens[project_namespace] = client.adapter.token
            else:
                # Reuse existing token for this namespace
                client.adapter.token = self.namespace_tokens[project_namespace]
            
            try:
                # Read the secret from Vault
                secret_path = f"secret/data/airflow/credentials"
                secret = client.secrets.kv.v2.read_secret_version(
                    path=secret_path
                )
                
                # Extract credentials
                data = secret['data']['data']
                return {
                    'username': data['airflow_user'],
                    'password': data['airflow_password']
                }
            finally:
                # Restore original namespace and token
                client.adapter.namespace = original_namespace
                client.adapter.token = original_token
                
        except Exception as e:
            logger.error(f"Failed to get Airflow credentials for {project}/{environment}: {str(e)}")
            raise 
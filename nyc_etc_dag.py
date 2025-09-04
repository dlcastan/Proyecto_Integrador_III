from datetime import datetime, timedelta
import os

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator

# Configuración general
default_args = {
    "owner": "data-eng",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

# Imagen pipeline
NYC_ELT_IMAGE = os.environ.get("NYC_ELT_IMAGE", "nyc-elt:latest")

# Variables
def common_env():
    keys = [
        "AWS_ACCESS_KEY_ID","AWS_SECRET_ACCESS_KEY","AWS_REGION","S3_BUCKET_NAME",
        "PGHOST","PGDATABASE","PGUSER","PGPASSWORD","PGPORT",
        "BCRA_BASE_URL","BCRA_API_PATH","BCRA_CAT_PATH","BCRA_FROM","BCRA_TO","BCRA_SERIES",
        "VERIFY_SSL",
    ]
    return {k: os.environ.get(k) for k in keys if os.environ.get(k) is not None}

with DAG(
    dag_id="nyc_elt_bcra_dbt",
    default_args=default_args,
    description="ELT: AB_NYC -> S3/RDS, BCRA -> S3, luego dbt",
    schedule_interval="0 9 * * *",  # todos los días 09:00
    start_date=datetime(2025, 8, 1),
    catchup=False,
    tags=["nyc","elt","dbt","bcra"],
) as dag:

    raw_to_s3_rds = DockerOperator(
        task_id="raw_to_s3_rds",
        image=NYC_ELT_IMAGE,
        api_version="auto",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        environment={
            **common_env(),
            "RUN_RAW": "true",
            "RUN_BCRA_FETCH": "false",
            "RUN_DBT": "false",
        },
        auto_remove=True,
    )

    fetch_bcra = DockerOperator(
        task_id="fetch_bcra",
        image=NYC_ELT_IMAGE,
        api_version="auto",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        environment={
            **common_env(),
            "RUN_RAW": "false",
            "RUN_BCRA_FETCH": "true",
            "RUN_DBT": "false",
        },
        auto_remove=True,
    )

    dbt_build = DockerOperator(
        task_id="dbt_build",
        image=NYC_ELT_IMAGE,
        api_version="auto",
        docker_url="unix://var/run/docker.sock",
        network_mode="bridge",
        environment={
            **common_env(),
            "RUN_RAW": "false",
            "RUN_BCRA_FETCH": "false",
            "RUN_DBT": "true",
        },
        auto_remove=True,
    )

    raw_to_s3_rds >> fetch_bcra >> dbt_build

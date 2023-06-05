from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.docker_operator import DockerOperator
from airflow.operators.bash import BashOperator
from airflow.models import Variable
from airflow.providers.microsoft.azure.hooks.wasb import WasbHook
from airflow.providers.postgres.hooks.postgres import PostgresHook
import docker
import ast
import requests

import csv
import logging
from tempfile import NamedTemporaryFile

GITHUB_KEY = Variable.get("github_key")
FASTAPI_URL = Variable.get("fastapi_my_linux_url")

default_args = {
    'owner': 'Woody',
    'retries': 5,
    'retry_delay': timedelta(minutes=5)
}

host = 'host.docker.internal'


def postgres_to_blob(ti):
    datetimeStr = str(datetime.now().strftime('%d%m%Y_%H%M%S'))
    
    hook = PostgresHook(postgres_conn_id="postgres_azure") # local: postgres_local_devDB
    conn = hook.get_conn()
    cursor = conn.cursor()
    

    sql = """
        with userActionRate as (
            select 
                uhra."userId", 
                uhra."helpRequestId", 
                case 
                    when uhra."actionType" like 'dislike' then 0
                    when uhra."actionType" like 'view' then 3
                    when uhra."actionType" like 'like' then 6
                    when uhra."actionType" like 'bookmark' then 7
                    when uhra."actionType" like 'commit' then 10
                end
                as "actionRate"
            from "UserHelpRequestAction" uhra
        ),
        userWithInterest as (
            select 
                u.id, username, email, address, city, country, phone, "displayName", 
                district, occupation, "dateOfBirth", date_part('year', (SELECT current_timestamp)) - date_part('year', "dateOfBirth") as age, gender,
                string_agg(c."name", ',') as "userInterest"
            from "User" u 
            left join "Interest" i 
            on u.id = i."userId" 
            left join "Category" c 
            on i."categoryId" = c.id 
            group by 
                u.id, username, email, address, city, country, phone, "displayName", 
                district, occupation, "dateOfBirth", age, gender
        ),
        helpRequestWithCategory as (
            select 
                hr.id,
                hr.district,
                hr.price,
                hr.title,
                hr.description,
                string_agg(c."name", ',') as category
            from "HelpRequest" hr 
            left join "HelpRequestCategory" hrc
            on hr.id = hrc."helpRequestId"
            left join "Category" c 
            on hrc."categoryId" = c.id 
            group by 
                hr.id,
                hr.category,
                hr.district,
                hr.price,
                hr.title,
                hr.description
        )
        select
            uar."userId", 
            uar."helpRequestId", 
            max(uar."actionRate") as "actionRate", 
            date_part('year', (SELECT current_timestamp)) - date_part('year', u."dateOfBirth") as age,
            u.district as "userDistrict", 
            u.gender, 
            u."userInterest",
            hr.category, 
            hr.title, 
            hr.description, 
            hr.district as "helpRequestDistrict", 
            hr.price 
        from userActionRate as uar
        left join userWithInterest u 
        on uar."userId"  = u.id 
        left join helpRequestWithCategory hr 
        on uar."helpRequestId" = hr.id 
        group by 
            uar."userId", 
            uar."helpRequestId", 
            u."dateOfBirth", 
            u.district, 
            u.gender, 
            u."userInterest",
            hr.category, 
            hr.title, 
            hr.description, 
            hr.district, 
            hr.price 
    """
    
    cursor.execute(sql)

    with NamedTemporaryFile(mode='w', ) as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow([i[0] for i in cursor.description])
        csv_writer.writerows(cursor)
        f.flush()
        cursor.close()
        logging.info("Saved Users data in text file")

        blobHook = WasbHook(wasb_conn_id="azure_blob_conn_id")
        logging.info(f"f.name: {f.name}")
        blob_name = f"UserHelpRequestActionDataset_{datetimeStr}.csv"
        blobHook.load_file(
            file_path=f.name,
            container_name="dataset",
            blob_name=blob_name,
            create_container=True
        )
        ti.xcom_push(key='dataset_name', value=blob_name)
        logging.info("User Help Request Action Dataset has been pushed to Blob!", f.name)
    
    cursor = conn.cursor()
    sql = """
        select 
            u.id, username, email, address, city, country, phone, "displayName", 
            district, occupation, "dateOfBirth", 
            date_part('year', (SELECT current_timestamp)) - date_part('year', "dateOfBirth") as age, 
            gender,
            string_agg(c."name", ',') as "userInterest"
        from "User" u 
        left join "Interest" i 
        on u.id = i."userId" 
        left join "Category" c 
        on i."categoryId" = c.id 
        group by 
            u.id, username, email, address, city, country, phone, "displayName", 
            district, occupation, "dateOfBirth", age, gender
    """
    
    cursor.execute(sql)
    with NamedTemporaryFile(mode='w', ) as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow([i[0] for i in cursor.description])
        csv_writer.writerows(cursor)
        f.flush()
        cursor.close()
        logging.info("Saved Users data in text file")

        blobHook = WasbHook(wasb_conn_id="azure_blob_conn_id")
        logging.info(f"f.name: {f.name}")
        blob_name = f"UserData_{datetimeStr}.csv"
        blobHook.load_file(
            file_path=f.name,
            container_name="users",
            blob_name=blob_name,
            create_container=True
        )
        ti.xcom_push(key='UserData_name', value=blob_name)
        logging.info("User data has been pushed to Blob!", f.name)
    
    cursor = conn.cursor()
    sql = """
        select 
            hr.id,
            hr.district,
            hr.price,
            hr.title,
            hr.description,
            case 
                when hr.is_taken = true then true
                when hr.is_taken = false then false
                when hr.is_taken is NULL then false
            end
            as is_taken, 
            string_agg(c."name", ',') as category
        from "HelpRequest" hr 
        left join "HelpRequestCategory" hrc
        on hr.id = hrc."helpRequestId"
        left join "Category" c 
        on hrc."categoryId" = c.id 
        group by 
            hr.id,
            hr.category,
            hr.district,
            hr.price,
            hr.title,
            hr.description
    """
    
    cursor.execute(sql)
    with NamedTemporaryFile(mode='w', ) as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow([i[0] for i in cursor.description])
        csv_writer.writerows(cursor)
        f.flush()
        cursor.close()
        logging.info("Saved Users data in text file")

        blobHook = WasbHook(wasb_conn_id="azure_blob_conn_id")
        logging.info(f"f.name: {f.name}")
        blob_name = f"HelpRequestData_{datetimeStr}.csv"
        blobHook.load_file(
            file_path=f.name,
            container_name="help-requests",
            blob_name=blob_name,
            create_container=True
        )
        ti.xcom_push(key='HelpRequestData_name', value=blob_name)
        logging.info("Help Request data has been pushed to Blob!", f.name)
    
    conn.close()


def update_fastapi_model(ti):
    UserDataName = ti.xcom_pull(task_ids='postgres_to_blob', key='UserData_name')
    HelpRequestDataName = ti.xcom_pull(task_ids='postgres_to_blob', key='HelpRequestData_name')
    return_value = ti.xcom_pull(
        task_ids='start_training', key='return_value').split('\n')[-1]
    return_value = ast.literal_eval(return_value)
    print(return_value['zipped_model_name'])
    modelConfig = {
        "modelName": return_value['zipped_model_name'],
        "userDataName": UserDataName,
        "helpRequestDataName": HelpRequestDataName
    }
    updateFastapiModelRequest = requests.post(f"http://{FASTAPI_URL}/updateModel/", json=modelConfig)
    print(f"updateFastapiModelRequest.status_code: {updateFastapiModelRequest.status_code}")
    if updateFastapiModelRequest.status_code != 200:
        raise ValueError('Fastapi server respone status_code is not 200!')
    print(updateFastapiModelRequest.json())

with DAG(
    default_args=default_args,
    dag_id='Hourly_recommender_system_retraining_task',
    description='Hourly_recommender_system_retraining',
    start_date=datetime(2023, 4, 8),
    schedule_interval='@hourly',
    catchup=False,
) as dag:

    start_training_task = DockerOperator(
        task_id='start_training',
        image='recommenders:gpu',
        api_version='auto',
        auto_remove=True,
        container_name='myRecommendersContainer',
        command="bash -c 'cd src && python ./train.py'",
        docker_url=f'tcp://{host}:2375',
        network_mode="bridge",
        device_requests=[
                # Add all gpu's to the container
                docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])
        ],
        environment={
            "dataset_name": "{{ti.xcom_pull(task_ids='postgres_to_blob', key='dataset_name')}}"
        }
    )

    update_fastapi_model_task = PythonOperator(
        task_id='update_fastapi_model',
        provide_context=True,
        python_callable=update_fastapi_model,
        dag=dag
    )
    
    postgres_to_blob_task = PythonOperator(
        task_id='postgres_to_blob',
        python_callable=postgres_to_blob,
        dag=dag
    )

    postgres_to_blob_task  >> start_training_task >> update_fastapi_model_task 

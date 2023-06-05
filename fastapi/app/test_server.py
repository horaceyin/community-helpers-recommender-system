import requests
import os
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

# connectionString = "AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;DefaultEndpointsProtocol=http;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
# # Create a unique name for the container
# container_name = "rs-models"
# # Create the ContainerClient object

# rs_models_container_client = \
#     ContainerClient.from_connection_string(connectionString, container_name)
# try:
#     rs_models_container_client.get_container_properties()
# except Exception as e:
#     # Create the container "rs-models", if not exist
#     rs_models_container_client.create_container()

# with open(file='/home/woodyw/githubRepo/fyp/RecommenderSystem/fastapi/app/test.zip', mode="wb") as sample_blob:
#         download_stream = rs_models_container_client.download_blob('12032023_112820.zip')
#         sample_blob.write(download_stream.readall())

try:
    # print(requests.get("http://127.0.0.1:80/updateModel/12032023_112820.zip").json())
    # print(requests.get("http://127.0.0.1:80/recommendItem/5").json())
    # print(requests.get("http://127.0.0.1:80/recommendItem/5?start=0&end=5").json())
    # print(requests.get("http://127.0.0.1:80/modelVersion/").json())
    # print(requests.get("http://woodyw2.ddns.net:80/recommendItem/5?start=0&end=5").json())
    userFeatures = {
        'age': 45,
        'gender': 'Male',
        'userDistrict': 'Eastern'
    }
    # print(requests.post("http://woodyw2.ddns.net:80/recommendItemForNewUser?start=0&end=20", json=userFeatures).json())
    
    print(requests.post("http://127.0.0.1:80/recommendItemForNewUser?start=0&end=20", json=userFeatures).json())
except Exception as e:
    print(str(e))
    
# try:
#     print(requests.get("http://127.0.0.1:80/").json())
# except Exception as e:
#     print(str(e))
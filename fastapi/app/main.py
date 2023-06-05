from enum import Enum
from typing import List
from typing import Dict
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel
from typing import Union
import tensorflow as tf;
import keras
import pandas as pd
import uuid
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import os
import zipfile
import shutil

connectionString = "DefaultEndpointsProtocol=https;AccountName=communityhelperstudentea;AccountKey=EwWwuGer7cUwdCwBiyvrenVNqi4RSvgnWzfAhFTtHEBcBg/eIjBjLoYo/1U8n7eiiEUvX0gjnD/t+ASt2ncvPQ==;EndpointSuffix=core.windows.net"

# Create a unique name for the container
model_container_name = "rs-models"
user_data_container_name = "users"
helpRequest_data_container_name = "help-requests"
# Create the ContainerClient object

app = FastAPI()

model_dir = None
data_dir = os.path.join('/', 'data')
user_data_path = None
helpRequest_data_path = None


class ModelConfig(BaseModel):
    modelName: str
    userDataName: str
    helpRequestDataName: str

class UserFeatures(BaseModel):
    age: int
    gender: str
    userDistrict: str
    
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Custom title",
        version="2.5.0",
        description="This is a very custom OpenAPI schema",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
    

@app.post("/updateModel/")
async def updateModel(modelConfig: ModelConfig) -> int:
    global model_dir
    global user_data_path
    global helpRequest_data_path
    global connectionString
    global model_container_name
    global user_data_container_name
    global helpRequest_data_container_name
    
    modelName = modelConfig.modelName
    userDataName = modelConfig.userDataName
    helpRequestDataName = modelConfig.helpRequestDataName
    
    print(f"userDataName: {userDataName}")
    print(f"helpRequestDataName: {helpRequestDataName}")
    
    if model_dir != None and os.path.basename(os.path.normpath(model_dir)) == modelName[:-4]:
        raise HTTPException(
            status_code=404, detail=f"Model: {modelName[:-4]} is already existed.")
        
    if user_data_path != None and os.path.basename(user_data_path) == userDataName:
        raise HTTPException(
            status_code=404, detail=f"User Data: {userDataName} is already existed.")
    
    if helpRequest_data_path != None and os.path.basename(helpRequest_data_path) == helpRequestDataName:
        raise HTTPException(
            status_code=404, detail=f"Help Request Data: {helpRequestDataName} is already existed.")
    
    rs_models_container_client = ContainerClient.from_connection_string(
        connectionString, model_container_name)
    try:
        rs_models_container_client.get_container_properties()
    except Exception as e:
        # Create the container, if not exist
        rs_models_container_client.create_container()
    
    user_data_container_client = ContainerClient.from_connection_string(
        connectionString, user_data_container_name)
    try:
        user_data_container_client.get_container_properties()
    except Exception as e:
        # Create the container, if not exist
        user_data_container_client.create_container()
        
    helpRequest_data_container_client = ContainerClient.from_connection_string(
        connectionString, helpRequest_data_container_name)
    try:
        helpRequest_data_container_client.get_container_properties()
    except Exception as e:
        # Create the container, if not exist
        helpRequest_data_container_client.create_container()
    
    zipped_model_path = os.path.join('/', 'model', modelName)
    os.makedirs(os.path.dirname(zipped_model_path), exist_ok=True)
    with open(file=zipped_model_path, mode="wb") as sample_blob:
        print(f"Updated model saved at: {zipped_model_path}")
        download_stream = rs_models_container_client.download_blob(modelName)
        sample_blob.write(download_stream.readall())
        
    print('hi updateModel2')
    
    updated_model_dir = os.path.join(os.path.dirname(zipped_model_path), modelName[:-4])
    os.makedirs(updated_model_dir, exist_ok=True)
    with zipfile.ZipFile(zipped_model_path, 'r', zipfile.ZIP_DEFLATED) as archive:
        archive.extractall(updated_model_dir)
        
    os.remove(zipped_model_path)
    
    updated_user_data_path = os.path.join(data_dir, 'user', userDataName)
    os.makedirs(os.path.dirname(updated_user_data_path), exist_ok=True)
    with open(file=updated_user_data_path, mode="wb") as blob:
        print(f"User data saved at: {updated_user_data_path}")
        download_stream = user_data_container_client.download_blob(userDataName)
        blob.write(download_stream.readall())
    
    updated_helpRequest_data_path = os.path.join(data_dir, 'helpRequest', helpRequestDataName)
    os.makedirs(os.path.dirname(updated_helpRequest_data_path), exist_ok=True)
    with open(file=updated_helpRequest_data_path, mode="wb") as blob:
        print(f"helpRequest data saved at: {updated_helpRequest_data_path}")
        download_stream = helpRequest_data_container_client.download_blob(helpRequestDataName)
        blob.write(download_stream.readall())
    
    if model_dir != None:
        if os.path.exists(model_dir):
            shutil.rmtree(model_dir)
    
    if user_data_path != None:
        if os.path.exists(user_data_path):
            os.remove(user_data_path)
    
    if helpRequest_data_path != None:
        if os.path.exists(helpRequest_data_path):
            os.remove(helpRequest_data_path)

    model_dir = updated_model_dir
    user_data_path = updated_user_data_path
    helpRequest_data_path = updated_helpRequest_data_path
    return modelName[:-4]

@app.get("/recommendItem/{userId}")
def recommendItem(userId: str, start: int, end: int) -> List[str]:
    global model_dir
    
    if start is None or end is None:
        raise HTTPException(
            status_code=404, detail=f"Missing start and end query parameters")
        
    if model_dir == None:
        raise HTTPException(
            status_code=404, detail=f"No model exist in fastapi server!.")
    
    userDataframe = pd.read_csv(user_data_path)
    for col in userDataframe:
        #get dtype for column
        dt = userDataframe[col].dtype 
        #check if it is a number
        if dt == int or dt == float:
            userDataframe[col].fillna(0, inplace=True)
        else:
            userDataframe[col].fillna("", inplace=True)
    print(userDataframe)
    if int(userId) not in userDataframe['id'].unique():
        return ["-1"]
    userDataframe = userDataframe.drop(["username", "email","address","city","country","phone","displayName","occupation","dateOfBirth"], axis=1)
    userDataframe = userDataframe.rename(columns={'district': 'userDistrict', 'id': 'userId'})
    print(userDataframe)
    userSeries = userDataframe.loc[(userDataframe['userId'] == int(userId))].reset_index(drop=True).squeeze()
    print(userSeries)
    
    helpRequestDataframe = pd.read_csv(helpRequest_data_path)
    for col in helpRequestDataframe:
        #get dtype for column
        dt = helpRequestDataframe[col].dtype 
        #check if it is a number
        if dt == int or dt == float:
            helpRequestDataframe[col].fillna(0, inplace=True)
        else:
            helpRequestDataframe[col].fillna("", inplace=True)
    helpRequestDataframe = helpRequestDataframe.rename(columns={'district': 'helpRequestDistrict', 'id': 'helpRequestId'})
    isTakenHelpRequestDataframe = helpRequestDataframe[["helpRequestId", "is_taken"]]
    isTakenHelpRequestDataframe['helpRequestId'] = isTakenHelpRequestDataframe['helpRequestId'].astype(object)
    print("isTakenHelpRequestDataframe: ")
    print(isTakenHelpRequestDataframe)
    helpRequestDataframe = helpRequestDataframe.drop(["is_taken"], axis=1)
    
    
    queryDataframe = helpRequestDataframe.merge(pd.DataFrame(data = [userSeries.values] * len(helpRequestDataframe), columns = userSeries.index), left_index=True, right_index=True)
    queryDataframe['userId'] = queryDataframe['userId'].astype(str)
    queryDataframe['helpRequestId'] = queryDataframe['helpRequestId'].astype(str)
    print(queryDataframe.head())
    
    queryDataset = tf.data.Dataset.from_tensors(dict(queryDataframe))
    
    model = tf.keras.models.load_model(model_dir)

    pred_y = []
    for x in queryDataset:
        y = model(x)
        y = y.numpy()[:, 0]
        pred_y.extend(y)
    queryDataframe['actionRate'] = pred_y
    
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1000)
    
    print(queryDataframe)
    queryDataframe = queryDataframe.sort_values(by=['actionRate'], ascending=False)
    queryDataframe = queryDataframe.loc[queryDataframe['actionRate'] >= 2.0]
    # queryDataframe = queryDataframe.merge(isTakenHelpRequestDataframe, how='left', on='helpRequestId')
    queryDataframe = pd.merge(queryDataframe.assign(helpRequestId=queryDataframe.helpRequestId.astype(str)), isTakenHelpRequestDataframe.assign(helpRequestId=isTakenHelpRequestDataframe.helpRequestId.astype(str)), how='left', on='helpRequestId')
    print(queryDataframe)
    print(queryDataframe.dtypes)
    queryDataframe = queryDataframe.loc[queryDataframe['is_taken'] == False]
    
    recommendedHelpRequestsDataframe = queryDataframe['helpRequestId']
    recommendedHelpRequestsDataframe = recommendedHelpRequestsDataframe.reset_index(drop=True)
    recommendedHelpRequestsDataframe = recommendedHelpRequestsDataframe.iloc[start:end]
    recommendedHelpRequestsList = recommendedHelpRequestsDataframe.values.tolist()
    
    return recommendedHelpRequestsList
    
    # return 1

@app.post("/recommendItemForNewUser/")
def recommendItemForNewUser(start: int, end: int, userFeatures: UserFeatures) -> List[str]:
    age = userFeatures.age
    gender = userFeatures.gender
    userDistrict = userFeatures.userDistrict
    
    global model_dir
    
    if start is None or end is None:
        raise HTTPException(
            status_code=404, detail=f"Missing start and end query parameters")
        
    if model_dir == None:
        raise HTTPException(
            status_code=404, detail=f"No model exist in fastapi server!.")
        
    if age == None or gender == None or userDistrict == None:
        raise HTTPException(
            status_code=404, detail=f"age or gender or userDistrict can't be None.")
    
    user = {'userId': 0, 'userDistrict': userDistrict, 'gender': gender, 'age': age}
    userSeries = pd.Series(data=user, index=['userId', 'userDistrict', 'gender', 'age'])
    print(userSeries)
    
    helpRequestDataframe = pd.read_csv(helpRequest_data_path)
    for col in helpRequestDataframe:
        #get dtype for column
        dt = helpRequestDataframe[col].dtype 
        #check if it is a number
        if dt == int or dt == float:
            helpRequestDataframe[col].fillna(0, inplace=True)
        else:
            helpRequestDataframe[col].fillna("", inplace=True)
    helpRequestDataframe = helpRequestDataframe.rename(columns={'district': 'helpRequestDistrict', 'id': 'helpRequestId'})
    isTakenHelpRequestDataframe = helpRequestDataframe[["helpRequestId", "is_taken"]]
    isTakenHelpRequestDataframe['helpRequestId'] = isTakenHelpRequestDataframe['helpRequestId'].astype(object)
    print("isTakenHelpRequestDataframe: ")
    print(isTakenHelpRequestDataframe)
    helpRequestDataframe = helpRequestDataframe.drop(["is_taken"], axis=1)
    
    queryDataframe = helpRequestDataframe.merge(pd.DataFrame(data = [userSeries.values] * len(helpRequestDataframe), columns = userSeries.index), left_index=True, right_index=True)
    queryDataframe['userId'] = queryDataframe['userId'].astype(str)
    queryDataframe['helpRequestId'] = queryDataframe['helpRequestId'].astype(str)
    print(queryDataframe.head())
    
    queryDataset = tf.data.Dataset.from_tensors(dict(queryDataframe))
    
    model = tf.keras.models.load_model(model_dir)

    pred_y = []
    for x in queryDataset:
        y = model(x)
        y = y.numpy()[:, 0]
        pred_y.extend(y)
    queryDataframe['actionRate'] = pred_y
    
    pd.set_option('display.max_rows', 500)
    pd.set_option('display.max_columns', 500)
    pd.set_option('display.width', 1000)
    
    queryDataframe = queryDataframe.sort_values(by=['actionRate'], ascending=False)
    queryDataframe = queryDataframe.loc[queryDataframe['actionRate'] >= 2.0]
    queryDataframe = pd.merge(queryDataframe.assign(helpRequestId=queryDataframe.helpRequestId.astype(str)), isTakenHelpRequestDataframe.assign(helpRequestId=isTakenHelpRequestDataframe.helpRequestId.astype(str)), how='left', on='helpRequestId')
    queryDataframe = queryDataframe.loc[queryDataframe['is_taken'] == False]
    
    recommendedHelpRequestsDataframe = queryDataframe['helpRequestId']
    recommendedHelpRequestsDataframe = recommendedHelpRequestsDataframe.reset_index(drop=True)
    recommendedHelpRequestsDataframe = recommendedHelpRequestsDataframe.iloc[start:end]
    recommendedHelpRequestsList = recommendedHelpRequestsDataframe.values.tolist()
    
    return recommendedHelpRequestsList

@app.get("/modelVersion/")
def modelVersion() -> str:
    if model_dir == None:
        raise HTTPException(
            status_code=404, detail=f"No model exist in fastapi server!.")
    
    return os.path.basename(model_dir)

# docker build -t myimage .
# docker run --gpus all -d --name mycontainer -p 80:80 myimage
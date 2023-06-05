import pandas as pd
import tensorflow as tf
import numpy as np
from model import build_model
import time
import uuid
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import zipfile
import os
import matplotlib.pyplot as plt
from datetime import datetime

connectionString = "DefaultEndpointsProtocol=https;AccountName=communityhelperstudentea;AccountKey=EwWwuGer7cUwdCwBiyvrenVNqi4RSvgnWzfAhFTtHEBcBg/eIjBjLoYo/1U8n7eiiEUvX0gjnD/t+ASt2ncvPQ==;EndpointSuffix=core.windows.net"
data_dir = os.path.join('..', 'data')

linear_inputs_features = ['userId', 'helpRequestId', 'userDistrict', 'gender', 
                          'category', 'title', 'description', 'helpRequestDistrict']

inputs_features = ['age', 'price', 'userId', 'helpRequestId', 'userDistrict', 
                   'gender', 'userInterest','category', 'title', 'description', 'helpRequestDistrict']

def train_model(model, dataset, testset):
    version = int(time.time())
    history = model.fit(dataset, epochs=4000, validation_data=testset, 
              callbacks=[tf.keras.callbacks.EarlyStopping(start_from_epoch=200, patience=50)])
    print(model.summary())
    model.save('model/{}'.format(version), save_format='tf', include_optimizer=False)
    plt.plot(history.epoch[::10], history.history["loss"][::10], 'g', label='Training loss')
    plt.plot(history.epoch[::10], history.history["val_loss"][::10], 'r', label='Validation loss')
    plt.title('Training & Validation loss')
    plt.xlabel('Epochs')
    plt.ylabel('MAE Loss')
    plt.legend()
    plt.savefig('TrainingLoss.png')
    return version

dataset_name = os.getenv('dataset_name')
print(dataset_name)

# Fetch dataset from blob
# Create the ContainerClient object
dataset_container_client = \
    ContainerClient.from_connection_string(connectionString, 'dataset')

trainDataset_name = 'trainDataset.csv'
trainDataset_path = os.path.join(data_dir, trainDataset_name)
with open(file=trainDataset_path, mode="wb") as blob:
    print(f"User data saved at: {trainDataset_path}")
    download_stream = dataset_container_client.download_blob(dataset_name)
    blob.write(download_stream.readall())



datasetDataFrame = pd.read_csv(trainDataset_path)
for col in datasetDataFrame:
    #get dtype for column
    dt = datasetDataFrame[col].dtype 
    #check if it is a number
    if dt == int or dt == float:
        datasetDataFrame[col].fillna(0, inplace=True)
    else:
        datasetDataFrame[col].fillna("", inplace=True)
msk = np.random.rand(len(datasetDataFrame)) < 0.8
trainDataFrame = datasetDataFrame[msk]
testDataFrame = datasetDataFrame[~msk]
myTrainDataset = tf.data.Dataset.from_tensors((dict(trainDataFrame[inputs_features]), trainDataFrame[['actionRate']]))
myTestDataset = tf.data.Dataset.from_tensors((dict(testDataFrame[inputs_features]), testDataFrame[['actionRate']]))

# create wide&deep model
wide_deep_model = build_model()
# start train
print(f"pd dtype: {datasetDataFrame.dtypes}")
version = train_model(wide_deep_model, myTrainDataset, myTestDataset)

model_path = os.path.join('model', str(version))
print(f"model_path: {model_path}")

print("Azure Blob Storage Python quickstart sample")

with zipfile.ZipFile(f"{str(model_path)}.zip", 'w', zipfile.ZIP_DEFLATED) as archive:
    for root, dirs, files in os.walk(str(model_path)):
        for file_name in files:
            print(os.path.join(root, file_name))
            archive.write(os.path.join(root, file_name), 
                          os.path.relpath(os.path.join(root, file_name), str(model_path))
                          )

# # Create a unique name for the container
model_container_name = "rs-models"
loss_graph_container_name = "loss-graphs"

# Create the ContainerClient object
rs_models_container_client = \
    ContainerClient.from_connection_string(connectionString, model_container_name)
    
loss_graph_container_client = \
    ContainerClient.from_connection_string(connectionString, loss_graph_container_name)

try:
    rs_models_container_client.get_container_properties()
except Exception as e:
    # Create the container "rs-models", if not exist
    rs_models_container_client.create_container()

try:
    loss_graph_container_client.get_container_properties()
except Exception as e:
    # Create the container "rs-models", if not exist
    loss_graph_container_client.create_container()

print("\nUploading the models to Azure Storage as blob:\n\t" + str(model_path))

model_version = str(datetime.now().strftime("%d%m%Y_%H%M%S"))
zipped_model_name = model_version+".zip"
# Upload the created file
with open(file=f"{str(model_path)}.zip", mode="rb") as data:
    rs_models_container_client.upload_blob(name=zipped_model_name, data=data)
    
with open(file='TrainingLoss.png', mode="rb") as data:
    loss_graph_container_client.upload_blob(name=model_version+'_TrainingLoss.png', data=data)

print(dict(zipped_model_name=zipped_model_name))

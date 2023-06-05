# Set-up guide
## Pre-requisite
### Windows user
- docker for windows
- WSL (optional)
- Nvidia GPU (supported cuda)
- nvidia-container-runtime (not sure whether really need this, you can try without this package first)
- cuda tool kit
### Mac and Linux user
Did not test, but should be similar to Windows 

---
## Step 1
Clone this repo to your local machine 
```
git clone https://github.com/FYP-Community-Helpers-Organization/RecommenderSystem.git
```
## Step 2
Build our Recommender System image
```
cd RecommenderSystem_docker
```
```
docker build -t recommenders:gpu .
```
## Step 3
Build and start our fast api server
```
cd ..
cd fastapi
```
```
docker build -t myimage .
docker run --gpus all -d --name mycontainer -p 80:80 myimage
```
Fast api server url: `http://localhost:80/`
## Step 4
Start Azurite  
> The Azurite open-source emulator provides a free local environment for testing your Azure Blob, Queue Storage, and Table Storage applications. When you're satisfied with how your application is working locally, switch to using an Azure Storage account in the cloud. The emulator provides cross-platform support on Windows, Linux, and macOS.  

ref guide: https://learn.microsoft.com/en-us/azure/storage/common/storage-use-azurite?tabs=visual-studio

Recommend to use Visual Studio Code extension, since it seem to be the easiest way to use Azurite  
> Of course, you can just use a ***REAL*** Azure Blob storage  

**Note: Your might need to edit the connection string of the blob storage**  
## Step 5
Build our Airflow image
```
cd ..
cd airflow_docker
```
```
docker build . --tag extanding_airflow:latest
```
## Step 6
Start our Airflow container
```
docker compose up -d
```
## Step 7
Open your browser and go to `http://localhost:8080/` \
You should able to see the login page of Airflow
## Step 8
Login to Airflow, default Username and password is, 
- Username: Airflow
- Password: Airflow
## Step 9
**Please be aware of the env var and connection, you might need to config it by your self**  
Now you had already started up the whole RS. \
If you found any problem, please contact Woody.

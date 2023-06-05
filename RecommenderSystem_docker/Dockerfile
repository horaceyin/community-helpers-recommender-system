FROM tensorflow/tensorflow:latest-gpu

ARG HOME="/root"
WORKDIR ${HOME}   
  
# COPY ./test.py test.py
# COPY ./train.py train.py
COPY ./src ./src
COPY ./data ./data
COPY requirements.txt /requirements.txt
RUN pip install --user --upgrade pip
RUN pip install --no-cache-dir --user -r /requirements.txt

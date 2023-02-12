## pull official base image
#FROM python:3.10
From registry.tech1a.co:81/repository/tech1a-docker-registry/python/python:3.9

# set working directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install system dependencies
RUN apt-get update \
  && apt-get -y install netcat iputils-ping net-tools gcc nano \
  && apt-get clean

# install python dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt .
RUN pip install -r requirements.txt

# add app
COPY . .
#CMD python customer.py
#CMD python firm.py
#CMD python trades.py

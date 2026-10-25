## pull official base image
FROM python:3.13.6-alpine

# set working directory
WORKDIR /usr/src/app

# set environment variables
ENV TZ=Asia/Tehran
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

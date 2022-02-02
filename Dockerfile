FROM python:3.9
ENV PYTHONUNBUFFERED 1
MAINTAINER Igor Rudenko <ig.rudenko1@yandex.ru>

WORKDIR /home/django
COPY . .

RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

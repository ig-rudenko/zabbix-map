#!/bin/bash
python manage.py makemigrations;
python manage.py migrate;
python manage.py makemigrations zabbix_visual_map;
python manage.py migrate zabbix_visual_map;
if [ "$DJANGO_SUPERUSER_NAME" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ];
  then
    python manage.py createsuperuser --username "$DJANGO_SUPERUSER_NAME" --noinput --email "$DJANGO_SUPERUSER_EMAIL" || true ; echo $?;
  else
    python manage.py createsuperuser --username root --noinput --email root@example.com || true ; echo $?;
fi
python manage.py runserver 0.0.0.0:8000;
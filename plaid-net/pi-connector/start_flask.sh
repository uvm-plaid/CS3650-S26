#!/bin/bash

echo $HOSTNAME

export FLASK_APP=/home/pi/pi-switch-flask/app.py
flask run --host=0.0.0.0 --port=1142 &

#python3 /home/pi/pi-switch-flask/app.py & > log.txt

echo "started"

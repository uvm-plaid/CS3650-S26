from flask import Flask
from RPi import GPIO
import os

app = Flask(__name__)


@app.route("/red_light_on")
def red_light_on():
    os.system("echo 1 | tee /sys/class/leds/led1/brightness")
    return "ok"


@app.route("/red_light_off")
def red_light_off():
    os.system("echo 0 | tee /sys/class/leds/led1/brightness")
    return "ok"


@app.route("/green_light_on")
def green_light_on():
    os.system("echo 1 | tee /sys/class/leds/led0/brightness")
    return "ok"


@app.route("/green_light_off")
def green_light_off():
    os.system("echo 0 | tee /sys/class/leds/led0/brightness")
    return "ok"


if __name__ == '__main__':
    app.run()

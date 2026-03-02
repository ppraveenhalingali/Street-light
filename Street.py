from flask import Flask, render_template
import RPi.GPIO as GPIO
import spidev
import time

app = Flask(__name__)

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# ---------------- GPIO PINS ----------------
street_leds = [17, 18, 22, 23]
ir_pin = 24
red_lights = [25, 5]
green_lights = [6, 12]

# Setup LEDs
for pin in street_leds + red_lights + green_lights:
    GPIO.setup(pin, GPIO.OUT)

GPIO.setup(ir_pin, GPIO.IN)

# PWM Setup
pwms = []
for pin in street_leds:
    pwm = GPIO.PWM(pin, 1000)
    pwm.start(0)
    pwms.append(pwm)

# ---------------- MCP3008 SPI Setup ----------------
spi = spidev.SpiDev()
spi.open(0, 0)   # Bus 0, Device 0
spi.max_speed_hz = 1350000

def read_adc(channel):
    adc = spi.xfer2([1, (8 + channel) << 4, 0])
    data = ((adc[1] & 3) << 8) + adc[2]
    return data  # 0–1023

traffic_state = "OFF"

@app.route('/')
def home():
    global traffic_state

    ldr_value = read_adc(0)  # CH0
    ir_status = GPIO.input(ir_pin)

    street_status = "OFF"

    # Night condition (adjust threshold if needed)
    if ldr_value < 400:
        street_status = "ON (50%)"
        for pwm in pwms:
            pwm.ChangeDutyCycle(50)

        if ir_status == 1:
            street_status = "ON (100%)"
            for pwm in pwms:
                pwm.ChangeDutyCycle(100)
    else:
        for pwm in pwms:
            pwm.ChangeDutyCycle(0)
        street_status = "OFF"

    return render_template("index.html",
                           ldr=ldr_value,
                           ir=ir_status,
                           street=street_status,
                           traffic=traffic_state)

@app.route('/traffic/<state>')
def traffic_control(state):
    global traffic_state

    if state == "red":
        traffic_state = "RED ON"
        for r in red_lights:
            GPIO.output(r, GPIO.HIGH)
        for g in green_lights:
            GPIO.output(g, GPIO.LOW)

    elif state == "green":
        traffic_state = "GREEN ON"
        for g in green_lights:
            GPIO.output(g, GPIO.HIGH)
        for r in red_lights:
            GPIO.output(r, GPIO.LOW)

    elif state == "off":
        traffic_state = "OFF"
        for r in red_lights:
            GPIO.output(r, GPIO.LOW)
        for g in green_lights:
            GPIO.output(g, GPIO.LOW)

    return home()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)



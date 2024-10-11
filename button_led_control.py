import RPi.GPIO as GPIO
import time

# Pin definitions
BUTTON_PIN_1 = 23  # Button 1 connected to GPIO 23
BUTTON_PIN_2 = 24  # Button 2 connected to GPIO 24
LED_PIN = 12       # Green LED connected to GPIO 12
LED_BLUE = 6       # Blue LED connected to GPIO 6

# Setup GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_PIN_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(LED_BLUE, GPIO.OUT)

def perform_action(button_number):
    """Function to perform action based on button pressed."""
    if button_number == 1:
        print("Button 1 pressed!")
        GPIO.output(LED_BLUE, GPIO.HIGH)  # Turn on blue LED for action
        time.sleep(1)                     # Simulate action duration
        GPIO.output(LED_BLUE, GPIO.LOW)   # Turn off blue LED
    elif button_number == 2:
        print("Button 2 pressed!")
        GPIO.output(LED_BLUE, GPIO.HIGH)  # Turn on blue LED for action
        time.sleep(1)                     # Simulate action duration
        GPIO.output(LED_BLUE, GPIO.LOW)   # Turn off blue LED

try:
    while True:
        # Indicate waiting state by blinking the green LED
        GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on green LED
        time.sleep(0.5)                  # Keep it on for 0.5 seconds
        GPIO.output(LED_PIN, GPIO.LOW)   # Turn off green LED
        time.sleep(0.5)                  # Keep it off for 0.5 seconds

        # Check Button 1
        if GPIO.input(BUTTON_PIN_1) == GPIO.LOW:  # Button pressed
            GPIO.output(LED_PIN, GPIO.LOW)  # Turn off green LED during action
            perform_action(1)
            while GPIO.input(BUTTON_PIN_1) == GPIO.LOW:  # Wait for button release
                time.sleep(0.1)

        # Check Button 2
        if GPIO.input(BUTTON_PIN_2) == GPIO.LOW:  # Button pressed
            GPIO.output(LED_PIN, GPIO.LOW)  # Turn off green LED during action
            perform_action(2)
            while GPIO.input(BUTTON_PIN_2) == GPIO.LOW:  # Wait for button release
                time.sleep(0.1)

except KeyboardInterrupt:
    print("Program terminated.")
finally:
    GPIO.output(LED_PIN, GPIO.LOW)  # Ensure green LED is off on exit
    GPIO.cleanup()  # Clean up GPIO on exit

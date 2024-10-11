import subprocess
import time
import sys
import bluetooth  # Ensure you have pybluez installed to use this library
import RPi.GPIO as GPIO  # Import RPi.GPIO library

# Set up GPIO
LED_PIN = 18          # GPIO pin for the LED
BUTTON_PIN_23 = 23    # GPIO pin for button to turn on the A9G module
BUTTON_PIN_24 = 24    # GPIO pin for button to turn on Bluetooth

# Initialize GPIO
GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
GPIO.setup(LED_PIN, GPIO.OUT)  # Set LED pin as an output
GPIO.setup(BUTTON_PIN_23, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button input with pull-up resistor
GPIO.setup(BUTTON_PIN_24, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button input with pull-up resistor

def main():
    print("Waiting for button press to trigger Bluetooth initialization...")

    try:
        while True:
            # Debug statement to monitor button states
            print(f"Button 23 state: {GPIO.input(BUTTON_PIN_23)}, Button 24 state: {GPIO.input(BUTTON_PIN_24)}")

            # Check if button on GPIO 24 is pressed for Bluetooth initialization
            if GPIO.input(BUTTON_PIN_24) == GPIO.LOW:  # LOW indicates button press in pull-up configuration
                print("Button on GPIO 24 pressed. Starting Bluetooth initialization...")
                break  # Handle Bluetooth logic here

            # Check if button on GPIO 23 is pressed for A9G module
            if GPIO.input(BUTTON_PIN_23) == GPIO.LOW:  # LOW indicates button press in pull-up configuration
                print("Button on GPIO 23 pressed. Turning on A9G module...")
                break  # Handle A9G module logic here

            time.sleep(0.1)  # Polling delay to avoid high CPU usage

    except KeyboardInterrupt:
        print("\nExiting...")

    finally:
        GPIO.cleanup()  # Cleanup GPIO settings

if __name__ == "__main__":
    main()

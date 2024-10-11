import RPi.GPIO as GPIO
import time

# Define GPIO pins
BUTTON_PIN_1 = 23  # Button 1 connected to GPIO 23 (Bluetooth)
BUTTON_PIN_2 = 24  # Button 2 connected to GPIO 24 (A9G Module)
LED_PIN = 12       # Green LED connected to GPIO 12
LED_BLUE = 6       # Blue LED connected to GPIO 6

def setup_gpio():
    """Set up GPIO pins."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button 1 as input with pull-up
    GPIO.setup(BUTTON_PIN_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button 2 as input with pull-up
    GPIO.setup(LED_PIN, GPIO.OUT)                                 # Green LED as output
    GPIO.setup(LED_BLUE, GPIO.OUT)                               # Blue LED as output

def detect_button_presses():
    """Detect button presses and handle actions."""
    while True:
        # Check for button press on BUTTON_PIN_1
        if GPIO.input(BUTTON_PIN_1) == GPIO.LOW:
            print("Button 1 pressed! Initiating Bluetooth connection...")
            GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on green LED
            time.sleep(1)  # Delay to avoid multiple triggers
            GPIO.output(LED_PIN, GPIO.LOW)   # Turn off green LED
            # Add Bluetooth connection logic here

        # Check for button press on BUTTON_PIN_2
        if GPIO.input(BUTTON_PIN_2) == GPIO.LOW:
            print("Button 2 pressed! Initiating A9G module action...")
            GPIO.output(LED_BLUE, GPIO.HIGH)  # Turn on blue LED
            time.sleep(1)  # Delay to avoid multiple triggers
            GPIO.output(LED_BLUE, GPIO.LOW)   # Turn off blue LED
            # Add A9G module logic here

        time.sleep(0.1)  # Small delay to prevent CPU overload

def main():
    """Main function to initialize the button detection."""
    try:
        GPIO.setwarnings(False)  # Disable warnings
        GPIO.cleanup()           # Clean up GPIO settings
        setup_gpio()             # Set up GPIO pins
        print("System is ready, waiting for button press...")
        detect_button_presses()  # Start detecting button presses
    except KeyboardInterrupt:
        print("Program stopped by user.")
    finally:
        GPIO.cleanup()  # Clean up GPIO settings

if __name__ == "__main__":
    main()

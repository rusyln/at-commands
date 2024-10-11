import RPi.GPIO as GPIO
import time
import serial

# Set up the GPIO using BCM numbering
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)  # Suppress GPIO warnings

# Define the GPIO pins
BUTTON_PIN = 23  # Button connected to GPIO 23
A9G_PIN = 17     # A9G module control pin (PWR_KEY)

# Set up GPIO pins
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button input
GPIO.setup(A9G_PIN, GPIO.OUT)  # A9G control pin as output

# Function to turn on the A9G module
def turn_on_a9g():
    print("Turning on A9G module...")
    GPIO.output(A9G_PIN, GPIO.HIGH)  # Set the pin high to turn on the A9G module
    time.sleep(2)  # Keep it on for 2 seconds (adjust as needed)
    GPIO.output(A9G_PIN, GPIO.LOW)  # Set the pin low to turn off the A9G module
    print("A9G module powered on.")

# Function to send AT command
def send_at_command(command):
    # Open the serial port
    ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=1)  # Use /dev/serial0
    time.sleep(2)  # Wait for the serial connection to initialize
    ser.write((command + '\r\n').encode('utf-8'))  # Send the command
    time.sleep(1)  # Wait for a response
    response = ser.read(ser.inWaiting()).decode('utf-8')  # Read the response
    ser.close()  # Close the serial port
    return response

print("Waiting for button press to turn on A9G module and send AT command...")

try:
    while True:
        # Check if the button is pressed
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
            print("Button pressed!")
           

            time.sleep(0.5)  # Debounce delay to avoid multiple triggers

except KeyboardInterrupt:
    print("Script interrupted by user")

finally:
    # Clean up GPIO settings before exiting
    GPIO.cleanup()
    print("GPIO cleanup completed")

import RPi.GPIO as GPIO
import time
import serial
import subprocess
import sys
import random
import threading
import bluetooth

# Set up the GPIO using BCM numbering
GPIO.setmode(GPIO.BCM)
print("GPIO mode set to BCM")  # Debugging line to confirm mode is set
GPIO.setwarnings(False)  # Suppress GPIO warnings

# Define the GPIO pins
BUTTON_PIN_1 = 23  # Button 1 connected to GPIO 23
BUTTON_PIN_2 = 24  # Button 2 connected to GPIO 24 (Add more as needed)
A9G_PIN = 17       # A9G module control pin (PWR_KEY)
LED_PIN = 12       # Green LED connected to GPIO 12
LED_BLUE = 6       # Blue LED connected 

# Global variable to control the blinking
blinking = False

# Set up GPIO pins
GPIO.setup(BUTTON_PIN_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button 1 input
GPIO.setup(BUTTON_PIN_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button 2 input
GPIO.setup(A9G_PIN, GPIO.OUT)  # A9G control pin as output
GPIO.setup(LED_PIN, GPIO.OUT)  # LED as output
GPIO.setup(LED_BLUE, GPIO.OUT)  # LED as output

# Turn on the LED initially to indicate waiting state
GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on the LED
print("Green LED is ON while waiting for button press.")

# Global variable to control the RFCOMM server restart
rfcomm_should_restart = True


def blink_led(led_pin):
    """Blink the LED at a regular interval."""
    while blinking:
        GPIO.output(led_pin, GPIO.HIGH)
        time.sleep(0.5)  # LED ON for 0.5 seconds
        GPIO.output(led_pin, GPIO.LOW)
        time.sleep(0.5)  # LED OFF for 0.5 seconds

def start_rfcomm_server():
    """Start RFCOMM server on channel 24."""
    global rfcomm_should_restart  # Ensure we are using the global variable
    server_sock = None
    client_sock = None
    channel = 24  # Fixed RFCOMM channel

    while rfcomm_should_restart:  # Loop to keep the server running based on the restart condition
        print("Starting RFCOMM server...")

        # Create a Bluetooth socket
        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)

        try:
            server_sock.bind(("", channel))
            server_sock.listen(1)
            print(f"Listening for connections on RFCOMM channel {channel}...")

            client_sock, address = server_sock.accept()
            # Stop blinking and turn on the blue LED steadily
            global blinking  # Ensure we are using the global variable
            blinking = False  # Stop the blinking loop
            
            GPIO.output(LED_BLUE, GPIO.HIGH)  # Keep the blue LED on
            print("Connection established with:", address)

            while True:
                recvdata = client_sock.recv(1024).decode('utf-8').strip()  # Decode bytes to string and strip whitespace
                print("Received command:", recvdata)

                if recvdata.lower() == "q" or recvdata.lower() == "socket close":
                    print("Ending connection.")
                    rfcomm_should_restart = False  # Prevent the server from restarting automatically
                    break  # Break from the inner while loop to close the client socket

                # Execute the command received from the Android device
                response = run_raspberry_pi_command(recvdata)

                # Send the response back to the Android device
                if response:
                    client_sock.send(f"Command executed successfully:\n{response}".encode('utf-8'))
                else:
                    client_sock.send("Command execution failed or produced no output.".encode('utf-8'))

        except bluetooth.btcommon.BluetoothError as e:
            if e.errno == 98:  # Address already in use
                print("Bluetooth error: Address already in use. Please ensure sdptool has the correct channel set.")
                time.sleep(1)  # Sleep for a bit before retrying
                continue  # Retry binding to the same port
            else:
                print("Bluetooth error:", e)
                time.sleep(1)

        except OSError as e:
            print("OS error:", e)
            time.sleep(1)

        finally:
            # Ensure sockets are closed
            if client_sock:
                client_sock.close()
                print("Client socket closed.")
            if server_sock:
                server_sock.close()
                print("Server socket closed.")

            # Indicate readiness to accept new connections
            if rfcomm_should_restart:  # Only set this to True if we want to restart the server
                print("Waiting for button press to turn on A9G module and send AT command...")
                time.sleep(1)  # Add a slight delay to avoid rapid retrying
            else:
                print("RFCOMM server will not restart. Waiting for button press.")

def turn_on_a9g():
    print("Turning on A9G module...")
    GPIO.output(A9G_PIN, GPIO.HIGH)  # Set the pin high to turn on the A9G module
    time.sleep(2)  # Keep it on for 2 seconds (adjust as needed)
    GPIO.output(A9G_PIN, GPIO.LOW)  # Set the pin low to turn off the A9G module
    print("A9G module powered on.")

def run_bluetoothctl():
    """Start bluetoothctl as a subprocess and return the process handle."""
    return subprocess.Popen(
        ['bluetoothctl'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # Line-buffered
    )

def run_raspberry_pi_command(command):
    """Run a command on Raspberry Pi."""
    try:
        output = subprocess.check_output(command, shell=True, text=True)
        print("Command output:", output)
        return output
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}\nOutput: {e.output}")

def run_command(process, command):
    """Run a command in bluetoothctl."""
    if process.poll() is None:  # Check if the process is still running
        print(f"Running command: {command}")
        process.stdin.write(command + '\n')
        process.stdin.flush()
        time.sleep(1)  # Allow some time for processing
    else:
        print(f"Process is not running. Unable to execute command: {command}")

def start_bluetooth():
    """Start Bluetooth functionality."""
    # Start bluetoothctl
    process = run_bluetoothctl()

    # Power on the Bluetooth adapter
    print("Powering on the Bluetooth adapter...")
    run_command(process, "power on")

    # Make the device discoverable
    print("Making device discoverable...")
    run_command(process, "discoverable on")

    # Enable the agent
    print("Enabling agent...")
    run_command(process, "agent on")

    # Set as default agent
    print("Setting default agent...")
    run_command(process, "default-agent")

    # Start device discovery
    print("Starting device discovery...")
    run_command(process, "scan on")

    try:
        print("Waiting for a device to connect...")
        countdown_started = False
        countdown_duration = 10  # 10 seconds countdown
        start_time = None

        while True:
            # Read output continuously
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break  # Exit loop if the process is terminated
            if output:
                print(f"Output: {output.strip()}")

                # Check for the passkey confirmation prompt
                if "Confirm passkey" in output:
                    print("Responding 'yes' to passkey confirmation...")
                    run_command(process, "yes")

                # Check for authorization service prompt
                if "[agent] Authorize service" in output:
                    print("Responding 'yes' to authorization service...")
                    run_command(process, "yes")
                    countdown_started = False  # Stop countdown if service is authorized
                    
                # Check for the specific message to start the countdown
                if "Invalid command in menu main:" in output:
                    print("Received 'Invalid command in menu main:', starting countdown...")
                    countdown_started = True
                    start_time = time.time()

                # Check for Serial Port service registration
                if "Serial Port service registered" in output:
                    print("Serial Port service registered. Waiting for 5 seconds...")
                    time.sleep(5)  # Wait for 5 seconds
                    #start_rfcomm_server()  # Start the RFCOMM server
                    # Do not break, continue listening for other output

            # Show countdown if it has been started
            if countdown_started:
                elapsed_time = time.time() - start_time
                remaining_time = countdown_duration - int(elapsed_time)
                if remaining_time > 0:
                    sys.stdout.write(f"\rWaiting for {remaining_time} seconds...")
                    sys.stdout.flush()
                else:
                    print("\nCountdown expired. Continuing to check for output...")

    except KeyboardInterrupt:
        print("Process interrupted by user.")
    finally:
        process.terminate()  # Ensure subprocess is terminated

# Event handlers for button presses
def button_1_pressed(channel):
    print("Button 1 pressed! Starting A9G module and RFCOMM server...")
    turn_on_a9g()  # Turn on the A9G module
    start_rfcomm_server()  # Start the RFCOMM server

def button_2_pressed(channel):
    print("Button 2 pressed! Restarting the RFCOMM server...")
    global rfcomm_should_restart
    rfcomm_should_restart = True
    start_rfcomm_server()  # Start the RFCOMM server

# Add event detection for buttons
GPIO.add_event_detect(BUTTON_PIN_1, GPIO.FALLING, callback=button_1_pressed, bouncetime=300)
GPIO.add_event_detect(BUTTON_PIN_2, GPIO.FALLING, callback=button_2_pressed, bouncetime=300)

try:
    start_bluetooth()  # Start Bluetooth functionality
except KeyboardInterrupt:
    print("Program interrupted by user.")
finally:
    GPIO.cleanup()  # Clean up GPIO pins
    print("GPIO cleanup completed.")

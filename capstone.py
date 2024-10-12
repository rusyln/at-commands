import RPi.GPIO as GPIO
import time
import subprocess
import sys
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

def blink_led(led_pin):
    """Blink the LED at a regular interval."""
    while blinking:
        GPIO.output(led_pin, GPIO.HIGH)
        time.sleep(0.5)  # LED ON for 0.5 seconds
        GPIO.output(led_pin, GPIO.LOW)
        time.sleep(0.5)  # LED OFF for 0.5 seconds

def start_rfcomm_server():
    """Start RFCOMM server on channel 24."""
    server_sock = None
    client_sock = None
    channel = 24  # Fixed RFCOMM channel

    while True:  # Loop to keep the server running
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
            print("Waiting for button press to turn on A9G module and send AT command...")
            time.sleep(1)  # Add a slight delay to avoid rapid retrying

def turn_on_a9g():
    print("Turning on A9G module...")
    GPIO.output(A9G_PIN, GPIO.HIGH)  # Set the pin high to turn on the A9G module
    time.sleep(2)  # Keep it on for 2 seconds (adjust as needed)
    GPIO.output(A9G_PIN, GPIO.LOW)  # Set the pin low to turn off the A9G module
    print("A9G module powered on.")

def run_raspberry_pi_command(command):
    """Run a command on Raspberry Pi."""
    try:
        output = subprocess.check_output(command, shell=True, text=True)
        print("Command output:", output)
        return output
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}\nOutput: {e.output}")

def handle_button_1_press():
    """Handle the action for button 1 press."""
    global blinking
    print("Button 1 pressed: Initiating Bluetooth sequence...")

    GPIO.output(LED_PIN, GPIO.LOW)  # Turn off the green LED when button 1 is pressed
    blinking = True
    blink_thread = threading.Thread(target=blink_led, args=(LED_BLUE,))
    blink_thread.start()

    start_rfcomm_server()

def handle_button_2_press():
    """Handle the action for button 2 press."""
    print("Button 2 pressed: Turning on the A9G module...")
    turn_on_a9g()

def main():
    """Main function to monitor button presses and initiate actions."""
    print("Waiting for button press to trigger actions...")
    try:
        while True:
            if GPIO.input(BUTTON_PIN_1) == GPIO.LOW:
                handle_button_1_press()
                time.sleep(0.5)  # Debounce delay

            if GPIO.input(BUTTON_PIN_2) == GPIO.LOW:
                handle_button_2_press()
                time.sleep(0.5)  # Debounce delay

    except KeyboardInterrupt:
        print("Script interrupted by user")

    finally:
        GPIO.cleanup()
        print("GPIO cleanup completed")

# Entry point for the script
if __name__ == "__main__":
    main()

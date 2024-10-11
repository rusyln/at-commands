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
GPIO.setup(BUTTON_PIN_23, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Button input with pull-down resistor
GPIO.setup(BUTTON_PIN_24, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Button input with pull-down resistor

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

def run_command(process, command):
    """Run a command in bluetoothctl."""
    if process.poll() is None:  # Check if the process is still running
        print(f"Running command: {command}")
        process.stdin.write(command + '\n')
        process.stdin.flush()
        time.sleep(1)  # Allow some time for processing
    else:
        print(f"Process is not running. Unable to execute command: {command}")

def start_rfcomm_server():
    """Start RFCOMM server on channel 24."""
    print("Starting RFCOMM server on channel 24...")

    # Create a Bluetooth socket
    server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
    port = 24
    server_sock.bind(("", port))
    server_sock.listen(1)

    print(f"Listening for connections on RFCOMM channel {port}...")

    try:
        client_sock, address = server_sock.accept()
        print("Connection established with:", address)

        while True:
            recvdata = client_sock.recv(1024).decode('utf-8').strip()  # Decode bytes to string and strip whitespace
            print("Received command:", recvdata)

            if recvdata == "Q":
                print("Ending connection.")
                break
            if recvdata == "socket close":
                print("Ending connection.")
                server_sock.close()
                break   

            if recvdata == "stop led":
                print("Turning off the LED.")
                GPIO.output(LED_PIN, GPIO.LOW)  # Turn off the LED
                continue

            # Execute the received command
            try:
                output = subprocess.check_output(recvdata, shell=True, text=True)
                print("Command output:", output)  # Print command output for debugging
                client_sock.send(output.encode('utf-8'))  # Send the output back to the client
            except subprocess.CalledProcessError as e:
                error_message = f"Error executing command: {e}\nOutput: {e.output}"
                print("Error:", error_message)  # Print the error for debugging
                client_sock.send(error_message.encode('utf-8'))  # Send error message back to client

    except OSError as e:
        print("Error:", e)

    finally:
        client_sock.close()
        server_sock.close()
        print("Sockets closed.")

def main():
    print("Waiting for button press to trigger Bluetooth initialization...")

    try:
        while True:
            # Debug statement to monitor button states
            print(f"Button 23 state: {GPIO.input(BUTTON_PIN_23)}, Button 24 state: {GPIO.input(BUTTON_PIN_24)}")

            # Check if button on GPIO 24 is pressed for Bluetooth initialization
            if GPIO.input(BUTTON_PIN_24) == GPIO.HIGH:
                print("Button on GPIO 24 pressed. Starting Bluetooth initialization...")

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

                # Start the RFCOMM server
                start_rfcomm_server()

                break  # Exit loop once Bluetooth logic is handled

            # Check if button on GPIO 23 is pressed for A9G module
            if GPIO.input(BUTTON_PIN_23) == GPIO.HIGH:
                print("Button on GPIO 23 pressed. Turning on A9G module...")

            time.sleep(0.1)  # Polling delay to avoid high CPU usage

    except KeyboardInterrupt:
        print("\nExiting...")

    finally:
        GPIO.cleanup()  # Cleanup GPIO settings

if __name__ == "__main__":
    main()

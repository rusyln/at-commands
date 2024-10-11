import RPi.GPIO as GPIO
import time
import serial
import subprocess
import sys
import bluetooth

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
                # Run the command using subprocess
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

def run_raspberry_pi_command(command):
    """Run a command on Raspberry Pi."""
    try:
        output = subprocess.check_output(command, shell=True, text=True)
        print("Command output:", output)
        return output
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}\nOutput: {e.output}")

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
                    start_rfcomm_server()  # Start the RFCOMM server
                    # Do not break, continue listening for other output

            # Show countdown if it has been started
            if countdown_started:
                elapsed_time = time.time() - start_time
                remaining_time = countdown_duration - int(elapsed_time)
                if remaining_time > 0:
                    sys.stdout.write(f"\rWaiting for authorization service... {remaining_time} seconds remaining")
                    sys.stdout.flush()
                else:
                    print("\nNo authorization service found within 10 seconds. Sending 'quit' command to bluetoothctl...")
                    run_command(process, "quit")
                    process.wait()  # Wait for bluetoothctl to exit gracefully
                    countdown_started = False  # Reset countdown after sending quit

                    # Wait for 5 seconds for any response from bluetoothctl
                    print("Waiting for 5 seconds for any response from bluetoothctl...")
                    time.sleep(5)

                    # Execute the Raspberry Pi command after exiting bluetoothctl
                    print("Ready to execute the Raspberry Pi command...")
                    run_raspberry_pi_command("sudo sdptool add --channel=24 SP")
                    print("Command executed successfully.")

                    # Now start the RFCOMM server after the command execution
                    start_rfcomm_server()  # Start the RFCOMM server here

    except KeyboardInterrupt:
        print("\nExiting...")

    finally:
        # Cleanup GPIO settings
        GPIO.cleanup()
        
        # Stop scanning if bluetoothctl is still running
        if process.poll() is None:
            print("\nStopping device discovery...")
            run_command(process, "scan off")
        else:
            print("\nbluetoothctl has already exited.")

        process.terminate()


print("Waiting for button press to turn on A9G module and send AT command...")

try:
    while True:
        # Check if the button is pressed
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:
  
            # Start Bluetooth functionality
            start_bluetooth()

            time.sleep(0.5)  # Debounce delay to avoid multiple triggers

except KeyboardInterrupt:
    print("Script interrupted by user")

finally:
    # Clean up GPIO settings before exiting
    GPIO.cleanup()
    print("GPIO cleanup completed")

import time
import sys
import signal
import subprocess
import bluetooth
import os
import RPi.GPIO as GPIO

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


                
def manage_bluetooth_connection():
    """Start bluetoothctl, manage commands, and handle device connections."""
    # Start bluetoothctl as a subprocess
    process = subprocess.Popen(
        ['bluetoothctl'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1  # Line-buffered
    )

    commands = [
        ("Powering on the Bluetooth adapter...", "power on"),
        ("Making device discoverable...", "discoverable on"),
        ("Enabling agent...", "agent on"),
        ("Setting default agent...", "default-agent"),
        ("Starting device discovery...", "scan on")
    ]

    for message, command in commands:
        print(message)
        if process.poll() is None:  # Check if the process is still running
            process.stdin.write(command + '\n')
            process.stdin.flush()
            time.sleep(1)  # Allow some time for processing
        else:
            print(f"Process is not running. Unable to execute command: {command}")

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
                    process.stdin.write("yes\n")
                    process.stdin.flush()

                # Check for authorization service prompt
                if "[agent] Authorize service" in output:
                    print("Responding 'yes' to authorization service...")
                    process.stdin.write("yes\n")
                    process.stdin.flush()
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
                    # Continue listening for other output

            # Show countdown if it has been started
            if countdown_started:
                elapsed_time = time.time() - start_time
                remaining_time = countdown_duration - int(elapsed_time)
                if remaining_time > 0:
                    sys.stdout.write(f"\rWaiting for authorization service... {remaining_time} seconds remaining")
                    sys.stdout.flush()
                else:
                    print("\nNo authorization service found within 10 seconds. Sending 'quit' command to bluetoothctl...")
                    process.stdin.write("quit\n")
                    process.stdin.flush()
                    process.wait()  # Wait for bluetoothctl to exit gracefully
                    countdown_started = False  # Reset countdown after sending quit

                    # Wait for 5 seconds for any response from bluetoothctl
                    print("Waiting for 5 seconds for any response from bluetoothctl...")
                    time.sleep(5)

                    # Execute the Raspberry Pi command after exiting bluetoothctl
                    print("Ready to execute the Raspberry Pi command...")
                    run_raspberry_pi_command("sudo sdptool add --channel=23 SP")
                    print("Command executed successfully.")
                    GPIO.output(LED_PIN, GPIO.LOW)   # Turn off green LED
                    start_rfcomm_server()

                    # Now start the RFCOMM server after the command execution
                   

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        process.terminate()  # Ensure the process is terminated
        print("bluetoothctl process terminated.")
        GPIO.output(LED_PIN, GPIO.HIGH)
        
def run_raspberry_pi_command(command):
    """Run a command on Raspberry Pi."""
    try:
        output = subprocess.check_output(command, shell=True, text=True)
        print("Command output:", output)
        return output
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}\nOutput: {e.output}")

def append_to_contacts(number):
    with open("Contacts.txt", "a") as f:
        f.write(number + "\n")

def edit_contact(old_number, new_number):
    with open("Contacts.txt", "r") as f:
        lines = f.readlines()
    
    with open("Contacts.txt", "w") as f:
        for line in lines:
            if line.strip() == old_number:
                f.write(new_number + "\n")
            else:
                f.write(line)

def display_contacts():
    with open("Contacts.txt", "r") as f:
        contacts = f.readlines()
    return ''.join(contacts)

def request_contacts():
    """Retrieve and return contacts from the Contacts.txt file."""
    with open("Contacts.txt", "r") as f:
        contacts = f.readlines()
    return ''.join(contacts)

def start_rfcomm_server():
    """Start RFCOMM server on channel 23."""
    print("Starting RFCOMM server on channel 23...")

    try:
        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        port = 23
        server_sock.bind(("", port))
        server_sock.listen(1)

        print(f"Listening for connections on RFCOMM channel {port}...")
        client_sock, address = server_sock.accept()
        print("Connection established with:", address)

        while True:
            recvdata = client_sock.recv(1024).decode('utf-8').strip()
            print("Received command:", recvdata)

            if recvdata == "Q":
                print("Ending connection.")
                break
            if recvdata == "socket close":
                print("Ending connection.")
                break   

            if recvdata == "stop led":
                print("Turning off the LED.")
                GPIO.output(LED_PIN, GPIO.LOW)
                continue

            if recvdata == "show contacts":
                contacts = display_contacts()
                client_sock.send(contacts.encode('utf-8'))
                continue

            if recvdata == "request contacts":
                contacts = request_contacts()  # Call the new request_contacts function
                client_sock.send(contacts.encode('utf-8'))
                continue

            if recvdata.startswith('edit '):
                parts = recvdata.split()
                if len(parts) == 3:
                    old_number = parts[1]
                    new_number = parts[2]
                    edit_contact(old_number, new_number)
                    client_sock.send(f"Edited contact: {old_number} to {new_number}".encode('utf-8'))
                else:
                    client_sock.send("Invalid edit command format. Use: edit <old_number> <new_number>".encode('utf-8'))
                continue

            if recvdata.startswith('+') and len(recvdata) >= 10:
                append_to_contacts(recvdata)
                client_sock.send(f"Number added: {recvdata}".encode('utf-8'))
                continue

            try:
                output = subprocess.check_output(recvdata, shell=True, text=True)
                print("Command output:", output)
                client_sock.send(output.encode('utf-8'))
            except subprocess.CalledProcessError as e:
                error_message = f"Error executing command: {e}\nOutput: {e.output}"
                print("Error:", error_message)
                client_sock.send(error_message.encode('utf-8'))

    except bluetooth.BluetoothError as e:
        print("Bluetooth error occurred:", e)
    except OSError as e:
        print("OS error occurred:", e)
    finally:
        if 'client_sock' in locals():
            client_sock.close()
        if 'server_sock' in locals():
            server_sock.close()
        print("Sockets closed.")
        
def detect_button_presses():
    """Detect button presses and handle actions."""
    while True:
        # Check for button press on BUTTON_PIN_1
        if GPIO.input(BUTTON_PIN_1) == GPIO.LOW:
          # Add Bluetooth connection logic here
            print("Button 1 pressed! Initiating A9G module action...")
            GPIO.output(LED_BLUE, GPIO.HIGH)  # Turn on blue LED
            time.sleep(1)  # Delay to avoid multiple triggers
            GPIO.output(LED_BLUE, GPIO.LOW)   # Turn off blue LED
            # Add A9G module logic here

        # Check for button press on BUTTON_PIN_2
        if GPIO.input(BUTTON_PIN_2) == GPIO.LOW:
            print("Button 2 pressed! Initiating Bluetooth connection...")
            GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on green LED
            manage_bluetooth_connection()
            
           

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
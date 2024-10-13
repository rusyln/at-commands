import time
import sys
import signal
import subprocess
import bluetooth
import csv
import sqlite3
import os
import RPi.GPIO as GPIO
import serial
# Define GPIO pins
BUTTON_PIN_1 = 23  # Button 1 connected to GPIO 23 (Bluetooth)
BUTTON_PIN_2 = 24  # Button 2 connected to GPIO 24 (A9G Module)
LED_PIN = 12       # Green LED connected to GPIO 12
LED_BLUE = 6       # Blue LED connected to GPIO 6
A9G_POWER_PIN = 17  # GPIO17
# Initialize Serial connection with A9G module
ser = serial.Serial('/dev/serial0', baudrate=115200, timeout=1)
def setup_gpio():
    """Set up GPIO pins."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(BUTTON_PIN_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button 1 as input with pull-up
    GPIO.setup(BUTTON_PIN_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button 2 as input with pull-up
    GPIO.setup(LED_PIN, GPIO.OUT)                                 # Green LED as output
    GPIO.setup(LED_BLUE, GPIO.OUT)                               # Blue LED as output
    GPIO.setup(A9G_POWER_PIN, GPIO.OUT)                         # A9G Power pin as output

def create_database():
    """Create the SQLite database and contacts/messages tables if they don't exist."""
    conn = sqlite3.connect('contacts.db')  # Create or open the SQLite database
    cursor = conn.cursor()

    # Create a table named 'contacts' if it doesn't already exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contacts (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            ContactName TEXT NOT NULL,
            ContactNumber TEXT NOT NULL
        )
    ''')

    # Create a table named 'messages' if it doesn't already exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            MessageText TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    print("Database and tables 'contacts' and 'messages' created successfully.")


def add_contact_to_database(contact_name, contact_number):
    """Add a new contact to the contacts table."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    # Insert a new contact into the contacts table
    cursor.execute('''
        INSERT INTO contacts (ContactName, ContactNumber)
        VALUES (?, ?)
    ''', (contact_name, contact_number))

    conn.commit()
    conn.close()
    print(f"Contact '{contact_name}' with number '{contact_number}' added successfully.")
def add_message_to_database(message_text):
    """Add a new message to the messages table."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    # Insert a new message into the messages table
    cursor.execute('''
        INSERT INTO messages (MessageText)
        VALUES (?)
    ''', (message_text,))

    conn.commit()
    conn.close()
    print(f"Message '{message_text}' added successfully.")
    
def list_all_contacts():
    """Retrieve and display all contacts from the contacts table."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    # Query all contacts from the contacts table
    cursor.execute('SELECT * FROM contacts')
    contacts = cursor.fetchall()

    conn.close()

    if contacts:
        print("Contact List:")
        for contact in contacts:
            print(f"ID: {contact[0]}, Name: {contact[1]}, Number: {contact[2]}")
    else:
        print("No contacts found in the database.")
                
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
        GPIO.output(LED_PIN, GPIO.HIGH)
        while True:
            recvdata = client_sock.recv(1024).decode('utf-8').strip()
            print("Received command:", recvdata)

            if recvdata == "Q" or recvdata == "socket close":
                print("Ending connection.")
                break   

            if recvdata.startswith("contact:"):
                # Example format: "contact:John Doe,1234567890"
                _, contact_info = recvdata.split(":", 1)
                contact_name, contact_number = contact_info.split(",", 1)
                add_contact_to_database(contact_name.strip(), contact_number.strip())
                print(f"Contact '{contact_name.strip()}' with number '{contact_number.strip()}' saved to the database.")
                continue

            if recvdata.startswith("set message:"):
                # Example format: "set message:Hello, this is a test message"
                _, message_text = recvdata.split(":", 1)
                add_message_to_database(message_text.strip())
                print(f"Message '{message_text.strip()}' saved to the database.")
                continue

            print(f"Unknown command received: {recvdata}")  # Log unknown commands
            client_sock.send(f"Unknown command: {recvdata}".encode('utf-8'))

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

def turn_on_a9g():
    print("Turning on A9G module...")
    GPIO.output(A9G_POWER_PIN, GPIO.HIGH)  # Set the pin high to turn on the A9G module
    time.sleep(10)  # Keep it on for 2 seconds (adjust as needed)
    
    if check_module_ready():  # Check if the A9G module is ready
        print("A9G module is ready.")
        GPIO.output(LED_PIN, GPIO.LOW)
        GPIO.output(LED_BLUE, GPIO.HIGH)
    else:
        GPIO.output(A9G_POWER_PIN, GPIO.LOW)
        print("A9G module is not ready. Please check the connection.")


def send_command(command):
    """Send a command to the A9G module and return the response."""
    ser.write((command + '\r\n').encode())
    time.sleep(1)  # Wait for the response
    response = ser.readlines()
    return [line.decode('utf-8').strip() for line in response]

def check_module_ready():
    """Check if the A9G module is ready by sending the AT command."""
    response = send_command('AT')
    print("AT Command Response:", response)
    return any("OK" in line for line in response)
       
def detect_button_presses():
    """Detect button presses and handle actions."""
    while True:
        # Check for button press on BUTTON_PIN_1
        if GPIO.input(BUTTON_PIN_1) == GPIO.LOW:
            print("Initiating Bluetooth connection...")
            GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on green LED
            manage_bluetooth_connection()
        
        # Check for button press on BUTTON_PIN_2
        if GPIO.input(BUTTON_PIN_2) == GPIO.LOW:
            press_start_time = time.time()  # Record the start time of the press
            GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on green LED
            while GPIO.input(BUTTON_PIN_2) == GPIO.LOW:
                time.sleep(0.1)  # Debounce delay while button is pressed

            press_duration = time.time() - press_start_time  # Calculate press duration

            # Check if it was a long press (3 seconds)
            if press_duration >= 3:
                print("Long press detected. Fetching GPS data...")
                get_gps_location()  # Call the function to fetch GPS data
            else:
                print("Short press detected. Turning on A9G module...")
                turn_on_a9g()  # Call to turn on A9G and check readiness
            
            time.sleep(1)  # Delay to avoid multiple triggers

        time.sleep(0.1)  # Small delay to prevent CPU overload

def get_gps_location(retries=3):
    """Fetch GPS location data from the A9G module using AT+LOCATION=2.
    
    Args:
        retries (int): The number of times to retry fetching the GPS location if no valid data is found.
    
    Returns:
        tuple: A tuple containing latitude and longitude or (None, None) if not found.
    """
    for attempt in range(retries):
        print(f"Attempt {attempt + 1} to fetch GPS location...")

        # Enable GPS if it's not enabled
        gps_enable_response = send_command('AT+GPS=1')  # Ensure GPS is enabled
        print("GPS Activation Response:", gps_enable_response)

        # Request GPS data for 5 seconds
        gps_read_response = send_command('AT+GPSRD=5')
        print("GPS Read Response:", gps_read_response)

        # Wait for a moment to ensure data is ready
        time.sleep(6)  # Wait for 5 seconds to allow GPS to gather data

        # Now request GPS location
        response = send_command('AT+LOCATION=2')
        print("GPS Location Response:", response)

        latitude, longitude = None, None

        # Check for the expected response format
        for line in response:
            if "OK" not in line and line:  # Exclude the OK line
                try:
                    latitude, longitude = map(float, line.split(','))
                    print(f"Latitude: {latitude}, Longitude: {longitude}")
                    break  # Exit once valid data is found
                except ValueError:
                    print(f"Failed to parse GPS data: {line}")

        # Stop GPS reading after getting the location
        gps_read_response = send_command('AT+GPSRD=0')
        print("GPS Read Response After Location Request:", gps_read_response)

        # Check if valid GPS data was found
        if latitude is not None and longitude is not None:
            return latitude, longitude
        else:
            print("No valid GPS data found. Retrying...")
            time.sleep(2)  # Wait before retrying

    print("Failed to obtain valid GPS data after multiple attempts.")
    return None, None  # Return None if GPS data could not be retrieved


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
    create_database()  # Ensure the database is set up before running
    main()
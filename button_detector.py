import time
import sys
import signal
import subprocess
import bluetooth
import csv
import sqlite3
import os
import re
import RPi.GPIO as GPIO
import serial
import random

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
    
def retrieve_all_messages():
    """Retrieve all saved messages from the messages table."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    # Query all messages from the messages table
    cursor.execute('SELECT MessageText FROM messages')
    messages = cursor.fetchall()

    conn.close()
    
    # Extract messages from tuples and return as a list
    return [message[0] for message in messages]
    
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
    """Retrieve and return all contact numbers from the contacts table."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    # Query all contacts from the contacts table
    cursor.execute('SELECT ContactNumber FROM contacts')
    contact_numbers = cursor.fetchall()

    conn.close()

    # Use a regular expression to extract valid contact numbers (keeping + and digits only)
    cleaned_numbers = []
    for contact in contact_numbers:
        cleaned_number = re.sub(r'[^\d+]', '', contact[0])  # Remove all characters except digits and '+'
        cleaned_numbers.append(cleaned_number)

    return cleaned_numbers  # Return the cleaned list of numbers
def retrieve_all_contact_numbers():
    """Retrieve all unique contact numbers from the contacts table."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    try:
        # Query all contact numbers from the contacts table
        cursor.execute('SELECT ContactNumber FROM contacts')
        contact_numbers = cursor.fetchall()

        # Extract numbers from tuples and return as a unique list
        unique_contact_numbers = set(contact[0] for contact in contact_numbers)  # Use a set for uniqueness
        return list(unique_contact_numbers)  # Convert set back to list

    except sqlite3.Error as e:
        print(f"An error occurred while retrieving contact numbers: {e}")
        return []  # Return an empty list on error

    finally:
        conn.close()  # Ensure the connection is closed


def send_sms(latitude, longitude, contact, message_text):
    """Send an SMS with a given message to a contact using the A9G module."""
    # Set SMS format to text mode
    response = send_command('AT+CMGF=1')
    print("Setting SMS format:", response)

    # Prepare the SMS command
    sms_command = f'AT+CMGS="{contact}"'
    response = send_command(sms_command)
    print("SMS Command Response:", response)

    # Send the message body
    ser.write((message_text + chr(26)).encode())  # Send the message followed by Ctrl+Z (ASCII 26)
    time.sleep(3)  # Wait for the message to be sent

    # Check for response
    response = ser.readlines()
    print("SMS Response:", response)

def send_sms_to_all_contacts(latitude, longitude):
    """Send all saved messages from the database and then the GPS coordinates to all contacts."""
    contact_numbers = list_all_contacts()  # Retrieve all contact numbers from the database
    messages = retrieve_all_messages()  # Retrieve all saved messages from the database
    
    if not contact_numbers:
        print("No contacts to send SMS.")
        return

    if not messages:
        print("No messages to send.")
        return

    # Format for Google Maps URL
    google_maps_url = f"{latitude},{longitude}"

    # Send each message to each contact number
    for contact in contact_numbers:
        # Send each retrieved message
        for message in messages:
            print(f"Sending SMS to {contact}: {message}...")
            send_sms(latitude, longitude, contact, message)  # Send each message to the contact
            time.sleep(1)  # Delay to avoid overwhelming the module

        # After sending all messages, send the GPS coordinates
        print(f"Sending GPS coordinates to {contact}: {google_maps_url}...")
        send_sms(latitude, longitude, contact, google_maps_url)  # Send Google Maps link to the contact
        time.sleep(1)  # Delay to avoid overwhelming the module


                
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
        ("Starting device discovery...", "scan on"),
        ("Checking for devices...", "devices")  # Add 'devices' command here
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

        device_found = False

        while True:
            # Read output continuously
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break  # Exit loop if the process is terminated
            if output:
                print(f"Output: {output.strip()}")

                # Check for a connected device after issuing 'devices' command
                if "Device" in output:
                    print(f"Device found: {output.strip()}")
                    device_found = True
                    break  # Exit loop since a device is found

                # Check for passkey confirmation
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

            # Show countdown if it has been started (unchanged)
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
                    return  # Exit the function after completing the steps

        # Device found logic
        if device_found:
            print("Device connected. Sending 'quit' command to bluetoothctl...")
            process.stdin.write("quit\n")
            process.stdin.flush()

            # Wait for bluetoothctl to terminate with a timeout
            try:
                process.wait(timeout=5)  # Wait up to 5 seconds for process to terminate
            except subprocess.TimeoutExpired:
                print("bluetoothctl did not terminate within 5 seconds. Forcing termination...")
                process.terminate()
                process.wait()  # Ensure process is fully terminated

            # Now proceed with executing the Raspberry Pi command
            print("Ready to execute the Raspberry Pi command...")
            run_raspberry_pi_command("sudo sdptool add --channel=23 SP")
            print("Command executed successfully.")
            GPIO.output(LED_PIN, GPIO.LOW)  # Turn off green LED
            start_rfcomm_server()
            return  # Exit the function after completing the steps

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if process.poll() is None:  # Check if the process is still running
            process.terminate()  # Ensure the process is terminated
            process.wait()  # Wait for termination
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

def retrieve_all_contacts():
    """Retrieve all contacts from the contacts table."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    # Query all contacts from the contacts table
    cursor.execute('SELECT ContactName, ContactNumber FROM contacts')
    contacts = cursor.fetchall()

    conn.close()
    
    # Return contacts as a list of dictionaries
    return [{'name': contact[0], 'number': contact[1]} for contact in contacts]

def delete_contact_from_database(contact_number):
    """Delete a contact from the contacts table based on the contact number."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    # Delete the contact with the specified contact number
    cursor.execute('DELETE FROM contacts WHERE ContactNumber = ?', (contact_number,))

    conn.commit()
    conn.close()
    print(f"Contact with number '{contact_number}' deleted successfully.")

def update_message_in_database(message_id, new_message_text):
    """Update an existing message in the messages table."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    # Update the message text for the specified message ID
    cursor.execute('''
        UPDATE messages
        SET MessageText = ?
        WHERE ID = ?
    ''', (new_message_text, message_id))

    conn.commit()
    conn.close()
    print(f"Message with ID '{message_id}' updated successfully.")

def start_rfcomm_server():
    """Start RFCOMM server on a random channel if needed."""
    print("Starting RFCOMM server on channel 23...")

    try:
        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        port = 23
        server_sock.bind(("", port))
        server_sock.listen(1)

        print(f"Listening for connections on RFCOMM channel {port}...")
        client_sock, address = server_sock.accept()
        GPIO.output(LED_BLUE, GPIO.HIGH)
        print("Connection established with:", address)
       
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
            
            if recvdata.startswith("sync data"):
                # Retrieve all contacts and messages and send them to the Android app
                contacts = retrieve_all_contacts()
                messages = retrieve_all_messages()
                
                # Sync data as a dictionary
                sync_data = {'contacts': contacts, 'messages': messages}
                
                # Send the data in string format
                client_sock.send(str(sync_data).encode('utf-8'))
                
                # Print out the synced data
                print("Data synced with the Android app:", sync_data)
                continue

            if recvdata.startswith("delete contact:"):
                # Example format: "delete contact:1234567890"
                _, contact_number = recvdata.split(":", 1)
                delete_contact_from_database(contact_number.strip())
                print(f"Contact with number '{contact_number.strip()}' deleted.")
                continue

            if recvdata.startswith("update message:"):
                # Example format: "update message:1,New Message Text"
                _, message_info = recvdata.split(":", 1)
                message_id, new_message_text = message_info.split(",", 1)
                update_message_in_database(message_id.strip(), new_message_text.strip())
                print(f"Message with ID '{message_id.strip()}' updated to '{new_message_text.strip()}'.")
                continue

            print(f"Unknown command received: {recvdata}")  # Log unknown commands
            client_sock.send(f"Unknown command: {recvdata}".encode('utf-8'))

    except bluetooth.BluetoothError as e:
        print("Bluetooth error occurred:", e)
        if "Address already in use" in str(e):
            new_port = random.randint(24, 99)
            print(f"Address already in use. Trying a new port: {new_port}...")
            run_raspberry_pi_command(f"sudo sdptool add --channel={new_port} SP")
            start_rfcomm_server_with_new_port(new_port)  # Retry with new port
    except OSError as e:
        print("OS error occurred:", e)
    finally:
        if 'client_sock' in locals():
            client_sock.close()
        if 'server_sock' in locals():
            server_sock.close()
        print("Sockets closed.")

def start_rfcomm_server_with_new_port(port):
    """Start RFCOMM server on a specific port."""
    try:
        server_sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        server_sock.bind(("", port))
        server_sock.listen(1)

        print(f"Listening for connections on RFCOMM channel {port}...")
        client_sock, address = server_sock.accept()
        GPIO.output(LED_BLUE, GPIO.HIGH)
        print("Connection established with:", address)

        # Continue handling client communication as above
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
            
            if recvdata == "sync data":
                # Retrieve all contacts and messages and send them to the Android app
                contacts = retrieve_all_contacts()
                messages = retrieve_all_messages()
                sync_data = {'contacts': contacts, 'messages': messages}
                client_sock.send((str(sync_data) + "\nEND_OF_DATA").encode('utf-8'))
                print("Data synced with the Android app.")
                continue

            if recvdata.startswith("delete contact:"):
                # Example format: "delete contact:1234567890"
                _, contact_number = recvdata.split(":", 1)
                delete_contact_from_database(contact_number.strip())
                print(f"Contact with number '{contact_number.strip()}' deleted.")
                continue

            if recvdata.startswith("update message:"):
                # Example format: "update message:1,New Message Text"
                _, message_info = recvdata.split(":", 1)
                message_id, new_message_text = message_info.split(",", 1)
                update_message_in_database(message_id.strip(), new_message_text.strip())
                print(f"Message with ID '{message_id.strip()}' updated to '{new_message_text.strip()}'.")
                continue

            print(f"Unknown command received: {recvdata}")  # Log unknown commands
            client_sock.send(f"Unknown command: {recvdata}".encode('utf-8'))

    except bluetooth.BluetoothError as e:
        print("Bluetooth error occurred:", e)
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
    
    # Print raw byte data for debugging
    print("Raw Response:", response)  
    
    # Decode response and ignore decoding errors
    return [line.decode('utf-8', errors='ignore').strip() for line in response]

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
                GPIO.output(LED_BLUE, GPIO.LOW)
                get_gps_location()  # Call the function to fetch GPS data
            else:
                print("Short press detected. Turning on A9G module...")
                turn_on_a9g()  # Call to turn on A9G and check readiness
            
            time.sleep(1)  # Delay to avoid multiple triggers

        time.sleep(0.1)  # Small delay to prevent CPU overload

def get_gps_location():
    """Fetch GPS location data from the A9G module using AT+LOCATION=2.

    Returns:
        tuple: A tuple containing latitude and longitude or (None, None) if not found.
    """
    while True:
        print("Attempting to fetch GPS location...")

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

        # Check if valid GPS data was found
        if latitude is not None and longitude is not None:
            # Stop GPS reading after getting the location
            gps_read_response = send_command('AT+GPSRD=0')
            print("GPS Read Response After Location Request:", gps_read_response)

            # Now send SMS with retrieved messages and GPS coordinates
            send_sms_to_all_contacts(latitude, longitude)  # Send SMS after getting location
            return latitude, longitude  # Return valid data
        else:
            print("No valid GPS data found. Retrying...")
            time.sleep(2)  # Wait before retrying




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
import time
import sys
import signal
import subprocess
import bluetooth
import csv
import sqlite3
import os
import threading
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
    GPIO.setup(LED_PIN, GPIO.OUT)                                # Green LED as output
    GPIO.setup(LED_BLUE, GPIO.OUT)                               # Blue LED as output
    GPIO.setup(A9G_POWER_PIN, GPIO.OUT)                          # A9G Power pin as output
    GPIO.output(LED_PIN, GPIO.LOW)  # Ensure LEDs are initially off
    GPIO.output(LED_BLUE, GPIO.LOW)

def create_database():
    """Create the SQLite database and contacts/messages tables if they don't exist."""
    db_file = 'contacts.db'

    # Connect to the SQLite database; if the file doesn't exist, it will be created.
    db_exists = os.path.exists(db_file)
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # If the database did not exist, create the tables
    if not db_exists:
        # Create a table named 'contacts' if it doesn't already exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                ID INTEGER PRIMARY KEY AUTOINCREMENT,
                A_ID INTEGER NOT NULL,  -- New separate ID for Android data as INTEGER
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
        print("Database and tables 'contacts' and 'messages' created successfully.")
    else:
        print("Database already exists, no need to create tables.")

    conn.commit()
    conn.close()


def add_contact_to_database(a_id, contact_name, contact_number):
    """Add a new contact to the contacts table with A_ID."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    # Insert a new contact into the contacts table
    cursor.execute('''
        INSERT INTO contacts (A_ID, ContactName, ContactNumber)
        VALUES (?, ?, ?)
    ''', (a_id, contact_name, contact_number))

    conn.commit()
    conn.close()
    print(f"Contact '{contact_name}' with number '{contact_number}' and A_ID '{a_id}' added successfully.")
    
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

def retrieve_all_messages_with_id():
    """Retrieve all saved messages from the messages table."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    # Query all messages from the messages table
    cursor.execute('SELECT ID,MessageText FROM messages')
    messages = cursor.fetchall()

    conn.close()
    
    # Extract messages from tuples and return as a list
    return [{'id': message[0], 'message': message[1]} for message in messages]

def update_contact_in_database(a_id, new_contact_name, new_contact_number):
    """Update the contact information in the contacts table based on the A_ID."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    try:
        # Update the contact details using A_ID
        cursor.execute('''
            UPDATE contacts
            SET ContactName = ?, ContactNumber = ?
            WHERE A_ID = ?  -- Use A_ID to identify the contact
        ''', (new_contact_name, new_contact_number, a_id))

        if cursor.rowcount == 0:
            print(f"No contact found with A_ID {a_id}.")
        else:
            print(f"Contact with A_ID {a_id} updated to Name: '{new_contact_name}', Number: '{new_contact_number}'.")

        conn.commit()

    except sqlite3.Error as e:
        print(f"An error occurred while updating the contact: {e}")

    finally:
        conn.close()
        
            
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

    # Return only the numbers as a list
    return [contact[0] for contact in contact_numbers]  # Extract the number from the tuples
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



def steady_led(led_pin, duration=5):
    """Turn on the specified LED steadily for the given duration (in seconds)."""
    GPIO.output(led_pin, GPIO.HIGH)  # Turn on the LED
    time.sleep(duration)              # Keep the LED on for the duration
    GPIO.output(led_pin, GPIO.LOW)    # Turn off the LED after the duration

def blink_led(led_pin, duration=5):
    """Blink the specified LED for the given duration (in seconds)."""
    end_time = time.time() + duration
    while time.time() < end_time:
        GPIO.output(led_pin, GPIO.HIGH)  # Turn on the LED
        time.sleep(0.5)
        GPIO.output(led_pin, GPIO.LOW)    # Turn off the LED
        time.sleep(0.5)
def blue_led_blink():
    """Blink the Blue LED while Bluetooth is connecting until stopped."""
    while not stop_event.is_set():
        GPIO.output(LED_BLUE, GPIO.HIGH)  # Turn on Blue LED
        time.sleep(0.5)                   # Blink interval
        GPIO.output(LED_BLUE, GPIO.LOW)   # Turn off Blue LED
        time.sleep(0.5)

def manage_bluetooth_connection():
    """Start bluetoothctl, manage commands, and handle device connections."""
    
    # Set initial states for LEDs
    GPIO.output(LED_PIN, GPIO.LOW)   # Turn off green LED initially
    GPIO.output(LED_BLUE, GPIO.LOW)  # Turn off blue LED initially

    # Start the Blue LED blinking thread
    stop_event.clear()  # Ensure the stop event is cleared before starting the thread
    blue_led_thread = threading.Thread(target=blue_led_blink)
    blue_led_thread.start()

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
        ("Starting device scan...", "scan on")
    ]

    for message, command in commands:
        print(message)
        
        if command is None:
            print("Command is None. Skipping...")
            continue
        
        if process.poll() is None:  # Check if the process is still running
            try:
                process.stdin.write(command + '\n')
                process.stdin.flush()
                time.sleep(1)  # Allow time for processing
            except Exception as e:
                print(f"Failed to send command '{command}': {e}")
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

                    # Stop Blue LED blinking and turn it to steady light
                    stop_event.set()
                    blue_led_thread.join()  # Ensure blinking thread stops
                    GPIO.output(LED_BLUE, GPIO.HIGH)  # Turn on Blue LED (steady light)
                    
                    start_rfcomm_server()  # Now start the RFCOMM server

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # Ensure the process is terminated
        process.terminate()
        print("bluetoothctl process terminated.")
        turn_off_bluetooth()  # Call this function to turn off Bluetooth
        GPIO.output(LED_BLUE, GPIO.LOW)  # Turn off Blue LED
        GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on green LED steady

def turn_off_bluetooth():
    """Turn off Bluetooth using bluetoothctl."""
    try:
        # Start a new bluetoothctl process
        process = subprocess.Popen(
            ['bluetoothctl'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line-buffered
        )

        # Send the 'power off' command to disable Bluetooth
        print("Turning off Bluetooth...")
        process.stdin.write("power off\n")
        process.stdin.flush()
        
        # Wait for the process to finish gracefully
        process.stdin.write("quit\n")
        process.stdin.flush()
        process.wait()  # Wait for process termination

        # Process has successfully terminated
        print("bluetoothctl process terminated. Bluetooth is now powered off.")

    except Exception as e:
        print(f"An error occurred while turning off Bluetooth: {e}")
    finally:
        process.terminate()
        print("Bluetooth turned off successfully.")
        
                
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

def retrieve_all_contacts_with_id():
    """Retrieve all contacts from the contacts table."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    # Query all contacts from the contacts table
    cursor.execute('SELECT A_ID,ContactName, ContactNumber FROM contacts')
    contacts = cursor.fetchall()

    conn.close()
    
    # Return contacts as a list of dictionaries
    return [{'A_ID':contact[0],'name': contact[1], 'number': contact[2]} for contact in contacts]

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
    """Update an existing message in the messages table, or insert if not found."""
    conn = sqlite3.connect('contacts.db')
    cursor = conn.cursor()

    # Attempt to update the message text for the specified message ID
    cursor.execute('''
        UPDATE messages
        SET message_text = ?
        WHERE message_id = ?
    ''', (new_message_text, message_id))

    # Check if any row was updated
    if cursor.rowcount == 0:
        # If no rows were updated, insert the new message
        cursor.execute('''
            INSERT INTO messages (message_id, message_text)
            VALUES (?, ?)
        ''', (message_id, new_message_text))
        print(f"Message with ID '{message_id}' not found. Inserted as a new record.")
    else:
        print(f"Message with ID '{message_id}' updated successfully.")

    # Commit the transaction and close the connection
    conn.commit()
    conn.close()
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
                # Example format: "contact:A_ID,ContactName,ContactNumber"
                _, contact_info = recvdata.split(":", 1)
                a_id, contact_name, contact_number = contact_info.split(",", 2)
                
                # Call the function with all three arguments
                add_contact_to_database(int(a_id.strip()), contact_name.strip(), contact_number.strip())
                print(f"Contact '{contact_name.strip()}' with number '{contact_number.strip()}' and A_ID '{a_id.strip()}' saved to the database.")
                continue


            if recvdata.startswith("set message:"):
                # Example format: "set message:Hello, this is a test message"
                _, message_text = recvdata.split(":", 1)
                add_message_to_database(message_text.strip())
                print(f"Message '{message_text.strip()}' saved to the database.")
                continue
            
            if recvdata.startswith("sync data"):
                # Retrieve all contacts and messages and send them to the Android app
                contacts = retrieve_all_contacts_with_id()
                messages = retrieve_all_messages_with_id()
                
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
            
            if recvdata.startswith("update contact:"):
                # Example format: "update contact:1,New Name,0987654321"
                _, contact_info = recvdata.split(":", 1)
                contact_id, new_contact_name, new_contact_number = contact_info.split(",", 2)
                update_contact_in_database(contact_id.strip(), new_contact_name.strip(), new_contact_number.strip())
                print(f"Contact with ID '{contact_id.strip()}' updated.")
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
                # Example format: "contact:A_ID,ContactName,ContactNumber"
                _, contact_info = recvdata.split(":", 1)
                a_id, contact_name, contact_number = contact_info.split(",", 2)
                
                # Call the function with all three arguments
                add_contact_to_database(int(a_id.strip()), contact_name.strip(), contact_number.strip())
                print(f"Contact '{contact_name.strip()}' with number '{contact_number.strip()}' and A_ID '{a_id.strip()}' saved to the database.")
                continue
            
            if recvdata.startswith("set message:"):
                # Example format: "set message:Hello, this is a test message"
                _, message_text = recvdata.split(":", 1)
                add_message_to_database(message_text.strip())
                print(f"Message '{message_text.strip()}' saved to the database.")
                continue
            
            if recvdata == "sync data":
                # Retrieve all contacts and messages and send them to the Android app
                contacts = retrieve_all_contacts_with_id()
                messages = retrieve_all_messages_with_id()
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

def turn_off_a9g():
    """Check A9G responsiveness with AT command, then power it off if responsive."""
    # Set initial LED states
    GPIO.output(LED_PIN, GPIO.HIGH)   # Turn on green LED
    GPIO.output(LED_BLUE, GPIO.LOW)   # Turn off blue LED
    
    # Step 1: Send initial AT command to check for response
    response = send_command('AT')
    print("Initial AT command response:", response)
    
    # Step 2: Check if response is as expected
    if 'OK' in response:
        print("A9G module is responsive. Proceeding with power-off command.")
        
        # Step 3: Send the power-off command
        power_off_response = send_command('AT+RST=2')
        print("A9G power-off command response:", power_off_response)
        
        # Optional: Control GPIO pin to ensure power is off
        GPIO.output(A9G_POWER_PIN, GPIO.LOW)
        print("A9G module powered off via AT command and GPIO.")
        
        # Delay to allow for complete power-off
        time.sleep(2)
        
        # Update LED state to indicate completion
        GPIO.output(LED_PIN, GPIO.LOW)   # Turn off green LED
        GPIO.output(LED_BLUE, GPIO.HIGH) # Turn on blue LED to indicate module is powered off
        
    else:
        print("A9G module is not responding. Unable to power off.")

    
    
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
    global green_led_thread  # Make green_led_thread a global variable
    while True:
        # Check for button press on BUTTON_PIN_1
        if GPIO.input(BUTTON_PIN_1) == GPIO.LOW:
            print("Initiating Bluetooth connection...")
            GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on green LED (steady)
            manage_bluetooth_connection()  # Your Bluetooth handling function

        # Check for button press on BUTTON_PIN_2
        if GPIO.input(BUTTON_PIN_2) == GPIO.LOW:
            press_start_time = time.time()  # Record the start time of the press
            GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on green LED (steady)
            while GPIO.input(BUTTON_PIN_2) == GPIO.LOW:
                time.sleep(0.1)  # Debounce delay while button is pressed

            press_duration = time.time() - press_start_time  # Calculate press duration

            # Check if it was a long press (3 seconds)
            if press_duration >= 3:
                print("Long press detected. Fetching GPS data...")
                GPIO.output(LED_PIN, GPIO.LOW)  # Start blinking (set to low initially)
                stop_event.clear()  # Clear stop event to allow blinking
                green_led_thread = threading.Thread(target=green_led_blink)
                green_led_thread.start()  # Start blinking thread
                get_gps_location()  # Call the function to fetch GPS data
            else:
                print("Short press detected. Turning on A9G module...")
                turn_on_a9g()  # Call to turn on A9G and check readiness
            
            time.sleep(1)  # Delay to avoid multiple triggers

        time.sleep(0.1)  # Small delay to prevent CPU overload
        
        
        
def green_led_blink():
    """Blink the Green LED indefinitely until stopped."""
    while not stop_event.is_set():
        GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on Green LED
        time.sleep(0.5)                  # Blink interval
        GPIO.output(LED_PIN, GPIO.LOW)   # Turn off Green LED
        time.sleep(0.5)

def get_gps_location():
    """Fetch GPS location data from the A9G module using AT+LOCATION=2."""
    global green_led_thread  # Ensure access to green_led_thread
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

            # Stop green LED blinking by setting the stop event
            stop_event.set()
            green_led_thread.join()  # Ensure the thread finishes

            # Now turn on the Blue LED for 10 seconds
            GPIO.output(LED_BLUE, GPIO.HIGH)  # Turn on Blue LED
            time.sleep(10)                   # Keep Blue LED on for 10 seconds
            GPIO.output(LED_BLUE, GPIO.LOW)   # Turn off Blue LED

            # Send SMS with retrieved messages and GPS coordinates
            send_sms_to_all_contacts(latitude, longitude)  # Send SMS after getting location
            return latitude, longitude  # Return valid data
        else:
            print("No valid GPS data found. Retrying...")
            time.sleep(2)  # Wait before retrying


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

    # Turn off A9G module after sending the final message
    turn_off_a9g()
    print("All messages sent. A9G module turned off.")



def main():
    """Main function to initialize the button detection."""
    try:
        GPIO.setwarnings(False)  # Disable warnings
        GPIO.cleanup()           # Clean up GPIO settings
        setup_gpio()             # Set up GPIO pins
        print("System is ready, waiting for button press...")

        # Create a stop event for the blinking LED
        global stop_event
        stop_event = threading.Event()
        
        GPIO.output(LED_PIN, GPIO.HIGH) 
        GPIO.output(LED_BLUE, GPIO.LOW) 
        detect_button_presses()  # Start detecting button presses
    except KeyboardInterrupt:
        print("Program stopped by user.")
    finally:
        GPIO.cleanup()  # Clean up GPIO settings

if __name__ == "__main__":
    create_database()  # Ensure the database is set up before running
    main()
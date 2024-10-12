import time
import sys
import signal
import subprocess
import RPi.GPIO as GPIO

# Pin definitions
BUTTON_PIN_1 = 23  # Button 1 connected to GPIO 23
BUTTON_PIN_2 = 24  # Button 2 connected to GPIO 24
LED_PIN = 12       # Green LED connected to GPIO 12
LED_BLUE = 6       # Blue LED connected to GPIO 6

def setup_gpio():
    """Setup GPIO pins."""
    GPIO.setmode(GPIO.BCM)  # Use BCM pin numbering
    GPIO.setup(BUTTON_PIN_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button 1 as input with pull-up
    GPIO.setup(BUTTON_PIN_2, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Button 2 as input with pull-up
    GPIO.setup(LED_PIN, GPIO.OUT)      # Green LED as output
    GPIO.setup(LED_BLUE, GPIO.OUT)     # Blue LED as output
    GPIO.output(LED_PIN, GPIO.LOW)     # Ensure the green LED is off
    GPIO.output(LED_BLUE, GPIO.LOW)    # Ensure the blue LED is off

def run_bluetoothctl():
    """Start the bluetoothctl process."""
    return subprocess.Popen(
        ['bluetoothctl'],
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1,
        close_fds=True
    )

def run_command(process, command):
    """Send a command to the bluetoothctl process."""
    process.stdin.write(command + "\n")
    process.stdin.flush()

def signal_handler(sig, frame):
    """Handle the exit signal."""
    print("\nExiting... Please wait.")
    GPIO.cleanup()  # Clean up GPIO settings
    sys.exit(0)

def button_callback(channel):
    """Callback function to handle button press."""
    if channel == BUTTON_PIN_1:
        print("Button 1 pressed! Starting Bluetooth...")
        GPIO.output(LED_PIN, GPIO.HIGH)  # Turn on the green LED
        start_bluetooth()  # Start the Bluetooth functionality
        GPIO.output(LED_PIN, GPIO.LOW)   # Turn off the green LED

def start_bluetooth():
    """Start Bluetooth functionality."""
    process = run_bluetoothctl()

    # Set up signal handler to allow graceful exit
    signal.signal(signal.SIGINT, signal_handler)

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

    print("Waiting for a device to connect. Press Ctrl+C to exit.")
    
    countdown_started = False
    countdown_duration = 10  # 10 seconds countdown
    start_time = None

    while True:
        try:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break  # Exit loop if the process is terminated
            if output:
                print(f"Output: {output.strip()}")

                if "Confirm passkey" in output:
                    print("Responding 'yes' to passkey confirmation...")
                    run_command(process, "yes")

                if "[agent] Authorize service" in output:
                    print("Responding 'yes' to authorization service...")
                    run_command(process, "yes")
                    countdown_started = False  # Stop countdown if service is authorized

                if "Invalid command in menu main:" in output:
                    print("Received 'Invalid command in menu main:', starting countdown...")
                    countdown_started = True
                    start_time = time.time()

                if "Serial Port service registered" in output:
                    print("Serial Port service registered. Waiting for 5 seconds...")
                    time.sleep(5)  # Wait for 5 seconds

            if countdown_started:
                elapsed_time = time.time() - start_time
                remaining_time = countdown_duration - int(elapsed_time)
                if remaining_time > 0:
                    sys.stdout.write(f"\rWaiting for {remaining_time} seconds...")
                    sys.stdout.flush()
                else:
                    print("\nCountdown expired. Continuing to check for output...")

        except Exception as e:
            print(f"Error: {e}")

    process.terminate()  # Ensure subprocess is terminated
    GPIO.cleanup()  # Clean up GPIO settings

# Example call to the function
if __name__ == "__main__":
    setup_gpio()
    GPIO.add_event_detect(BUTTON_PIN_1, GPIO.FALLING, callback=button_callback, bouncetime=200)  # Add button press event detection
    signal.signal(signal.SIGINT, signal_handler)  # Set up signal handler for exit
    print("System ready. Press Button 1 to start Bluetooth.")

    # Keep the program running
    try:
        while True:
            time.sleep(1)  # Sleep to keep the script running

    except KeyboardInterrupt:
        print("Exiting on user interrupt...")
        GPIO.cleanup()  # Clean up GPIO settings

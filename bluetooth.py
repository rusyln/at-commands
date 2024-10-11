import time
import sys
import signal
import subprocess

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
    sys.exit(0)

def start_bluetooth():
    """Start Bluetooth functionality."""
    # Start bluetoothctl
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
    
    # Initialize variables for countdown
    countdown_started = False
    countdown_duration = 10  # 10 seconds countdown
    start_time = None

    while True:
        try:
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

        except Exception as e:
            print(f"Error: {e}")

    process.terminate()  # Ensure subprocess is terminated

# Example call to the function
if __name__ == "__main__":
    start_bluetooth()

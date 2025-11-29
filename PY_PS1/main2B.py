import json
import sys
import getpass
import subprocess
from typing import List, Dict, Any

# --- Dependency Check and Import ---
try:
    from tabulate import tabulate
except ImportError:
    print(f"\n[Dependency Error] The 'tabulate' library is required to display results. Please install it: 'pip install tabulate'", file=sys.stderr)
    sys.exit(1)


# --- Configuration ---
POWERSHELL_SCRIPT_PATH = "main2B.ps1"


# --- Console Coloring Utility ---
class ConsoleColors:
    """ANSI color codes for console output."""
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    DARK_GRAY = '\033[90m'
    WHITE = '\033[97m'
    ENDC = '\033[0m'

def print_colored(text: str, color: str, end: str = '\n'):
    """Prints text with the specified ANSI color."""
    sys.stdout.write(f"{color}{text}{ConsoleColors.ENDC}{end}")


# --- Helper Function for Table Display ---
def display_results_table(data: List[Dict[str, Any]]):
    """
    Formats and prints the list of AD user dictionaries into a clean, readable table.
    """
    if not data:
        print_colored("\nNo user data collected to display in table format.", ConsoleColors.YELLOW)
        return

    print_colored("\n--- Active Directory User Search Results (Tabulated) ---", ConsoleColors.BLUE)
    
    # Define headers and the order of keys for the table
    headers = [
        "Name", 
        "sAMAccountName", 
        "UserPrincipalName", 
        "IsDisabled"
    ]
    
    # Prepare the data for tabulate: a list of lists (rows)
    table_data = [
        [
            user.get("Name", "N/A"),
            user.get("SamAccountName", "N/A"),
            user.get("UserPrincipalName", "N/A"),
            # Format the boolean 'IsDisabled' for better readability
            "True" if user.get("IsDisabled", False) else "False"
        ]
        for user in data
    ]

    # Use 'fancy_grid' format for a clean, professional look
    print(tabulate(table_data, headers=headers, tablefmt="fancy_grid"))

    print_colored("------------------------------------------", ConsoleColors.DARK_GRAY)
    print_colored(f"Total Users Found: {len(data)}", ConsoleColors.GREEN)
    print_colored("------------------------------------------", ConsoleColors.DARK_GRAY)


# --- Subprocess-Based Active Directory Search Function (Calling PowerShell) ---
def search_ad_users(search_name: str, dc_ip: str) -> List[Dict[str, Any]]:
    """
    Executes the external PowerShell script to query Active Directory.
    """
    
    # Define the command array using -File to call the external script safely
    command = [
        "powershell.exe", 
        "-NoProfile", 
        "-ExecutionPolicy", "Bypass",
        "-File", POWERSHELL_SCRIPT_PATH, # Runs the external file
        "-SearchName", search_name,      # Passes parameters to the script
        "-DomainController", dc_ip
    ]

    try:
        print_colored(f"  --> Executing PowerShell script: {POWERSHELL_SCRIPT_PATH}...", ConsoleColors.DARK_GRAY)
        
        # Execute the command and capture output
        result = subprocess.run(
            command,
            capture_output=True,
            text=True, 
            check=True # Raise an exception for non-zero exit codes (signaling script failure)
        )

        json_output = result.stdout.strip()
        
        if not json_output:
            # Script successfully ran but returned no output (e.g., empty result set)
            return []

        # Parse the JSON string output by the PowerShell script
        users = json.loads(json_output)
        
        # Ensure 'users' is always a list for consistent processing
        if isinstance(users, dict):
            return [users]
        return users

    except subprocess.CalledProcessError as e:
        # Error handling now captures errors written to stderr by the script
        error_output = e.stderr.strip()
        print_colored(f"\n[Script Failure] PowerShell script returned an error:", ConsoleColors.RED)
        # Display the error from stderr for debugging
        print_colored(f"  --> Stderr: {error_output}", ConsoleColors.RED)
        return []
    except json.JSONDecodeError:
        print_colored(f"\n[Data Error] Failed to decode JSON from script output. Raw output: '{json_output[:100]}...'", ConsoleColors.RED)
        return []
    except FileNotFoundError as e:
        # Check if it's the script file or powershell.exe itself
        if POWERSHELL_SCRIPT_PATH in str(e):
             print_colored(f"\n[File Error] The required PowerShell script '{POWERSHELL_SCRIPT_PATH}' was not found. Ensure it is in the same directory.", ConsoleColors.RED)
        else:
             print_colored(f"\n[System Error] 'powershell.exe' not found. Ensure PowerShell is installed and in your PATH.", ConsoleColors.RED)
        return []


# --- Main Execution Block ---
def main():
    """Drives the user input, search loop, and displays results using tabulate."""
    print_colored("\n--- Active Directory User Search Tool (Python) ---", ConsoleColors.BLUE)
    print_colored(f"NOTE: Calling external PowerShell script: {POWERSHELL_SCRIPT_PATH}", ConsoleColors.YELLOW)


    # 1. Prompt for Domain Controller IP
    domain_controller_ip = input("Enter Domain Controller IP (e.g., 192.168.1.22): ").strip()
    
    # 2. Prompt for credentials (collected for UX but not used in subprocess call)
    username = input("Enter your domain username: ").strip()
    password = getpass.getpass("Enter your domain password (hidden): ")

    # 3. Prompt for search names
    search_names_input = input("Enter names separated by commas (e.g., Cadis, Neil, Modesto): ").strip()

    name_array = [name.strip() for name in search_names_input.split(',') if name.strip()]

    if not name_array:
        print_colored("Error: No search names provided. Exiting.", ConsoleColors.RED)
        return

    all_users_data = []

    # 4. Search Loop
    for name in name_array:
        print_colored(f"\nSearching for: {name}", ConsoleColors.CYAN)

        users = search_ad_users(name, domain_controller_ip)

        if not users:
            print_colored(f"No users found matching '{name}' via PowerShell query.", ConsoleColors.RED)
        else:
            for user in users:
                # 5. Create structured object for final JSON and Tabulate output
                enabled = user.get('Enabled', False) 
                
                # The keys here match the structure expected by the JSON output and display functions
                user_object = {
                    "Name": user.get('Name', 'N/A'),
                    "SamAccountName": user.get('SamAccountName', 'N/A'),
                    "UserPrincipalName": user.get('UserPrincipalName', 'N/A'),
                    "DistinguishedName": user.get('DistinguishedName', 'N/A'),
                    # Convert boolean 'Enabled' to 'IsDisabled' for final output structure
                    "IsDisabled": not enabled 
                }
                all_users_data.append(user_object)
    
    # --- Tabulate Display ---
    display_results_table(all_users_data)


    # 6. Final JSON Conversion and Display
    print_colored("\n=========================================================", ConsoleColors.WHITE)
    print_colored("           JSON OUTPUT (All Found Users)           ", ConsoleColors.YELLOW)
    print_colored("=========================================================", ConsoleColors.WHITE)

    try:
        json_output = json.dumps(
            all_users_data, 
            indent=4 
        )
        print(json_output) 
    except Exception as e:
        print_colored(f"Error converting results to JSON: {e}", ConsoleColors.RED)

    print_colored("\n=========================================================", ConsoleColors.WHITE)

if __name__ == "__main__":
    main()
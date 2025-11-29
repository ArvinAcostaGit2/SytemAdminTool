import json
import sys
import getpass
import subprocess
from typing import List, Dict, Any

# --- Console Coloring Utility ---
# Provides a simple way to mimic PowerShell's Write-Host -ForegroundColor
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


# --- Subprocess-Based Active Directory Account Disabler (Calling PowerShell) ---
def disable_ad_users(search_name: str, dc_ip: str) -> List[Dict[str, Any]]:
    """
    Executes a PowerShell command via subprocess to find users matching the search_name, 
    disable their AD accounts, and return the details of the disabled accounts.

    The PowerShell script performs Get-ADUser, pipes the results to Disable-ADAccount -PassThru, 
    and converts the resulting objects directly to JSON.

    CRITICAL NOTE: The execution context must have sufficient permissions to modify 
    Active Directory accounts (i.e., run Disable-ADAccount).
    """
    
    # 1. Construct the PowerShell script snippet
    # The script finds users, pipes them to Disable-ADAccount (-PassThru returns the object),
    # then selects properties and adds a confirmation 'Action' property.
    powershell_script = f"""
        Import-Module ActiveDirectory;
        Get-ADUser -Filter "Name -like '*{search_name}*'" -Server "{dc_ip}" |
        Disable-ADAccount -PassThru |
        Select-Object Name, SamAccountName, UserPrincipalName, DistinguishedName, @{{Name='Action'; Expression={{'Disabled'}}}}, @{{Name='WasEnabled'; Expression={{$_.Enabled}}}} |
        ConvertTo-Json -Compress
    """
    
    # 2. Define the command array
    command = [
        "powershell.exe", 
        "-NoProfile", 
        "-ExecutionPolicy", "Bypass",
        "-Command", 
        powershell_script
    ]

    try:
        # Use subprocess.run to execute the command and capture stdout
        print_colored(f"   --> Attempting to disable accounts using PowerShell...", ConsoleColors.DARK_GRAY)
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True, # Decode stdout/stderr as text
            check=True # Raise an exception for non-zero exit codes
        )

        json_output = result.stdout.strip()
        
        if not json_output or json_output.lower().startswith("no users found"):
            return []

        # 3. Parse the JSON string output by the PowerShell script
        users = json.loads(json_output)
        
        # Ensure 'users' is always a list for consistent processing
        if isinstance(users, dict):
            return [users]
        return users

    except subprocess.CalledProcessError as e:
        error_output = e.stderr.strip()
        
        if "Access is denied" in error_output or "insufficient access" in error_output:
            print_colored(f"\n[Authorization Error] Failed to disable accounts. Insufficient permissions on {dc_ip}.", ConsoleColors.RED)
        elif "Cannot find an object" in error_output:
            print_colored(f"\n[AD Error] DC {dc_ip} returned: {error_output}", ConsoleColors.RED)
        else:
            print_colored(f"\n[Subprocess Error] PowerShell command failed with exit code {e.returncode}.", ConsoleColors.RED)
            print_colored(f"  --> Stderr: {error_output}", ConsoleColors.RED)
        return []
    except json.JSONDecodeError:
        print_colored(f"\n[Data Error] Failed to decode JSON from PowerShell output. Raw output: '{json_output[:100]}...'", ConsoleColors.RED)
        return []
    except FileNotFoundError:
        print_colored(f"\n[System Error] 'powershell.exe' not found. Ensure PowerShell is installed and in your PATH.", ConsoleColors.RED)
        return []


# --- Main Execution Block ---
def main():
    """Drives the user input, disable loop, and JSON output."""
    print_colored("\n--- Active Directory Account DISABLER Tool (Python/PowerShell) ---", ConsoleColors.RED)
    print_colored("WARNING: This tool executes 'Disable-ADAccount' via subprocess.", ConsoleColors.YELLOW)


    # 1. Prompt for Domain Controller IP
    domain_controller_ip = input("Enter Domain Controller IP (e.g., 192.168.1.22): ").strip()
    
    # 2. Prompt for credentials (collected for UX/logging, but still relies on execution context permissions)
    username = input("Enter your domain username: ").strip()
    password = getpass.getpass("Enter your domain password (hidden): ")

    # 3. Prompt for search names
    search_names_input = input("Enter names separated by commas (e.g., Cadis, Neil, Modesto): ").strip()

    # Split input into an array and trim spaces, handling empty input gracefully
    name_array = [name.strip() for name in search_names_input.split(',') if name.strip()]

    if not name_array:
        print_colored("Error: No search names provided. Exiting.", ConsoleColors.RED)
        return

    all_users_data = []

    # 4. Action Loop: Disable Accounts
    for name in name_array:
        print_colored(f"\nProcessing for: {name}", ConsoleColors.CYAN)

        # Call the disabling function
        disabled_users = disable_ad_users(name, domain_controller_ip)

        if not disabled_users:
            print_colored(f"No accounts were disabled matching '{name}'.", ConsoleColors.RED)
        else:
            for user in disabled_users:
                # 5. Display interactive feedback
                print_colored("---------------------------------------------------------", ConsoleColors.DARK_GRAY)
                user_name = user.get('Name', 'N/A')
                sam_account = user.get('SamAccountName', 'N/A')
                upn = user.get('UserPrincipalName', 'N/A')
                action = user.get('Action', 'Failed')
                dn = user.get('DistinguishedName', 'N/A')
                was_enabled = user.get('WasEnabled', 'Unknown')

                print_colored(f"Account:             {user_name}", ConsoleColors.GREEN)
                print_colored(f"Logon Name (sAM):    {sam_account}", ConsoleColors.GREEN)
                print_colored(f"Action Status:       {action}", ConsoleColors.RED)
                print_colored(f"Was Enabled:         {was_enabled}", ConsoleColors.YELLOW)
                print_colored(f"Distinguished Name:  {dn}", ConsoleColors.CYAN)

                # 6. Create structured object for final JSON output (using the returned data)
                user_object = {
                    "Name": user_name,
                    "SamAccountName": sam_account,
                    "UserPrincipalName": upn,
                    "DistinguishedName": dn,
                    "Action": action,
                    "WasEnabledBefore": was_enabled
                }
                all_users_data.append(user_object)
            print_colored("---------------------------------------------------------", ConsoleColors.DARK_GRAY)

    # 7. Final JSON Conversion and Display
    print_colored("\n=========================================================", ConsoleColors.WHITE)
    print_colored("         JSON OUTPUT (All Accounts Targeted)   ", ConsoleColors.YELLOW)
    print_colored("=========================================================", ConsoleColors.WHITE)

    # Convert the collected list of dictionaries into a readable JSON string
    try:
        json_output = json.dumps(
            all_users_data, 
            indent=4 # Pretty-printing for human readability
        )
        print(json_output) # Print the raw JSON string
    except Exception as e:
        print_colored(f"Error converting results to JSON: {e}", ConsoleColors.RED)

    print_colored("\n=========================================================", ConsoleColors.WHITE)

if __name__ == "__main__":
    main()
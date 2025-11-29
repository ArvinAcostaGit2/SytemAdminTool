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


# --- Subprocess-Based Active Directory Search Function (Calling PowerShell) ---
def search_ad_users(search_name: str, dc_ip: str) -> List[Dict[str, Any]]:
    """
    Executes a PowerShell command via subprocess to query Active Directory.

    The PowerShell script performs Get-ADUser and converts the result directly to JSON.

    NOTE: The PowerShell command relies on the execution context having permissions
    to query the domain controller, as securely passing credentials via subprocess
    is generally not recommended.
    """
    
    # 1. Construct the PowerShell script snippet
    # Using Select-Object to explicitly shape the output object for reliable JSON parsing
    powershell_script = f"""
        Get-ADUser -Filter "Name -like '*{search_name}*'" -Server "{dc_ip}" `
            -Properties Enabled, DistinguishedName, UserPrincipalName, SamAccountName |
        Select-Object Name, SamAccountName, UserPrincipalName, DistinguishedName, @{{Name='Enabled'; Expression={{$_.Enabled}}}} |
        ConvertTo-Json -Compress
    """
    
    # 2. Define the command array
    # We use 'powershell.exe' (or 'pwsh.exe' for Core) and '-Command' to execute the script
    command = [
        "powershell.exe", 
        "-NoProfile", 
        "-ExecutionPolicy", "Bypass",
        "-Command", 
        powershell_script
    ]

    try:
        # Use subprocess.run to execute the command and capture stdout
        print_colored(f"   --> Executing PowerShell command...", ConsoleColors.DARK_GRAY)
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True, # Decode stdout/stderr as text
            check=True # Raise an exception for non-zero exit codes
        )

        json_output = result.stdout.strip()
        
        if not json_output or json_output.lower().startswith("no users found"):
            # Handle cases where the query results in no data or a custom message
            return []

        # 3. Parse the JSON string output by the PowerShell script
        # PowerShell ConvertTo-Json might return a single object or an array of objects.
        users = json.loads(json_output)
        
        # Ensure 'users' is always a list for consistent processing in the main loop
        if isinstance(users, dict):
            return [users]
        return users

    except subprocess.CalledProcessError as e:
        # Check for common AD errors (e.g., DC not reachable, access denied)
        error_output = e.stderr.strip()
        
        if "Access is denied" in error_output:
            print_colored(f"\n[Authorization Error] The current user does not have permission to query AD on {dc_ip}.", ConsoleColors.RED)
        elif "Cannot find an object" in error_output:
            # Sometimes AD returns an error instead of empty set if DC is specified incorrectly
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
    """Drives the user input, search loop, and JSON output."""
    print_colored("\n--- Active Directory User Search Tool (Python) ---", ConsoleColors.BLUE)
    print_colored("NOTE: Using 'subprocess' to execute PowerShell's Get-ADUser.", ConsoleColors.YELLOW)


    # 1. Prompt for Domain Controller IP
    domain_controller_ip = input("Enter Domain Controller IP (e.g., 192.168.1.22): ").strip()
    
    # 2. Prompt for credentials (collected for UX but not used in subprocess call)
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

    # 4. Search Loop
    for name in name_array:
        print_colored(f"\nSearching for: {name}", ConsoleColors.CYAN)

        # The search_ad_users function now executes PowerShell
        users = search_ad_users(name, domain_controller_ip)

        if not users:
            print_colored(f"No users found matching '{name}' via PowerShell query.", ConsoleColors.RED)
        else:
            for user in users:
                # 5. Display interactive feedback (mimicking PowerShell's Write-Host)
                print_colored("---------------------------------------------------------", ConsoleColors.DARK_GRAY)
                # Use .get() for safer access to fields retrieved from the external JSON
                user_name = user.get('Name', 'N/A')
                sam_account = user.get('SamAccountName', 'N/A')
                upn = user.get('UserPrincipalName', 'N/A')
                # 'Enabled' is a boolean from PowerShell JSON
                enabled = user.get('Enabled', False) 
                distinguished_name = user.get('DistinguishedName', 'N/A')

                print_colored(f"User Name:           {user_name}", ConsoleColors.GREEN)
                print_colored(f"Logon Name (sAM):    {sam_account}", ConsoleColors.GREEN)
                print_colored(f"NT Account (UPN):    {upn}", ConsoleColors.GREEN)
                print_colored(f"Enabled:             {enabled}", ConsoleColors.YELLOW)
                print_colored(f"Distinguished Name:  {distinguished_name}", ConsoleColors.CYAN)

                # 6. Create structured object for final JSON output
                user_object = {
                    "Name": user_name,
                    "SamAccountName": sam_account,
                    "UserPrincipalName": upn,
                    "DistinguishedName": distinguished_name,
                    # Convert boolean 'Enabled' to 'IsDisabled' as required by original spec
                    "IsDisabled": not enabled 
                }
                all_users_data.append(user_object)
            print_colored("---------------------------------------------------------", ConsoleColors.DARK_GRAY)

    # 7. Final JSON Conversion and Display
    print_colored("\n=========================================================", ConsoleColors.WHITE)
    print_colored("         JSON OUTPUT (All Found Users)         ", ConsoleColors.YELLOW)
    print_colored("=========================================================", ConsoleColors.WHITE)

    # Convert the collected list of dictionaries into a readable JSON string
    try:
        # --- MODIFIED: Used indent=4 for pretty-printing ---
        json_output = json.dumps(
            all_users_data, 
            indent=4 # Use 4 spaces for indentation for readability
        )
        print(json_output) # Print the raw JSON string
    except Exception as e:
        print_colored(f"Error converting results to JSON: {e}", ConsoleColors.RED)

    print_colored("\n=========================================================", ConsoleColors.WHITE)

if __name__ == "__main__":
    main()
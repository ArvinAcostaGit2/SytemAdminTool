from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import subprocess
import json
import uvicorn
import os
import sqlite3
from datetime import datetime
from contextlib import contextmanager

# Initialize FastAPI app
app = FastAPI(
    title="Active Directory User Search API",
    description="Web-based AD user search tool with bulk operations",
    version="3.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

# SQLite Database Configuration
DB_DIR = "db"
DB_PATH = f"{DB_DIR}/user_operations.db"

# ============================================
# Database Functions
# ============================================

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_database():
    """Initialize SQLite database with all required tables"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Table for disabled accounts (existing)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS disabled_accounts (
                idx INTEGER PRIMARY KEY AUTOINCREMENT,
                EID TEXT,
                Program TEXT,
                ticket_number TEXT NOT NULL,
                name TEXT NOT NULL,
                sam_account_name TEXT NOT NULL,
                user_principal_name TEXT,
                domain_username TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # NEW: Table for account actions (reset password, unlock)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_actions_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT NOT NULL,
                sam_account_name TEXT NOT NULL,
                reference TEXT NOT NULL,
                domain_user TEXT NOT NULL,
                additional_details TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Old table for general operations (kept for backward compatibility)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sam_account_name TEXT NOT NULL,
                name TEXT,
                user_principal_name TEXT,
                distinguished_name TEXT,
                operation_type TEXT NOT NULL,
                performed_by TEXT,
                is_disabled BOOLEAN,
                was_locked BOOLEAN,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                notes TEXT
            )
        """)
        
        # Indexes for disabled_accounts
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ticket_number 
            ON disabled_accounts(ticket_number)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sam_account_disabled 
            ON disabled_accounts(sam_account_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp_disabled 
            ON disabled_accounts(timestamp)
        """)
        
        # Indexes for account_actions_log
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_action_type 
            ON account_actions_log(action_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sam_account_actions 
            ON account_actions_log(sam_account_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp_actions 
            ON account_actions_log(timestamp)
        """)
        
        # Indexes for user_operations
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sam_account 
            ON user_operations(sam_account_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON user_operations(timestamp)
        """)
        
        print(f"✅ Database initialized: {DB_PATH}")

os.makedirs(DB_DIR, exist_ok=True)
init_database()


# ============================================
# Pydantic Models
# ============================================

class ADSearchRequest(BaseModel):
    domain_controller_ip: str = Field(..., description="Domain Controller IP address")
    username: str = Field(..., description="Domain username for authentication")
    password: str = Field(..., description="Domain password for authentication")
    raw_search_input: str = Field(..., description="Raw multiline, comma-separated search input from the user")

class ADUserResponse(BaseModel):
    Name: str
    SamAccountName: str
    UserPrincipalName: str
    DistinguishedName: str
    IsDisabled: bool
    IsLocked: bool
    CustomField1: Optional[str] = None 
    CustomField2: Optional[str] = None
    CustomField3: Optional[str] = None
    CustomField4: Optional[str] = None

class ADSearchResponse(BaseModel):
    success: bool
    total_users: int
    users: List[ADUserResponse]
    errors: Optional[List[str]] = None

class SaveToDbRequest(BaseModel):
    users: List[Dict[str, Any]]
    performed_by: str

class BulkDisableRequest(BaseModel):
    domain_controller_ip: str
    username: str
    password: str
    user_accounts: List[str]
    ticket_number: str
    user_details: List[Dict[str, Any]]

class UnlockUserRequest(BaseModel):
    domain_controller_ip: str
    username: str
    password: str
    sam_account_name: str
    reference: str

class ResetPasswordRequest(BaseModel):
    domain_controller_ip: str
    username: str
    password: str
    sam_account_name: str
    new_password: str
    is_temporary: bool
    reference: str


# ============================================
# PowerShell Execution Functions
# ============================================

def execute_powershell_ad_query(
    search_name: str, 
    dc_ip: str, 
    username: str, 
    password: str
) -> List[Dict[str, Any]]:
    """
    Executes PowerShell Get-ADUser command with LockedOut property.
    Searches both Name and sAMAccountName fields.
    Returns list of user dictionaries or empty list on failure.
    """
    
    powershell_script = f"""
        $SecurePassword = ConvertTo-SecureString '{password}' -AsPlainText -Force
        $Credential = New-Object System.Management.Automation.PSCredential('{username}', $SecurePassword)
        
        try {{
            Get-ADUser -Filter "Name -like '*{search_name}*' -or sAMAccountName -like '*{search_name}*'" -Server "{dc_ip}" -Credential $Credential `
                -Properties Enabled, DistinguishedName, UserPrincipalName, SamAccountName, LockedOut |
            Select-Object Name, SamAccountName, UserPrincipalName, DistinguishedName, 
                @{{Name='Enabled'; Expression={{$_.Enabled}}}},
                @{{Name='LockedOut'; Expression={{$_.LockedOut}}}} |
            ConvertTo-Json -Compress
        }} catch {{
            Write-Error $_.Exception.Message
            exit 1
        }}
    """
    
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        powershell_script
    ]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            raise Exception(f"PowerShell error: {error_msg}")
        
        json_output = result.stdout.strip()
        
        if not json_output or json_output.lower().startswith("no users found"):
            return []
        
        users = json.loads(json_output)
        
        if isinstance(users, dict):
            return [users]
        return users
        
    except subprocess.TimeoutExpired:
        raise Exception(f"PowerShell command timed out after 30 seconds")
    except json.JSONDecodeError as e:
        if json_output:
            return []
        raise Exception(f"Failed to parse PowerShell JSON output: {str(e)}")
    except FileNotFoundError:
        raise Exception("PowerShell not found. Ensure PowerShell is installed and in PATH")
    except Exception as e:
        raise Exception(f"Query failed: {str(e)}")


def execute_bulk_disable_users(
    user_accounts: List[str],
    dc_ip: str,
    username: str,
    password: str
) -> List[Dict[str, Any]]:
    """
    Disables multiple AD user accounts.
    Returns list of results with success/failure status.
    """
    
    users_array = ",".join([f"'{user}'" for user in user_accounts])
    
    powershell_script = f"""
        $SecurePassword = ConvertTo-SecureString '{password}' -AsPlainText -Force
        $Credential = New-Object System.Management.Automation.PSCredential('{username}', $SecurePassword)
        
        $users = @({users_array})
        $results = @()
        
        foreach ($user in $users) {{
            try {{
                Disable-ADAccount -Identity $user -Server "{dc_ip}" -Credential $Credential -ErrorAction Stop
                $results += [PSCustomObject]@{{
                    user = $user
                    success = $true
                    error = $null
                }}
            }} catch {{
                $results += [PSCustomObject]@{{
                    user = $user
                    success = $false
                    error = $_.Exception.Message
                }}
            }}
        }}
        
        $results | ConvertTo-Json -Compress
    """
    
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        powershell_script
    ]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        json_output = result.stdout.strip()
        
        if not json_output:
            raise Exception("No output from PowerShell bulk disable command")
        
        results = json.loads(json_output)
        
        if isinstance(results, dict):
            return [results]
        return results
        
    except subprocess.TimeoutExpired:
        raise Exception("Bulk disable operation timed out")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse bulk disable results: {str(e)}")
    except Exception as e:
        raise Exception(f"Bulk disable failed: {str(e)}")


def execute_unlock_user(
    sam_account_name: str,
    dc_ip: str,
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Unlocks a single AD user account.
    Returns success status and message.
    """
    
    powershell_script = f"""
        $SecurePassword = ConvertTo-SecureString '{password}' -AsPlainText -Force
        $Credential = New-Object System.Management.Automation.PSCredential('{username}', $SecurePassword)
        
        try {{
            Unlock-ADAccount -Identity "{sam_account_name}" -Server "{dc_ip}" -Credential $Credential -ErrorAction Stop
            Write-Output "SUCCESS"
        }} catch {{
            Write-Error $_.Exception.Message
            exit 1
        }}
    """
    
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        powershell_script
    ]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            return {
                "success": False,
                "message": f"Failed to unlock user: {error_msg}"
            }
        
        return {
            "success": True,
            "message": f"User {sam_account_name} unlocked successfully"
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Unlock operation timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unlock failed: {str(e)}"
        }

# ============================================
def execute_reset_password_old(
    sam_account_name: str,
    new_password: str,
    is_temporary: bool,
    dc_ip: str,
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Resets AD user password.
    is_temporary: True = user must change at next logon, False = permanent password
    Returns success status and message.
    """
    
    # Escape single quotes in the new password for PowerShell
    escaped_password = new_password.replace("'", "''")
    
    change_at_logon = "true" if is_temporary else "false"
    
    powershell_script = f"""
        $SecurePassword = ConvertTo-SecureString '{password}' -AsPlainText -Force
        $Credential = New-Object System.Management.Automation.PSCredential('{username}', $SecurePassword)
        
        $NewPassword = ConvertTo-SecureString '{escaped_password}' -AsPlainText -Force
        
        try {{
            Set-ADAccountPassword -Identity "{sam_account_name}" -NewPassword $NewPassword -Server "{dc_ip}" -Credential $Credential -Reset -ErrorAction Stop
            
            if ({change_at_logon}) {{
                Set-ADUser -Identity "{sam_account_name}" -ChangePasswordAtLogon $true -Server "{dc_ip}" -Credential $Credential -ErrorAction Stop
            }} else {{
                Set-ADUser -Identity "{sam_account_name}" -ChangePasswordAtLogon $false -Server "{dc_ip}" -Credential $Credential -ErrorAction Stop
            }}
            
            Write-Output "SUCCESS"
        }} catch {{
            Write-Error $_.Exception.Message
            exit 1
        }}
    """
    
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        powershell_script
    ]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            return {
                "success": False,
                "message": f"Failed to reset password: {error_msg}"
            }
        
        password_type = "temporary (must change at next logon)" if is_temporary else "permanent"
        return {
            "success": True,
            "message": f"Password reset successfully for {sam_account_name} ({password_type})"
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Password reset operation timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Password reset failed: {str(e)}"
        }
# ============================================

def execute_reset_password(
    sam_account_name: str,
    new_password: str,
    is_temporary: bool,
    dc_ip: str,
    username: str,
    password: str
) -> Dict[str, Any]:
    """
    Resets AD user password.
    Uses Base64 encoding to safely pass passwords with special characters.
    """
    
    import base64
    
    # Encode passwords to Base64 to avoid PowerShell escaping issues
    admin_password_b64 = base64.b64encode(password.encode('utf-16le')).decode('ascii')
    new_password_b64 = base64.b64encode(new_password.encode('utf-16le')).decode('ascii')
    
    change_at_logon = "true" if is_temporary else "false"
    
    powershell_script = f"""
        # Decode Base64 passwords
        $AdminPasswordBytes = [System.Convert]::FromBase64String('{admin_password_b64}')
        $AdminPassword = [System.Text.Encoding]::Unicode.GetString($AdminPasswordBytes)
        $SecurePassword = ConvertTo-SecureString $AdminPassword -AsPlainText -Force
        
        $NewPasswordBytes = [System.Convert]::FromBase64String('{new_password_b64}')
        $NewPasswordPlain = [System.Text.Encoding]::Unicode.GetString($NewPasswordBytes)
        $NewPassword = ConvertTo-SecureString $NewPasswordPlain -AsPlainText -Force
        
        $Credential = New-Object System.Management.Automation.PSCredential('{username}', $SecurePassword)
        
        try {{
            Set-ADAccountPassword -Identity "{sam_account_name}" -NewPassword $NewPassword -Server "{dc_ip}" -Credential $Credential -Reset -ErrorAction Stop
            
            if ({change_at_logon}) {{
                Set-ADUser -Identity "{sam_account_name}" -ChangePasswordAtLogon $true -Server "{dc_ip}" -Credential $Credential -ErrorAction Stop
            }} else {{
                Set-ADUser -Identity "{sam_account_name}" -ChangePasswordAtLogon $false -Server "{dc_ip}" -Credential $Credential -ErrorAction Stop
            }}
            
            Write-Output "SUCCESS"
        }} catch {{
            Write-Error $_.Exception.Message
            exit 1
        }}
    """
    
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        powershell_script
    ]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            return {
                "success": False,
                "message": f"Failed to reset password: {error_msg}"
            }
        
        password_type = "temporary (must change at next logon)" if is_temporary else "permanent"
        return {
            "success": True,
            "message": f"Password reset successfully for {sam_account_name} ({password_type})"
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "message": "Password reset operation timed out"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Password reset failed: {str(e)}"
        }







# ============================================
# Credentials Endpoint
# ============================================

CREDS_FILE = "creds.json"

@app.get("/api/credentials")
async def get_credentials():
    """Retrieve the list of AD credentials from the JSON file."""
    if not os.path.exists(CREDS_FILE):
        dummy_creds = [
            {"Program": "Demo Domain", "DomainControllerIP": "192.168.1.1", "DomainUsername": "DOMAIN\\demo_user", "DomainPassword": "password123"}
        ]
        with open(CREDS_FILE, 'w') as f:
            json.dump(dummy_creds, f, indent=4)
        
    try:
        with open(CREDS_FILE, 'r') as f:
            creds = json.load(f)
        return creds
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"Error decoding JSON from '{CREDS_FILE}'.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


# ============================================
# API Endpoints
# ============================================

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main HTML page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/search-users", response_model=ADSearchResponse)
async def search_ad_users(request: ADSearchRequest):
    """
    Main API endpoint for AD user search.
    Parses the raw input and merges custom fields with AD data.
    """
    
    all_users_data = []
    errors = []
    
    lines = [line.strip() for line in request.raw_search_input.split('\n') if line.strip()]
    
    if not lines:
        raise HTTPException(status_code=400, detail="No search input provided")
    
    if not request.domain_controller_ip or not request.username or not request.password:
        raise HTTPException(status_code=400, detail="Missing required credentials")
    
    for line in lines:
        parts = [p.strip() for p in line.split(',')]
        
        if len(parts) < 2 or not parts[1]:
            errors.append(f"Skipping line '{line}': Search term (second part) is missing or empty.")
            continue
            
        custom_field1 = parts[0] if len(parts) > 0 else None
        search_name = parts[1]
        custom_field2 = parts[2] if len(parts) > 2 else None
        custom_field3 = parts[3] if len(parts) > 3 else None
        
        try:
            users = execute_powershell_ad_query(
                search_name=search_name,
                dc_ip=request.domain_controller_ip,
                username=request.username,
                password=request.password
            )
            
            if users:
                for user in users:
                    enabled = user.get('Enabled', False)
                    locked_out = user.get('LockedOut', False)
                    
                    user_object = {
                        "Name": user.get('Name', 'N/A'),
                        "SamAccountName": user.get('SamAccountName', search_name),
                        "UserPrincipalName": user.get('UserPrincipalName', 'N/A'),
                        "DistinguishedName": user.get('DistinguishedName', 'N/A'),
                        "IsDisabled": not enabled,
                        "IsLocked": locked_out,
                        "CustomField1": custom_field1,
                        "CustomField2": custom_field2,
                        "CustomField3": custom_field3,
                        "CustomField4": search_name
                    }
                    all_users_data.append(user_object)
            else:
                all_users_data.append({
                    "Name": "USER NOT FOUND",
                    "SamAccountName": search_name,
                    "UserPrincipalName": "N/A",
                    "DistinguishedName": "N/A",
                    "IsDisabled": True,
                    "IsLocked": False,
                    "CustomField1": custom_field1,
                    "CustomField2": custom_field2,
                    "CustomField3": custom_field3,
                    "CustomField4": search_name
                })
                errors.append(f"No AD user found matching search term '{search_name}' from input line: '{line}'")
                
        except Exception as e:
            error_msg = f"Error searching '{search_name}' from line '{line}': {str(e)}"
            errors.append(error_msg)
            all_users_data.append({
                "Name": "SEARCH FAILED",
                "SamAccountName": search_name,
                "UserPrincipalName": "N/A",
                "DistinguishedName": "N/A",
                "IsDisabled": True, 
                "IsLocked": False,
                "CustomField1": custom_field1,
                "CustomField2": custom_field2,
                "CustomField3": custom_field3,
                "CustomField4": search_name
            })
    
    return ADSearchResponse(
        success=len(errors) == 0,
        total_users=len(all_users_data),
        users=all_users_data,
        errors=errors if errors else None
    )


@app.post("/api/save-to-database")
async def save_to_database(request: SaveToDbRequest):
    """
    Save selected users to SQLite database for audit/recording purposes.
    """
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            saved_count = 0
            for user in request.users:
                cursor.execute("""
                    INSERT INTO user_operations 
                    (sam_account_name, name, user_principal_name, distinguished_name, 
                     operation_type, performed_by, is_disabled, was_locked)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user.get('SamAccountName'),
                    user.get('Name'),
                    user.get('UserPrincipalName'),
                    user.get('DistinguishedName'),
                    'RECORDED',
                    request.performed_by,
                    user.get('IsDisabled', False),
                    user.get('IsLocked', False)
                ))
                saved_count += 1
            
        return {
            "success": True,
            "message": f"Successfully saved {saved_count} user(s) to database",
            "count": saved_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )


@app.post("/api/bulk-disable-users")
async def bulk_disable_users(request: BulkDisableRequest):
    """
    Disable multiple AD user accounts in bulk with ticket number tracking.
    Saves to disabled_accounts table.
    """
    
    if not request.user_accounts:
        raise HTTPException(status_code=400, detail="No user accounts provided")
    
    if not request.ticket_number:
        raise HTTPException(status_code=400, detail="Ticket number is required")
    
    try:
        results = execute_bulk_disable_users(
            user_accounts=request.user_accounts,
            dc_ip=request.domain_controller_ip,
            username=request.username,
            password=request.password
        )
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for result in results:
                if result['success']:
                    user_detail = next(
                        (u for u in request.user_details if u['SamAccountName'] == result['user']),
                        None
                    )
                    
                    if user_detail:
                        cursor.execute("""
                            INSERT INTO disabled_accounts 
                            (EID, Program, ticket_number, name, sam_account_name, 
                             user_principal_name, domain_username, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """, (
                            user_detail.get('CustomField1'),
                            user_detail.get('CustomField3'),
                            request.ticket_number,
                            user_detail.get('Name'),
                            user_detail.get('SamAccountName'),
                            user_detail.get('UserPrincipalName'),
                            request.username
                        ))
        
        success_count = sum(1 for r in results if r['success'])
        failed_count = len(results) - success_count
        
        return {
            "success": failed_count == 0,
            "total": len(results),
            "succeeded": success_count,
            "failed": failed_count,
            "results": results,
            "ticket_number": request.ticket_number
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Bulk disable operation failed: {str(e)}"
        )


@app.post("/api/unlock-user")
async def unlock_user(request: UnlockUserRequest):
    """
    Unlock a single AD user account with reference tracking.
    Logs to account_actions_log table.
    """
    
    try:
        result = execute_unlock_user(
            sam_account_name=request.sam_account_name,
            dc_ip=request.domain_controller_ip,
            username=request.username,
            password=request.password
        )
        
        # Log to database
        if result['success']:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO account_actions_log 
                    (action_type, sam_account_name, reference, domain_user, timestamp)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    'UNLOCK_ACCOUNT',
                    request.sam_account_name,
                    request.reference,
                    request.username
                ))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unlock operation failed: {str(e)}"
        )


@app.post("/api/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Reset AD user password with temporary/permanent option.
    Logs to account_actions_log table (NO PASSWORD STORED).
    """
    
    try:
        result = execute_reset_password(
            sam_account_name=request.sam_account_name,
            new_password=request.new_password,
            is_temporary=request.is_temporary,
            dc_ip=request.domain_controller_ip,
            username=request.username,
            password=request.password
        )
        
        # Log to database (NO PASSWORD STORED - SECURITY)
        if result['success']:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Store metadata about password type, NOT the actual password
                additional_details = json.dumps({
                    "password_type": "temporary" if request.is_temporary else "permanent",
                    "change_at_logon": request.is_temporary
                })
                
                cursor.execute("""
                    INSERT INTO account_actions_log 
                    (action_type, sam_account_name, reference, domain_user, additional_details, timestamp)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    'RESET_PASSWORD',
                    request.sam_account_name,
                    request.reference,
                    request.username,
                    additional_details
                ))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Password reset operation failed: {str(e)}"
        )


@app.get("/api/database-records")
async def get_database_records(limit: int = 100):
    """
    Retrieve recent database records for audit purposes.
    """
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM user_operations 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            
            records = []
            for row in rows:
                # Parse additional_details if it exists
                additional = None
                if row['additional_details']:
                    try:
                        additional = json.loads(row['additional_details'])
                    except:
                        additional = row['additional_details']
                
                records.append({
                    "id": row['id'],
                    "action_type": row['action_type'],
                    "sam_account_name": row['sam_account_name'],
                    "reference": row['reference'],
                    "domain_user": row['domain_user'],
                    "additional_details": additional,
                    "timestamp": row['timestamp']
                })
            
        return {
            "success": True,
            "count": len(records),
            "records": records
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database query failed: {str(e)}"
        )


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AD User Search API",
        "version": "3.0.0",
        "database": "connected" if os.path.exists(DB_PATH) else "not initialized"
    }


# Run the application
if __name__ == "__main__":
    os.makedirs("templates", exist_ok=True)
    os.makedirs(DB_DIR, exist_ok=True)
    
    print("\n" + "="*60)
    print("🚀 Active Directory User Management Tool")
    print("="*60)
    print(f"📊 Database: {DB_PATH}")
    print(f"🌐 Server: http://localhost:8956")
    print(f"📖 API Docs: http://localhost:8956/docs")
    print("="*60 + "\n")
    
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8956, 
        reload=True,
        log_level="info"
    )
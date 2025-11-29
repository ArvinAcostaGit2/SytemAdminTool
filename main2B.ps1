# Get-ADUserInfo.ps1

<#
.SYNOPSIS
    Queries Active Directory for user information based on a search name.
.PARAMETER SearchName
    The partial name to search for (wildcards are added internally).
.PARAMETER DomainController
    The IP address or FQDN of the Domain Controller to query.
.OUTPUTS
    A compressed JSON string containing a list of user objects.
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$SearchName,

    [Parameter(Mandatory=$true)]
    [string]$DomainController
)

# Use error handling in the script for cleaner output capture
try {
    # 1. Perform the Active Directory lookup using the passed parameters
    $Users = Get-ADUser -Filter "Name -like '*$SearchName*'" -Server $DomainController `
        -Properties Enabled, DistinguishedName, UserPrincipalName, SamAccountName `
        -ErrorAction Stop # Stop on any non-terminating AD error

    # 2. Shape the output and ensure the 'Enabled' property is a consistent boolean
    $FormattedUsers = $Users | Select-Object Name, SamAccountName, UserPrincipalName, DistinguishedName, @{Name='Enabled'; Expression={$_.Enabled}}

    if ($FormattedUsers -eq $null -or $FormattedUsers.Count -eq 0) {
        # Return an empty array if no users are found
        @() | ConvertTo-Json -Compress
    } else {
        # Convert the resulting objects directly to compressed JSON for Python consumption
        $FormattedUsers | ConvertTo-Json -Compress
    }

} catch {
    # If any error occurred (e.g., access denied, DC unreachable), write the message to stderr
    # Python captures stderr via subprocess.run()
    Write-Error $_.Exception.Message
    # Output an empty JSON array to stdout so Python doesn't crash trying to parse a message
    @() | ConvertTo-Json -Compress
    exit 1 # Exit with a non-zero code to signal failure to Python
}
# Preview group membership changes against a local directory export.
# Dry-run is the default. -Apply writes an updated directory JSON to -OutputPath.
# This script does not call a network API.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DesiredPath,

    [Parameter(Mandatory = $true)]
    [string]$ExportPath,

    [switch]$Apply,

    [string]$OutputPath,

    [string]$LogPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Log {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message,
        [string]$Level = 'INFO'
    )
    $line = '{0} {1} {2}' -f (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssK'), $Level, $Message
    Write-Host $line
    if ($LogPath) {
        $parent = Split-Path -Parent $LogPath
        if ($parent -and -not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent | Out-Null
        }
        Add-Content -LiteralPath $LogPath -Value $line -Encoding utf8
    }
}

function Read-GroupMap {
    param([Parameter(Mandatory = $true)][string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "File not found: $Path"
    }
    $document = Get-Content -LiteralPath $Path -Raw -Encoding utf8 | ConvertFrom-Json
    if ($null -eq $document.groups) {
        throw "$Path must contain a groups object"
    }
    $map = @{}
    foreach ($property in $document.groups.PSObject.Properties) {
        $members = New-Object System.Collections.Generic.List[string]
        if ($null -ne $property.Value) {
            foreach ($member in @($property.Value)) {
                if ($member -isnot [string]) {
                    throw "$Path members of $($property.Name) must be strings"
                }
                $members.Add($member)
            }
        }
        $map[$property.Name] = $members
    }
    return $map
}

function Get-Sorted {
    param($Values)
    return @($Values | Sort-Object)
}

function ConvertTo-DirectoryJson {
    param($Names, $MemberMap)
    $chunks = New-Object System.Collections.Generic.List[string]
    foreach ($name in $Names) {
        $members = New-Object System.Collections.Generic.List[string]
        foreach ($member in @($MemberMap[$name])) {
            if ([string]::IsNullOrEmpty($member)) { continue }
            $escaped = ($member -replace '\\', '\\') -replace '"', '\"'
            $members.Add('"' + $escaped + '"')
        }
        $body = [string]::Join(', ', $members.ToArray())
        $safeName = ($name -replace '\\', '\\') -replace '"', '\"'
        $chunks.Add('    "' + $safeName + '": [' + $body + ']')
    }
    $inner = [string]::Join(",`n", $chunks.ToArray())
    return "{`n  `"groups`": {`n$inner`n  }`n}"
}

try {
    if ($Apply -and -not $OutputPath) {
        throw '-Apply requires -OutputPath'
    }

    $desired = Read-GroupMap -Path $DesiredPath
    $live = Read-GroupMap -Path $ExportPath
    $lines = New-Object System.Collections.Generic.List[string]
    $changeCount = 0

    foreach ($name in (Get-Sorted $desired.Keys)) {
        $want = @($desired[$name])
        $have = @()
        if ($live.ContainsKey($name)) {
            $have = @($live[$name])
        }
        $add = @(Get-Sorted ($want | Where-Object { $have -notcontains $_ }))
        $remove = @(Get-Sorted ($have | Where-Object { $want -notcontains $_ }))
        if ($add.Count -gt 0 -or $remove.Count -gt 0) {
            $changeCount++
            $lines.Add($name)
            foreach ($member in $add) {
                $lines.Add("  add $member")
                Write-Log -Message "add $member to $name"
            }
            foreach ($member in $remove) {
                $lines.Add("  remove $member")
                Write-Log -Message "remove $member from $name"
            }
        }
    }

    if ($changeCount -eq 0) {
        $lines.Add('No membership changes.')
    }

    foreach ($name in (Get-Sorted $live.Keys)) {
        if (-not $desired.ContainsKey($name)) {
            $lines.Add("unmanaged $name")
            Write-Log -Message "unmanaged group $name"
        }
    }

    if ($Apply) {
        $updated = [ordered]@{}
        $names = New-Object System.Collections.Generic.List[string]
        foreach ($name in $live.Keys) { $names.Add($name) }
        foreach ($name in $desired.Keys) {
            if (-not $updated.Contains($name) -and -not $live.ContainsKey($name)) {
                $names.Add($name)
            }
        }
        foreach ($name in (Get-Sorted $names)) {
            if ($desired.ContainsKey($name)) {
                $updated[$name] = @(Get-Sorted $desired[$name])
            }
            else {
                $updated[$name] = @(Get-Sorted $live[$name])
            }
        }
        $payload = ConvertTo-DirectoryJson -Names (Get-Sorted $updated.Keys) -MemberMap $updated
        $parent = Split-Path -Parent $OutputPath
        if ($parent -and -not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent | Out-Null
        }
        Set-Content -LiteralPath $OutputPath -Value $payload -Encoding utf8
        $lines.Add('wrote the updated directory')
        Write-Log -Message "wrote $OutputPath"
    }
    else {
        $lines.Add('dry-run: no file written')
        Write-Log -Message 'dry-run: no file written'
    }

    $lines | ForEach-Object { Write-Output $_ }
    exit 0
}
catch {
    Write-Log -Message $_.Exception.Message -Level 'ERROR'
    Write-Host $_.Exception.Message
    exit 2
}

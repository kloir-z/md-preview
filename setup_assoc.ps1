<#
.SYNOPSIS
  Associate .md files with md-preview (double-click -> start server -> open in browser).

.DESCRIPTION
  Points the existing .md association command at md_open.pyw via pyw.exe (the Python
  launcher), so:
    - No console window appears (pyw.exe is windowless).
    - The existing UserChoice is reused, so this does not trip Windows 11's UserChoice
      hash protection and no "How do you want to open this?" dialog is shown.
  md_open.pyw itself starts the server if it is not running, otherwise reuses it.

.PARAMETER Unregister
  Remove the association (delete the .md UserChoice; Explorer falls back to its default).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File setup_assoc.ps1
  powershell -ExecutionPolicy Bypass -File setup_assoc.ps1 -Unregister

.NOTES
  To switch to another app instead, right-click a .md file in Explorer ->
  "Open with" -> "Choose another app" -> check "Always" -> pick any app.
  That selection becomes the new UserChoice and takes precedence (i.e. undoes this).
#>
param([switch]$Unregister)

$ErrorActionPreference = 'Stop'

$root     = Split-Path -Parent $MyInvocation.MyCommand.Path
$opener   = Join-Path $root 'md_open.pyw'
$launcher = Join-Path $env:WINDIR 'pyw.exe'   # version-independent Python launcher

# ProgId the current .md association points to (reuse the existing UserChoice target)
$cmdKey     = 'HKCU:\Software\Classes\Applications\md_open.bat\shell\open\command'
$userChoice = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.md\UserChoice'

function Invoke-ShellRefresh {
    # SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, 0, 0) -> tell Explorer to refresh
    $sig = '[System.Runtime.InteropServices.DllImport("shell32.dll")] public static extern void SHChangeNotify(int eventId, int flags, System.IntPtr item1, System.IntPtr item2);'
    $t = Add-Type -MemberDefinition $sig -Name 'ShellApi' -Namespace 'MdPreview' -PassThru
    $t::SHChangeNotify(0x08000000, 0x0000, [System.IntPtr]::Zero, [System.IntPtr]::Zero)
}

if ($Unregister) {
    if (Test-Path $userChoice) {
        Remove-Item $userChoice -Recurse -Force
        Write-Host '[unregister] Removed .md UserChoice. Explorer falls back to its default handler.'
    } else {
        Write-Host '[unregister] No UserChoice found (already unset).'
    }
    Invoke-ShellRefresh
    Write-Host 'Done. Use Explorer right-click > "Open with" to pick another app.'
    return
}

# --- register ---
if (-not (Test-Path $launcher)) { throw "pyw.exe not found: $launcher" }
if (-not (Test-Path $opener))   { throw "md_open.pyw not found: $opener" }

$command = '"{0}" "{1}" "%1"' -f $launcher, $opener

New-Item -Path $cmdKey -Force | Out-Null
Set-ItemProperty -Path $cmdKey -Name '(default)' -Value $command

Invoke-ShellRefresh

Write-Host '[register] Updated .md association command:'
Write-Host "        $command"
Write-Host 'Double-clicking a .md file now starts the server if needed and opens it (no window).'

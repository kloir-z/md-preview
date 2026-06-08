@echo off
rem md_open.bat - Markdown opener (fallback launcher)
rem
rem Alternative for environments where .vbs is blocked (security policy / WScript off).
rem Tries pythonw -> python -> py -3 to launch md_open.pyw.
rem With pythonw there is no window; if it falls back to python.exe a console window
rem flashes briefly. For a fully hidden launch, use md_open.vbs instead.
rem
rem Keep this file ASCII-only: cmd.exe reads .bat in the console code page, so
rem non-ASCII comments get mangled and can break parsing.

setlocal
set "DIR=%~dp0"

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%DIR%md_open.pyw" %*
    goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    start "" python "%DIR%md_open.pyw" %*
    goto :eof
)

where py >nul 2>nul
if %errorlevel%==0 (
    start "" py -3 "%DIR%md_open.pyw" %*
    goto :eof
)

echo Python not found. One of pythonw / python / py must be on PATH.
pause

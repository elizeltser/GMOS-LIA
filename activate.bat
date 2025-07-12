REM @echo off

set SCRIPT_DIR=%~dp0
set "venvActivatePath=%~dp0..\gmos_lia_venv\Scripts\Activate.ps1"
start "" powershell.exe -NoExit -Command "%venvActivatePath%"
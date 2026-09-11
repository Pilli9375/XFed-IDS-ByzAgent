@echo off
REM XFed-IDS Streamlit launcher.
REM Double-click this to start the app -- no typing cd + conda activate.
REM
REM Runs inside PowerShell rather than cmd.exe, because conda's shell
REM hook is only initialized for PowerShell on this machine (same reason
REM start_xfed.bat opens PowerShell instead of running commands directly
REM in cmd -- "conda activate" is a silent no-op in a plain cmd window
REM here, which is what caused streamlit to come back "not recognized").

start powershell.exe -NoExit -Command "cd 'C:\Pilli\Capstone\xfed-ids'; conda activate xfed; if (Test-Path app.py) { streamlit run app.py } else { Write-Host '[error] app.py not found -- check the path above.' -ForegroundColor Red }"

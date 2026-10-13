@echo off
cd /d "%~dp0"
echo [*] Launching scrcpy on port 28000 (bypassing Windows port conflicts)...
.\scrcpy-win64-v4.1\scrcpy.exe -p 28000:28050 -m 1024 -w %*

@echo off
set ROOT=C:\Users\coordinacion\OneDrive - Universidad Nacional de Chimborazo\Aplicaciones Bellaflor\BLIS

mkdir "%ROOT%" 2>nul
mkdir "%ROOT%\docs" 2>nul
mkdir "%ROOT%\database" 2>nul
mkdir "%ROOT%\database\schema" 2>nul
mkdir "%ROOT%\database\views" 2>nul
mkdir "%ROOT%\database\seeds" 2>nul
mkdir "%ROOT%\database\migrations" 2>nul
mkdir "%ROOT%\backend" 2>nul
mkdir "%ROOT%\frontend" 2>nul
mkdir "%ROOT%\deployment" 2>nul
mkdir "%ROOT%\imports" 2>nul
mkdir "%ROOT%\reports" 2>nul
mkdir "%ROOT%\backups" 2>nul

echo BLIS folder structure created successfully.
pause

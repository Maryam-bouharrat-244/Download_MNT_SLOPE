@echo off
REM Script pour lancer l'application MNT France Generator
REM 
REM Usage: Ouvrez ce fichier ou exécutez dans le terminal PowerShell

title MNT France Generator - Streamlit

echo ╔════════════════════════════════════════════════════════════════╗
echo ║           MNT France Generator - Streamlit App                 ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🚀 Démarrage de l'application...
echo.

REM Changer vers le répertoire du projet
cd /d "C:\Users\marya\Downloads\projet test"

REM Lancer Streamlit
python -m streamlit run mnt_app.py

pause

@echo off
REM Script de validation complète de tous les MNT
REM ATTENTION: Ce processus peut prendre 48-72 heures pour tous les départements!

title Validation Complète MNT France - Tous Départements

cls
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║    VALIDATION COMPLÈTE MNT FRANCE - TOUS LES DÉPARTEMENTS      ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo ⚠️  ATTENTION:
echo    • Cet processus télécharge ~1-2 GB par département
echo    • Pour 96 départements: ~100-200 GB d'espace disque requis
echo    • Durée estimée: 48-72 heures (selon votre connexion)
echo    • Los fichiers 7z sont conservés après extraction
echo.
echo 📂 Localisation:
echo    • Téléchargements: C:\Users\marya\Downloads\mnt_work\
echo    • VRT générés: C:\Users\marya\Downloads\
echo    • Rapports: C:\Users\marya\Downloads\mnt_logs\
echo.
echo     [1] Démarrer la validation complète
echo     [2] Valider seulement un département
echo     [3] Quitter
echo.

set /p choice="Votre choix (1/2/3): "

if "%choice%"=="1" (
    echo.
    echo Démarrage de la validation complète...
    echo.
    cd /d "C:\Users\marya\Downloads\projet test"
    python validate_all_mnt.py
) else if "%choice%"=="2" (
    echo.
    set /p dept="Entrez le code département (ex: 1, 23, 75, 2A): "
    echo Fonction disponible via l'application Streamlit
    streamlit run mnt_app.py
) else (
    echo Annulation.
    exit /b 0
)

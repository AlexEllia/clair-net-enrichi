@echo off
rem Sauvegarde des episodes (voix, rendus, builds) hors de git, vers OneDrive.
rem
rem     outils\sauvegarde_medias.bat
rem
rem Copie ADDITIVE : robocopy /E, sans /MIR ni /PURGE. Un fichier disparu de
rem la source reste dans la sauvegarde ; un fichier modifie y est remplace
rem (l'historique des versions de OneDrive garde l'ancien).
rem Exclus, car regenerables : __pycache__, *.pyc, cache de Manim (_manim,
rem partial_movie_files).
rem Journal horodate : %OneDrive%\Sauvegardes\clair-net-enrichi\journaux\
rem A lancer apres chaque episode publie (docs\REGLES_MOTEUR.md).

setlocal
if not defined OneDrive (
    echo ERREUR : la variable OneDrive n'existe pas sur cette machine.
    exit /b 2
)
if not exist "%OneDrive%\" (
    echo ERREUR : dossier OneDrive introuvable : %OneDrive%
    exit /b 2
)

set "SOURCE=%~dp0..\episodes"
set "RACINE=%OneDrive%\Sauvegardes\clair-net-enrichi"
set "DEST=%RACINE%\episodes"
set "JOURNAUX=%RACINE%\journaux"
if not exist "%SOURCE%\" (
    echo ERREUR : dossier source introuvable : %SOURCE%
    exit /b 2
)
if not exist "%JOURNAUX%\" mkdir "%JOURNAUX%"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HHmmss"') do set "HORO=%%i"
set "JOURNAL=%JOURNAUX%\sauvegarde_%HORO%.log"

echo Source  : %SOURCE%
echo Cible   : %DEST%
echo Journal : %JOURNAL%

robocopy "%SOURCE%" "%DEST%" /E /COPY:DAT /DCOPY:T /R:2 /W:5 /NP /XJ ^
    /XD __pycache__ _manim partial_movie_files ^
    /XF *.pyc ^
    /LOG:"%JOURNAL%" /TEE
set "CODE=%ERRORLEVEL%"

rem robocopy : 0 a 7 = reussite (bits : 1 copies, 2 en trop dans la cible,
rem 4 en ecart), 8 et plus = echecs de copie.
if %CODE% GEQ 8 (
    echo ECHEC : robocopy a rendu le code %CODE%. Voir %JOURNAL%
    exit /b %CODE%
)
echo Sauvegarde terminee, code robocopy %CODE%. Journal : %JOURNAL%
exit /b 0

@echo off
rem Relais pour "make video EP=EPxxx" quand GNU make n'est pas installe.
rem
rem   cmd.exe      : make video EP=EP001
rem   PowerShell   : .\make.cmd video EP=EP001
rem
rem Les cibles sont les memes que dans le Makefile : video, preview, plans,
rem rebuild, check, scene, draft, clean.

setlocal EnableDelayedExpansion
pushd "%~dp0"

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=video"
set "EP="
set "SEGS="
set "LOC=fr"

:parse
rem cmd.exe coupe les arguments sur "=" : EP=EP001 arrive en deux morceaux,
rem "EP" puis "EP001". On accepte les deux formes (et la forme entre guillemets).
shift
if "%~1"=="" goto run
set "ARG=%~1"
if /I "!ARG!"=="LOCALE" (
  set "LOC=%~2"
  shift
) else if /I "!ARG!"=="EP" (
  set "EP=%~2"
  shift
) else if /I "!ARG!"=="S" (
  set "SEGS=!SEGS! %~2"
  shift
) else if /I "!ARG:~0,3!"=="EP=" (
  set "EP=!ARG:~3!"
) else if /I "!ARG:~0,2!"=="S=" (
  set "SEGS=!SEGS! !ARG:~2!"
)
goto parse

:run
if "%EP%"=="" (
  echo Precisez l'episode^ : make video EP=EP001
  popd & exit /b 1
)

if /I "%TARGET%"=="video"   python video\build.py --ep %EP% --locale %LOC%
if /I "%TARGET%"=="preview" python video\build.py --ep %EP% --preview --locale %LOC%
if /I "%TARGET%"=="plans"   python video\build.py --ep %EP% --only %SEGS% --preview --locale %LOC%
if /I "%TARGET%"=="check"   python video\build.py --ep %EP% --check
if /I "%TARGET%"=="scene"   python video\build.py --ep %EP% --only %SEGS% --preview --locale %LOC%
if /I "%TARGET%"=="draft"   python video\build.py --ep %EP% --preview --locale %LOC%
if /I "%TARGET%"=="rebuild" python video\build.py --ep %EP% --skip-render --locale %LOC%
if /I "%TARGET%"=="clean" (
  rmdir /s /q "episodes\%EP%\video\plans"       2>nul
  rmdir /s /q "episodes\%EP%\video\plans_cales" 2>nul
  rmdir /s /q "episodes\%EP%\video\_manim"      2>nul
  rmdir /s /q "episodes\%EP%\video\_check"      2>nul
  del /q      "episodes\%EP%\video\voix.wav"    2>nul
  echo Fichiers intermediaires effaces pour %EP%.
)

set "RC=%ERRORLEVEL%"
popd
exit /b %RC%

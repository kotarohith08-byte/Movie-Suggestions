@echo off
title CineMatch AI - Movie Recommendation System
color 0b
echo ======================================================================
echo           Starting CineMatch AI Recommendation System...
echo ======================================================================
echo.

cd /d "%~dp0"

echo [*] Launching Flask server on http://127.0.0.1:5000
echo [*] Opening your default web browser...
start "" "http://127.0.0.1:5000"

python app.py
pause

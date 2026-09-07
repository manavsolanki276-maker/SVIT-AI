@echo off
title Deploy SVIT-AI to Vercel
color 0b
echo ====================================================================
echo        SVIT-AI - Push Local Commits to GitHub and Vercel
echo ====================================================================
echo.
echo Uploading 9 commits to https://github.com/manavsolanki276-maker/SVIT-AI ...
echo.
cd /d "%~dp0"
git push origin main

echo.
echo ====================================================================
if %ERRORLEVEL% EQU 0 (
    echo [SUCCESS] Code pushed successfully!
    echo Vercel is now building and deploying to https://svit-ai.vercel.app/
    echo Please wait ~60 seconds and refresh your live website.
) else (
    echo [FAILED] Push failed. Please ensure you are logged into GitHub.
)
echo ====================================================================
echo.
pause

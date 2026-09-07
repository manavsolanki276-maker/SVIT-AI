@echo off
setlocal enabledelayedexpansion
title Deploy SVIT-AI to Vercel
color 0b

echo ====================================================================
echo        SVIT-AI - Push Local Commits to GitHub and Vercel
echo ====================================================================
echo.

cd /d "%~dp0"

echo [*] Staging all files including local database and configurations...
git add -A

git diff --cached --quiet
if %ERRORLEVEL% NEQ 0 (
    echo [*] Committing local updates...
    git commit -m "chore(deploy): bundle database, unify run.py, and configure vercel functions"
)

echo.
echo [*] Pushing commits to https://github.com/manavsolanki276-maker/SVIT-AI ...
echo.

git push origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================================================
    echo  [SUCCESS] Code pushed successfully to GitHub!
    echo  Vercel is now building and deploying to:
    echo  https://svit-ai.vercel.app/
    echo.
    echo  Please wait ~60 seconds and refresh your live website.
    echo ====================================================================
    echo.
    pause
    exit /b 0
)

echo.
echo ====================================================================
echo  [ACTION REQUIRED] GitHub authentication is needed to push code.
echo ====================================================================
echo.
echo  GitHub requires a Personal Access Token (PAT) for HTTPS push.
echo.
echo  Options:
echo   [1] Paste your GitHub Personal Access Token (PAT) now
echo   [2] Press 'O' to open GitHub token page in your browser
echo   [3] Press 'Q' to quit
echo.
set /p USER_CHOICE="Enter option (1/2/Q) or paste token directly: "

if /i "%USER_CHOICE%"=="Q" (
    echo Deployment cancelled.
    pause
    exit /b 1
)

if /i "%USER_CHOICE%"=="2" (
    echo Opening GitHub token creation page...
    start https://github.com/settings/tokens/new?scopes=repo^&description=SVIT-AI-Deploy
    echo.
    echo Once you have generated the token, run this script again or paste it below.
    set /p GITHUB_TOKEN="Paste GitHub Token here: "
) else if /i "%USER_CHOICE%"=="O" (
    echo Opening GitHub token creation page...
    start https://github.com/settings/tokens/new?scopes=repo^&description=SVIT-AI-Deploy
    echo.
    echo Once you have generated the token, run this script again or paste it below.
    set /p GITHUB_TOKEN="Paste GitHub Token here: "
) else if /i "%USER_CHOICE%"=="1" (
    set /p GITHUB_TOKEN="Paste GitHub Token here: "
) else (
    set "GITHUB_TOKEN=%USER_CHOICE%"
)

if "%GITHUB_TOKEN%"=="" (
    echo [ERROR] No token provided.
    pause
    exit /b 1
)

echo.
echo [*] Configuring Git remote with provided token...
git remote set-url origin https://%GITHUB_TOKEN%@github.com/manavsolanki276-maker/SVIT-AI.git

echo [*] Retrying push to GitHub...
git push origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ====================================================================
    echo  [SUCCESS] Code pushed successfully to GitHub!
    echo  Vercel is now building and deploying to:
    echo  https://svit-ai.vercel.app/
    echo.
    echo  Please wait ~60 seconds and refresh your live website.
    echo ====================================================================
) else (
    echo.
    echo ====================================================================
    echo  [FAILED] Push failed. Please check that your token has 'repo' scope.
    echo ====================================================================
)

echo.
pause

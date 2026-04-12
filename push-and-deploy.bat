@echo off
setlocal enabledelayedexpansion

echo.
echo ================================================
echo   LeaseManager Greenfield Push + Deploy
echo ================================================
echo.

if "%~1"=="" (
    echo ERROR: Please provide a commit message
    echo Usage: push-and-deploy.bat "your commit message"
    echo        push-and-deploy.bat "your commit message" path\to\file1 path\to\file2
    echo        push-and-deploy.bat "your commit message" --all
    exit /b 1
)

set "COMMIT_MESSAGE=%~1"
shift
set "STAGE_MODE=staged"

if /I "%~1"=="--all" goto stage_all
if not "%~1"=="" goto stage_paths_start
echo [1/4] Using currently staged changes only...
goto after_stage

:stage_all
set "STAGE_MODE=all"
echo [1/4] Staging all changes explicitly requested...
git add .
if errorlevel 1 (
    echo ERROR: git add failed
    exit /b 1
)
goto after_stage

:stage_paths_start
set "STAGE_MODE=paths"
echo [1/4] Staging only the requested paths...

:stage_paths
if "%~1"=="" goto after_stage
echo    - %~1
git add -- "%~1"
if errorlevel 1 (
    echo ERROR: git add failed for %~1
    exit /b 1
)
shift
goto stage_paths

:after_stage
git diff --cached --quiet
if not errorlevel 1 (
    echo ERROR: No staged changes found.
    if "%STAGE_MODE%"=="staged" (
        echo Stage the intended files first or pass file paths to this script.
    )
    exit /b 1
)

echo Staged files:
git diff --cached --name-only

echo [2/4] Creating commit...
git commit -m "%COMMIT_MESSAGE%"
if errorlevel 1 (
    echo ERROR: Commit failed
    exit /b 1
)

echo [3/4] Pushing to GitHub...
git push
if errorlevel 1 (
    echo ERROR: git push failed
    exit /b 1
)

echo [4/4] Deploying greenfield frontend on Vercel...
pushd frontend >nul
vercel --prod --yes --scope joaquins-projects-72185699
if errorlevel 1 (
    popd >nul
    echo ERROR: Vercel deploy failed
    echo Ensure the Vercel CLI is authenticated and the frontend project remains linked.
    exit /b 1
)
popd >nul

echo.
echo ================================================
echo   SUCCESS: Code pushed and greenfield frontend deployed
echo ================================================
echo.
echo Current production alias:
echo https://leasemanager-backoffice.vercel.app
echo.

endlocal

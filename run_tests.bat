@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PROJECT_ROOT=%~dp0"
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

set "ISAAC_SIM_ROOT=E:\IsaacSim-5.1.0"
set "PYTHONEXE=%ISAAC_SIM_ROOT%\kit\python\python.exe"
set "PYTHONPATH=%PROJECT_ROOT%;%PROJECT_ROOT%\isaaclab_repo\source\isaaclab;%PROJECT_ROOT%\isaaclab_repo\source\isaaclab_assets;%PROJECT_ROOT%\isaaclab_repo\source\isaaclab_tasks;%PROJECT_ROOT%\isaaclab_repo\source\isaaclab_rl;%PROJECT_ROOT%\isaaclab_repo\source\isaaclab_mimic"
set "WARP_CACHE_PATH=%PROJECT_ROOT%\artifacts\warp_cache"

set "MODE=%~1"
if "%MODE%"=="" set "MODE=quick"

echo.
echo === SF_TRON_Ext Estimator Test Runner ===
echo Project: %PROJECT_ROOT%
echo Mode:    %MODE%
echo Python:  %PYTHONEXE%
echo.

if not exist "%ISAAC_SIM_ROOT%\python.bat" (
    echo [FAIL] Isaac Sim python.bat not found: %ISAAC_SIM_ROOT%\python.bat
    exit /b 1
)

if /I not "%MODE%"=="quick" if /I not "%MODE%"=="full" (
    echo [FAIL] Unknown mode: %MODE%
    echo Usage:
    echo   run_tests.bat        ^(quick tests only^)
    echo   run_tests.bat quick  ^(quick tests only^)
    echo   run_tests.bat full   ^(quick tests + Isaac Sim smoke test^)
    exit /b 1
)

pushd "%PROJECT_ROOT%"
if not exist "%PROJECT_ROOT%\artifacts" mkdir "%PROJECT_ROOT%\artifacts"
if not exist "%WARP_CACHE_PATH%" mkdir "%WARP_CACHE_PATH%"

echo [1/4] Compiling Python files...
call "%ISAAC_SIM_ROOT%\python.bat" -m py_compile ^
    SF_TRON_Ext\utils\Config\Config.py ^
    SF_TRON_Ext\utils\PPO\Actor_Critic.py ^
    SF_TRON_Ext\utils\Env\Tron_Env.py ^
    SF_TRON_Ext\utils\Estimator\Disturbance_Estimator.py ^
    SF_TRON_Ext\Run_2.py ^
    test_shapes.py ^
    check_env.py ^
    smoke_test.py ^
    tools\smoke_check_estimator.py ^
    tools\training_sanity_check.py ^
    tools\force_label_diagnostic.py
if errorlevel 1 goto :fail

echo.
echo [2/4] Running environment import check...
call "%ISAAC_SIM_ROOT%\python.bat" check_env.py
if errorlevel 1 goto :fail

echo.
echo [3/4] Running shape/unit checks...
call "%ISAAC_SIM_ROOT%\python.bat" test_shapes.py
if errorlevel 1 goto :fail

echo.
echo [4/4] Running estimator smoke check...
call "%ISAAC_SIM_ROOT%\python.bat" tools\smoke_check_estimator.py
if errorlevel 1 goto :fail

if /I "%MODE%"=="full" (
    echo.
    echo [FULL] Running Isaac Sim headless smoke test...
    if exist "%PROJECT_ROOT%\artifacts\smoke_test\success.txt" del "%PROJECT_ROOT%\artifacts\smoke_test\success.txt"
    call "%ISAAC_SIM_ROOT%\python.bat" smoke_test.py
    if errorlevel 1 goto :fail
    if not exist "%PROJECT_ROOT%\artifacts\smoke_test\success.txt" (
        echo [FAIL] Smoke test did not write success sentinel.
        goto :fail
    )
)

echo.
echo [PASS] All requested tests passed.
popd
exit /b 0

:fail
echo.
echo [FAIL] Test runner stopped with an error.
popd
exit /b 1

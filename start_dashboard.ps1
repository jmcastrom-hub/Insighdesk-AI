param(
    [switch]$RestartBackend
)

$basePath = "C:\Users\pc\OneDrive\Desktop\Lab_LE_Claude\ai-maze\Insightdesk-AI"
$pythonPath = "C:\Users\pc\AppData\Local\Python\pythoncore-3.14-64\python.exe"

function Test-LocalPort($port) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connect = $client.BeginConnect("127.0.0.1", $port, $null, $null)
        if (-not $connect.AsyncWaitHandle.WaitOne(800)) { return $false }
        $client.EndConnect($connect)
        return $true
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

# Cargar configuración local sin mostrar la clave ni guardarla en el repositorio.
$envFile = Join-Path $basePath ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([^#=\s]+)\s*=\s*(.*)\s*$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim('"', "'"), "Process")
        }
    }
}
if ($env:GEMINI_API_KEY) {
    Write-Host "Configuración de Gemini cargada (clave oculta)." -ForegroundColor Green
} else {
    Write-Host "GEMINI_API_KEY no está configurada; el chat seguirá deshabilitado." -ForegroundColor Yellow
}

if (Test-LocalPort 8000) {
    if (-not $RestartBackend) {
        Write-Host "Backend ya activo. Para cargar .env en una instancia nueva, detén el backend y usa -RestartBackend." -ForegroundColor Yellow
    } else {
        $backendProcesses = @(
            Get-Process -Name python -ErrorAction SilentlyContinue |
                Where-Object { $_.Path -eq $pythonPath }
        )
        if ($backendProcesses.Count -eq 1) {
            Stop-Process -Id $backendProcesses[0].Id -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        } elseif ($backendProcesses.Count -gt 1) {
            throw "Hay varios procesos Python con el mismo intérprete; para no detener otro trabajo, cierra Uvicorn con Ctrl+C en su terminal."
        } else {
            throw "Windows no encuentra el proceso Python del backend aunque el puerto 8000 responde. Cierra la ventana de Uvicorn manualmente y vuelve a ejecutar."
        }
        if (Test-LocalPort 8000) {
            throw "El puerto 8000 sigue ocupado, pero no encontré Uvicorn por su comando. Ejecuta: Get-CimInstance Win32_Process -Filter `"Name = 'python.exe'`" | Where-Object { `$_.CommandLine -match 'uvicorn.*app\.main:app' } | ForEach-Object { Stop-Process -Id `$_.ProcessId -Force }"
        }
    }
}

if (-not (Test-LocalPort 8000)) {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$basePath\backend'; `$env:PYTHONPATH='$basePath\backend'; & '$pythonPath' -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
}

if (Test-LocalPort 5173) {
    Write-Host "Frontend ya está escuchando en http://localhost:5173; reutilizaré esa instancia." -ForegroundColor Yellow
} else {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$basePath\frontend'; npm run dev -- --host 127.0.0.1 --port 5173 --strictPort"
}

Write-Host "Dashboard: http://localhost:5173 | API: http://127.0.0.1:8000/docs" -ForegroundColor Green

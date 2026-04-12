param(
    [string]$ProjectName = "leasemanager-backend",
    [string]$Workspace = "joaquins-projects-72185699",
    [string]$Environment = "production",
    [string]$BackendEnvPath = "D:\\Proyectos\\LeaseManager\\Produccion 1.0\\backend\\.env.railway.example",
    [switch]$CreateRedis,
    [switch]$CreatePostgres
)

$ErrorActionPreference = "Stop"

function Invoke-Railway {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    Write-Host ("railway " + ($Args -join " ")) -ForegroundColor Cyan
    & npx @railway/cli @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Railway command failed: railway $($Args -join ' ')"
    }
}

function Test-PlaceholderValue {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) { return $true }
    return $Value -match '^__.*__$' -or $Value -eq 'replace-me'
}

if (!(Test-Path $BackendEnvPath)) {
    throw "No existe el archivo de variables: $BackendEnvPath"
}

try {
    Invoke-Railway -Args @('whoami') | Out-Null
} catch {
    Write-Host "Railway CLI no está autenticada. Ejecuta primero:" -ForegroundColor Yellow
    Write-Host "  npx @railway/cli login" -ForegroundColor Yellow
    throw
}

Write-Host "`n==> Creando o reutilizando proyecto Railway" -ForegroundColor Green
Invoke-Railway -Args @('init', '--name', $ProjectName, '--workspace', $Workspace)

Write-Host "`n==> Creando servicios base" -ForegroundColor Green
Invoke-Railway -Args @('add', '--service', 'backend-web')
Invoke-Railway -Args @('add', '--service', 'backend-worker')

if ($CreateRedis) {
    Write-Host "`n==> Añadiendo Redis" -ForegroundColor Green
    Invoke-Railway -Args @('add', '--database', 'redis')
}

if ($CreatePostgres) {
    Write-Host "`n==> Añadiendo PostgreSQL" -ForegroundColor Green
    Invoke-Railway -Args @('add', '--database', 'postgres')
}

$entries = @{}
Get-Content $BackendEnvPath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith('#')) { return }
    $parts = $line -split '=', 2
    if ($parts.Length -ne 2) { return }
    $entries[$parts[0].Trim()] = $parts[1]
}

$serviceNames = @('backend-web', 'backend-worker')
foreach ($service in $serviceNames) {
    Write-Host "`n==> Cargando variables en $service" -ForegroundColor Green
    foreach ($key in $entries.Keys) {
        $value = [string]$entries[$key]
        if (Test-PlaceholderValue $value) {
            Write-Host "  - SKIP $key (placeholder o vacío)" -ForegroundColor DarkYellow
            continue
        }

        Invoke-Railway -Args @('variable', 'set', "$key=$value", '--service', $service, '--environment', $Environment, '--skip-deploys')
    }
}

Write-Host "`nBootstrap Railway listo." -ForegroundColor Green
Write-Host "Siguientes pasos manuales:" -ForegroundColor Green
Write-Host "  1. En backend-web, configura el custom config path a /backend/railway.web.json" -ForegroundColor Yellow
Write-Host "  2. En backend-worker, configura el custom config path a /backend/railway.worker.json" -ForegroundColor Yellow
Write-Host "  3. Completa DATABASE_URL y REDIS_URL reales si siguen en placeholder" -ForegroundColor Yellow
Write-Host "  4. Ejecuta deploy del servicio backend-web y luego backend-worker" -ForegroundColor Yellow
Write-Host "  5. Obtén la URL pública del backend y úsala como VITE_API_BASE_URL en Vercel" -ForegroundColor Yellow

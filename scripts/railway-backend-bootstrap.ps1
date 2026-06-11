param(
    [string]$ProjectName = "leasemanager-backend",
    [string]$Workspace = "joaquins-projects-72185699",
    [string]$Environment = "staging",
    [string]$BackendEnvPath = "backend\railway.env.example",
    [string]$AuthorizationRef = "",
    [switch]$Apply,
    [switch]$CreateRedis,
    [switch]$CreatePostgres
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Resolve-RepoPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "$Label no puede estar vacio."
    }

    $candidate = $Path
    if (-not [System.IO.Path]::IsPathRooted($candidate)) {
        $candidate = Join-Path $repoRoot $candidate
    }
    if (-not (Test-Path -LiteralPath $candidate)) {
        throw "No existe $Label en $candidate."
    }

    $resolved = (Resolve-Path -LiteralPath $candidate).Path
    $root = (Resolve-Path -LiteralPath $repoRoot).Path.TrimEnd('\')
    $rootWithSeparator = "$root\"
    if (-not ($resolved.Equals($root, [System.StringComparison]::OrdinalIgnoreCase) -or $resolved.StartsWith($rootWithSeparator, [System.StringComparison]::OrdinalIgnoreCase))) {
        throw "$Label debe estar dentro del root activo $root."
    }

    return $resolved
}

function Assert-AuthorizationRef {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "AuthorizationRef es obligatorio con -Apply."
    }
    if ($Value.Trim().Length -lt 6) {
        throw "AuthorizationRef debe ser una referencia no sensible y trazable."
    }
    if ($Value -match '(?i)(bearer|token|secret|password|passwd|api[_-]?key|railway_[a-z0-9]+|https?://|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})') {
        throw "AuthorizationRef no debe contener secretos, URLs ni emails."
    }
}

function Assert-BackendEnvPathSafe {
    param([string]$Path)

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "BackendEnvPath no puede estar vacio."
    }

    $leaf = [System.IO.Path]::GetFileName($Path.TrimEnd('\', '/'))
    $looksLikeEnvFile = $leaf -match '(?i)(^\.env($|\.)|\.env($|\.))'
    $isTemplate = $leaf -match '(?i)\.env\.example$'
    if ($looksLikeEnvFile -and -not $isTemplate) {
        throw "BackendEnvPath no puede apuntar a .env real; usa un template .env.example no sensible."
    }
}

function Invoke-Railway {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args,
        [string]$DisplayArgs = ""
    )

    if ([string]::IsNullOrWhiteSpace($DisplayArgs)) {
        $DisplayArgs = $Args -join " "
    }

    Write-Host ("railway " + $DisplayArgs) -ForegroundColor Cyan
    & npx @railway/cli @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Railway command failed: railway $DisplayArgs"
    }
}

function Test-PlaceholderValue {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) { return $true }
    return $Value -match '^__.*__$' -or $Value -eq 'replace-me'
}

function Read-EnvEntries {
    param([string]$Path)

    $entries = @{}
    Get-Content -LiteralPath $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith('#')) { return }
        $parts = $line -split '=', 2
        if ($parts.Length -ne 2) { return }
        $entries[$parts[0].Trim()] = $parts[1]
    }
    return $entries
}

Assert-BackendEnvPathSafe -Path $BackendEnvPath
$resolvedBackendEnvPath = Resolve-RepoPath -Path $BackendEnvPath -Label "BackendEnvPath"
Assert-BackendEnvPathSafe -Path $resolvedBackendEnvPath
$entries = Read-EnvEntries -Path $resolvedBackendEnvPath
$activeEntries = @($entries.Keys | Where-Object { -not (Test-PlaceholderValue ([string]$entries[$_])) })

if (-not $Apply) {
    Write-Host "Modo plan: no se ejecuta Railway CLI ni se crean recursos externos." -ForegroundColor Yellow
    Write-Host "project_name_configurado=true" -ForegroundColor Green
    Write-Host "workspace_configurado=true" -ForegroundColor Green
    Write-Host "environment=$Environment" -ForegroundColor Green
    Write-Host "backend_env_file_validado=true" -ForegroundColor Green
    Write-Host "variables_detectadas=$($entries.Count)" -ForegroundColor Green
    Write-Host "variables_no_placeholder=$($activeEntries.Count)" -ForegroundColor Green
    Write-Host "create_redis=$($CreateRedis.IsPresent)" -ForegroundColor Green
    Write-Host "create_postgres=$($CreatePostgres.IsPresent)" -ForegroundColor Green
    Write-Host "Para aplicar, reejecuta con -Apply y AuthorizationRef no sensible." -ForegroundColor Yellow
    exit 0
}

Assert-AuthorizationRef -Value $AuthorizationRef

try {
    Invoke-Railway -Args @('whoami') | Out-Null
} catch {
    Write-Host "Railway CLI no esta autenticada. Ejecuta primero:" -ForegroundColor Yellow
    Write-Host "  npx @railway/cli login" -ForegroundColor Yellow
    throw
}

Write-Host "`n==> Creando o reutilizando proyecto Railway" -ForegroundColor Green
Invoke-Railway -Args @('init', '--name', $ProjectName, '--workspace', $Workspace)

Write-Host "`n==> Creando servicios base" -ForegroundColor Green
Invoke-Railway -Args @('add', '--service', 'backend-web')
Invoke-Railway -Args @('add', '--service', 'backend-worker')

if ($CreateRedis) {
    Write-Host "`n==> Anadiendo Redis" -ForegroundColor Green
    Invoke-Railway -Args @('add', '--database', 'redis')
}

if ($CreatePostgres) {
    Write-Host "`n==> Anadiendo PostgreSQL" -ForegroundColor Green
    Invoke-Railway -Args @('add', '--database', 'postgres')
}

$serviceNames = @('backend-web', 'backend-worker')
foreach ($service in $serviceNames) {
    Write-Host "`n==> Cargando variables en $service" -ForegroundColor Green
    foreach ($key in $entries.Keys) {
        $value = [string]$entries[$key]
        if (Test-PlaceholderValue $value) {
            Write-Host "  - SKIP $key (placeholder o vacio)" -ForegroundColor DarkYellow
            continue
        }

        Invoke-Railway `
            -Args @('variable', 'set', "$key=$value", '--service', $service, '--environment', $Environment, '--skip-deploys') `
            -DisplayArgs "variable set $key=<redacted> --service $service --environment $Environment --skip-deploys"
    }
}

Write-Host "`nBootstrap Railway aplicado." -ForegroundColor Green
Write-Host "authorization_ref_registrada=true" -ForegroundColor Green
Write-Host "Siguientes pasos manuales:" -ForegroundColor Green
Write-Host "  1. En backend-web, configura el custom config path a /backend/railway.web.json" -ForegroundColor Yellow
Write-Host "  2. En backend-worker, configura el custom config path a /backend/railway.worker.json" -ForegroundColor Yellow
Write-Host "  3. Completa DATABASE_URL y REDIS_URL reales si siguen en placeholder" -ForegroundColor Yellow
Write-Host "  4. Ejecuta deploy del servicio backend-web y luego backend-worker" -ForegroundColor Yellow
Write-Host "  5. Obten la URL publica del backend y usala como VITE_API_BASE_URL en Vercel" -ForegroundColor Yellow

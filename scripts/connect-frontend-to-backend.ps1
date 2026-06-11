param(
    [Parameter(Mandatory = $true)]
    [string]$BackendUrl,
    [string]$VercelToken = $env:VERCEL_TOKEN,
    [string]$ProjectId = "",
    [string]$TeamId = "",
    [string]$ProjectConfigPath = "frontend\.vercel\project.json",
    [string]$FrontendDir = "frontend",
    [string[]]$Targets = @("production", "preview"),
    [string]$VercelScope = "joaquins-projects-72185699",
    [string]$AuthorizationRef = "",
    [switch]$Apply,
    [switch]$Redeploy
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot

function Resolve-RepoPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Label,
        [switch]$MustExist
    )

    if ([string]::IsNullOrWhiteSpace($Path)) {
        throw "$Label no puede estar vacio."
    }

    $candidate = $Path
    if (-not [System.IO.Path]::IsPathRooted($candidate)) {
        $candidate = Join-Path $repoRoot $candidate
    }

    if ($MustExist -and -not (Test-Path -LiteralPath $candidate)) {
        throw "No existe $Label en $candidate."
    }

    $resolved = $candidate
    if (Test-Path -LiteralPath $candidate) {
        $resolved = (Resolve-Path -LiteralPath $candidate).Path
    } else {
        $parent = Split-Path -Parent $candidate
        if ($parent -and (Test-Path -LiteralPath $parent)) {
            $resolvedParent = (Resolve-Path -LiteralPath $parent).Path
            $resolved = Join-Path $resolvedParent (Split-Path -Leaf $candidate)
        }
    }

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
    if ($Value -match '(?i)(bearer|token|secret|password|passwd|api[_-]?key|vercel_[a-z0-9]+|https?://|[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})') {
        throw "AuthorizationRef no debe contener secretos, URLs ni emails."
    }
}

function Assert-Targets {
    param([string[]]$Values)

    if (-not $Values -or $Values.Count -eq 0) {
        throw "Targets debe contener al menos un ambiente Vercel."
    }
    foreach ($target in $Values) {
        if ($target -notin @("production", "preview", "development")) {
            throw "Target Vercel no permitido: $target."
        }
    }
}

$normalizedBackendUrl = $BackendUrl.Trim().TrimEnd('/')
if ($normalizedBackendUrl -notmatch '^https?://') {
    throw "BackendUrl debe incluir esquema http:// o https://."
}
Assert-Targets -Values $Targets

if (-not $Apply) {
    Write-Host "Modo plan: no se modifica Vercel ni se ejecuta deploy." -ForegroundColor Yellow
    Write-Host "backend_url_validada=true" -ForegroundColor Green
    Write-Host ("targets=" + ($Targets -join ",")) -ForegroundColor Green
    Write-Host "Para aplicar, reejecuta con -Apply y AuthorizationRef no sensible." -ForegroundColor Yellow
    Write-Host "Para redeploy, agrega -Redeploy explicitamente." -ForegroundColor Yellow
    exit 0
}

Assert-AuthorizationRef -Value $AuthorizationRef

if ([string]::IsNullOrWhiteSpace($VercelToken)) {
    throw "Falta VERCEL_TOKEN. Este script no usa fallbacks locales ni rutas legacy."
}

if ([string]::IsNullOrWhiteSpace($ProjectId) -or [string]::IsNullOrWhiteSpace($TeamId)) {
    $projectFile = Resolve-RepoPath -Path $ProjectConfigPath -Label "ProjectConfigPath" -MustExist
    $projectMeta = Get-Content -Raw -LiteralPath $projectFile | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace($ProjectId)) {
        $ProjectId = $projectMeta.projectId
    }
    if ([string]::IsNullOrWhiteSpace($TeamId)) {
        $TeamId = $projectMeta.orgId
    }
}

if ([string]::IsNullOrWhiteSpace($ProjectId) -or [string]::IsNullOrWhiteSpace($TeamId)) {
    throw "No se pudo resolver ProjectId/TeamId del proyecto Vercel activo."
}

$headers = @{
    Authorization = "Bearer $VercelToken"
    "Content-Type" = "application/json"
}

$payload = @{
    key = "VITE_API_BASE_URL"
    value = $normalizedBackendUrl
    type = "encrypted"
    target = $Targets
} | ConvertTo-Json -Depth 5

$endpoint = "https://api.vercel.com/v10/projects/$ProjectId/env?upsert=true&teamId=$TeamId"

Write-Host "==> Actualizando VITE_API_BASE_URL en Vercel" -ForegroundColor Green
Invoke-RestMethod -Method Post -Uri $endpoint -Headers $headers -Body $payload | Out-Null

Write-Host "VITE_API_BASE_URL actualizada en Vercel." -ForegroundColor Green
Write-Host ("Targets: " + ($Targets -join ", ")) -ForegroundColor Green
Write-Host "authorization_ref_registrada=true" -ForegroundColor Green

if (-not $Redeploy) {
    Write-Host "Redeploy no ejecutado. Agrega -Redeploy para publicar una nueva revision." -ForegroundColor Yellow
    exit 0
}

$resolvedFrontendDir = Resolve-RepoPath -Path $FrontendDir -Label "FrontendDir" -MustExist

Write-Host "`n==> Ejecutando redeploy explicito del frontend en Vercel" -ForegroundColor Green
$latestDeploymentUrl = $null
$listOutput = & vercel list leasemanager-backoffice --token $VercelToken --scope $VercelScope 2>$null
foreach ($line in $listOutput) {
    if ($line -match 'https://leasemanager-backoffice-[^\s]+\.vercel\.app') {
        $latestDeploymentUrl = $Matches[0]
        break
    }
}

if ($latestDeploymentUrl) {
    & vercel redeploy $latestDeploymentUrl --target production --no-wait --scope $VercelScope --token $VercelToken
} else {
    & vercel --cwd $resolvedFrontendDir --prod --yes --scope $VercelScope --token $VercelToken
}
if ($LASTEXITCODE -ne 0) {
    throw "Fallo el redeploy del frontend en Vercel."
}

Write-Host "`n==> Listo" -ForegroundColor Green
Write-Host "frontend_publicado=true" -ForegroundColor Green
Write-Host "backend_url_configurada=true" -ForegroundColor Green

param(
    [Parameter(Mandatory = $true)]
    [string]$BackendUrl,
    [string]$VercelToken = $env:VERCEL_TOKEN,
    [string]$ProjectId = "",
    [string]$TeamId = "",
    [string[]]$Targets = @("production", "preview"),
    [switch]$SkipDeploy
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($VercelToken)) {
    $legacyDeploy = "D:\Proyectos\LeaseManager\deploy.bat"
    if (Test-Path $legacyDeploy) {
        $line = Get-Content $legacyDeploy | Where-Object { $_ -match '^set VERCEL_TOKEN=' } | Select-Object -First 1
        if ($line) {
            $VercelToken = $line.Substring("set VERCEL_TOKEN=".Length).Trim()
        }
    }
}

if ([string]::IsNullOrWhiteSpace($VercelToken)) {
    throw "Falta VERCEL_TOKEN. Pásalo como parámetro, variable de entorno o deja disponible el fallback local."
}

$projectFile = "D:\Proyectos\LeaseManager\Produccion 1.0\frontend\.vercel\project.json"
if (([string]::IsNullOrWhiteSpace($ProjectId) -or [string]::IsNullOrWhiteSpace($TeamId)) -and (Test-Path $projectFile)) {
    $projectMeta = Get-Content -Raw $projectFile | ConvertFrom-Json
    if ([string]::IsNullOrWhiteSpace($ProjectId)) {
        $ProjectId = $projectMeta.projectId
    }
    if ([string]::IsNullOrWhiteSpace($TeamId)) {
        $TeamId = $projectMeta.orgId
    }
}

if ([string]::IsNullOrWhiteSpace($ProjectId) -or [string]::IsNullOrWhiteSpace($TeamId)) {
    throw "No se pudo resolver ProjectId/TeamId del proyecto Vercel enlazado."
}

$normalizedBackendUrl = $BackendUrl.Trim().TrimEnd('/')

if ($normalizedBackendUrl -notmatch '^https?://') {
    throw "BackendUrl debe incluir esquema http:// o https://"
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

Write-Host "VITE_API_BASE_URL => $normalizedBackendUrl" -ForegroundColor Green
Write-Host ("Targets: " + ($Targets -join ", ")) -ForegroundColor Green

if ($SkipDeploy) {
    Write-Host "Saltando redeploy por --SkipDeploy" -ForegroundColor Yellow
    exit 0
}

$frontendDir = "D:\Proyectos\LeaseManager\Produccion 1.0\frontend"
$vercelScope = "joaquins-projects-72185699"

Write-Host "`n==> Desplegando frontend en Vercel" -ForegroundColor Green
$latestDeploymentUrl = $null
$listOutput = & vercel list leasemanager-backoffice --token $VercelToken --scope $vercelScope 2>$null
foreach ($line in $listOutput) {
    if ($line -match 'https://leasemanager-backoffice-[^\s]+\.vercel\.app') {
        $latestDeploymentUrl = $Matches[0]
        break
    }
}

if ($latestDeploymentUrl) {
    & vercel redeploy $latestDeploymentUrl --target production --no-wait --scope $vercelScope --token $VercelToken
} else {
    & vercel --cwd $frontendDir --prod --yes --scope $vercelScope --token $VercelToken
}
if ($LASTEXITCODE -ne 0) {
    throw "Falló el redeploy del frontend en Vercel."
}

Write-Host "`n==> Listo" -ForegroundColor Green
Write-Host "Frontend: https://leasemanager-backoffice.vercel.app" -ForegroundColor Green
Write-Host "Backend:  $normalizedBackendUrl" -ForegroundColor Green

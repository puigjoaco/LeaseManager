param(
    [Parameter(Mandatory = $true)]
    [string]$BackendUrl,
    [string]$VercelToken = $env:VERCEL_TOKEN,
    [string]$ProjectId = "prj_VA58SoPZzzjOCaGjVHvaJoMFh6Xe",
    [string]$TeamId = "team_yP8rkOhe7Mj1UWoOnGwWKcvD",
    [string[]]$Targets = @("production", "preview"),
    [switch]$SkipDeploy
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($VercelToken)) {
    throw "Falta VERCEL_TOKEN. Pásalo como parámetro o variable de entorno."
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

Write-Host "`n==> Desplegando frontend en Vercel" -ForegroundColor Green
& vercel --cwd $frontendDir --prod --yes --scope joaquins-projects-72185699 --token $VercelToken
if ($LASTEXITCODE -ne 0) {
    throw "Falló el redeploy del frontend en Vercel."
}

Write-Host "`n==> Listo" -ForegroundColor Green
Write-Host "Frontend: https://leasemanager-backoffice.vercel.app" -ForegroundColor Green
Write-Host "Backend:  $normalizedBackendUrl" -ForegroundColor Green

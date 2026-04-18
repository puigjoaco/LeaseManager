param(
    [string]$FrontendUrl = 'https://leasemanager-backoffice.vercel.app/',
    [string]$ApiBaseUrl = 'https://surprising-balance-production.up.railway.app',
    [string]$BackendTestDb = '',
    [switch]$SkipSmoke
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Step($message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Assert-Condition($condition, $message) {
    if (-not $condition) {
        throw $message
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'
$frontendDir = Join-Path $repoRoot 'frontend'
$pythonExe = Join-Path $backendDir '.venv\Scripts\python.exe'
$smokeScript = Join-Path $PSScriptRoot 'smoke-public-backoffice.mjs'

Assert-Condition (Test-Path $pythonExe) "No existe el Python del backend en $pythonExe"
Assert-Condition (Test-Path $smokeScript) "No existe el smoke script en $smokeScript"

if (-not $BackendTestDb) {
    $resolvedDbPath = (Join-Path $backendDir 'test-acceptance-workflows.sqlite3') -replace '\\', '/'
    $BackendTestDb = "sqlite:///$resolvedDbPath"
}

$testTargets = @(
    'users.tests.UserAuthAPITests',
    'contratos.tests.ContratosAPITests',
    'documentos.tests.DocumentosAPITests',
    'canales.tests.CanalesAPITests',
    'cobranza.tests.CobranzaAPITests',
    'audit.tests.AuditAPITests',
    'conciliacion.tests.ConciliacionAPITests',
    'contabilidad.tests.ContabilidadAPITests',
    'reporting.tests.ReportingAPITests',
    'sii.tests.SiiAPITests'
)

Step "Backend acceptance suite"
$env:DATABASE_URL = $BackendTestDb
Push-Location $backendDir
try {
    & $pythonExe manage.py test @testTargets --keepdb
    Assert-Condition ($LASTEXITCODE -eq 0) 'La suite backend de acceptance fallo.'

    Step "Backend system check"
    & $pythonExe manage.py check
    Assert-Condition ($LASTEXITCODE -eq 0) 'manage.py check fallo.'
}
finally {
    Pop-Location
}

Step "Frontend build"
Push-Location $frontendDir
try {
    npm run build
    Assert-Condition ($LASTEXITCODE -eq 0) 'npm run build fallo.'
}
finally {
    Pop-Location
}

if (-not $SkipSmoke) {
    Step "Public smoke"
    $smokeOutput = & node $smokeScript --frontend-url $FrontendUrl --api-base-url $ApiBaseUrl | Out-String
    Assert-Condition ($LASTEXITCODE -eq 0) 'La smoke publica fallo.'

    $smokeResults = $smokeOutput | ConvertFrom-Json
    $adminResult = $smokeResults | Where-Object { $_.label -eq 'admin' } | Select-Object -First 1
    $reviewerResult = $smokeResults | Where-Object { $_.label -eq 'reviewer' } | Select-Object -First 1
    $partnerResult = $smokeResults | Where-Object { $_.label -eq 'partner' } | Select-Object -First 1

    Assert-Condition ($null -ne $adminResult) 'La smoke no devolvio resultado admin.'
    Assert-Condition ($null -ne $reviewerResult) 'La smoke no devolvio resultado reviewer.'
    Assert-Condition ($null -ne $partnerResult) 'La smoke no devolvio resultado partner.'
    Assert-Condition ($adminResult.ok -eq $true) 'La smoke admin no quedo OK.'
    Assert-Condition ($reviewerResult.ok -eq $true) 'La smoke reviewer no quedo OK.'
    Assert-Condition ($partnerResult.ok -eq $true) 'La smoke partner no quedo OK.'

    Assert-Condition ($adminResult.excerpt -match 'conciliacion\.ingreso desconocido') 'El overview admin no mostro la categoria real del backlog manual.'
    Assert-Condition ($adminResult.excerpt -notmatch 'Actualizando detalle de') 'El overview admin volvio a mostrar placeholder de backlog.'
    Assert-Condition ($reviewerResult.excerpt -match 'Configuración fiscal, eventos, asientos y cierres') 'Reviewer no aterrizo en Contabilidad.'
    Assert-Condition ($reviewerResult.excerpt -notmatch 'Cargando catálogo contable') 'Reviewer mostro carga residual de catalogo contable.'
    Assert-Condition ($reviewerResult.excerpt -notmatch 'Cargando actividad contable') 'Reviewer mostro carga residual de actividad contable.'
    Assert-Condition ($partnerResult.excerpt -match 'Resumen propio') 'El smoke partner no aterrizo en Reporting propio.'
    Assert-Condition ($partnerResult.excerpt -match 'Socio vinculado') 'El smoke partner no mostro el bloque de socio vinculado.'
    Assert-Condition ($partnerResult.excerpt -notmatch 'Sin resumen cargado') 'El smoke partner no alcanzo a cargar el resumen propio.'
    Assert-Condition ($partnerResult.excerpt -notmatch 'RUT\r?\nSin dato') 'El smoke partner no alcanzo a cargar el RUT del socio.'

    Step "Smoke summary"
    Write-Host ($smokeResults | ConvertTo-Json -Depth 6)
}

Step "Acceptance complete"
Write-Host "Workflow acceptance suite OK." -ForegroundColor Green

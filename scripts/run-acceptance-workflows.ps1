param(
    [string]$FrontendUrl = '',
    [string]$ApiBaseUrl = '',
    [string]$BackendTestDb = '',
    [string]$PythonExe = '',
    [switch]$OnlySmoke,
    [switch]$SkipSmoke,
    [switch]$RunPublicSmoke
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
$pythonExe = $PythonExe
if ([string]::IsNullOrWhiteSpace($pythonExe)) {
    $pythonExe = Join-Path $backendDir '.venv\Scripts\python.exe'
}
$smokeScript = Join-Path $PSScriptRoot 'smoke-public-backoffice.mjs'
$stage7ReadinessScript = Join-Path $PSScriptRoot 'run-stage7-readiness-gate.ps1'

$shouldRunPublicSmoke = $OnlySmoke -or $RunPublicSmoke

Assert-Condition (-not ($OnlySmoke -and $SkipSmoke)) 'OnlySmoke y SkipSmoke no pueden usarse juntos.'
Assert-Condition (-not ($RunPublicSmoke -and $SkipSmoke)) 'RunPublicSmoke y SkipSmoke no pueden usarse juntos.'
if (-not $OnlySmoke) {
    Assert-Condition (Test-Path $pythonExe) "No existe el Python del backend en $pythonExe"
}
if ($shouldRunPublicSmoke) {
    Assert-Condition (Test-Path $smokeScript) "No existe el smoke script en $smokeScript"
    Assert-Condition ($FrontendUrl.Trim()) 'FrontendUrl es obligatorio para ejecutar smoke publico.'
    Assert-Condition ($ApiBaseUrl.Trim()) 'ApiBaseUrl es obligatorio para ejecutar smoke publico.'
}

if (-not $BackendTestDb) {
    $resolvedDbPath = (Join-Path $backendDir 'test-acceptance-workflows.sqlite3') -replace '\\', '/'
    $BackendTestDb = "sqlite:///$resolvedDbPath"
}

$testTargets = @(
    'users.tests.UserAuthAPITests',
    'core.tests.PlatformBootstrapAPITests',
    'core.tests.EffectiveRoleUtilityTests',
    'core.tests_operational_observability',
    'core.tests_permissions.RolePermissionTests',
    'core.tests_scope_access.ScopeFilteringAPITests',
    'core.tests_stage1_matrix_audit.Stage1MatrixAuditTests',
    'health.tests.HealthEndpointTests',
    'patrimonio.tests.PatrimonioAPITests',
    'patrimonio.tests.PatrimonioMigrationSafetyTests',
    'operacion.tests.OperacionAPITests',
    'contratos.tests.ContratosAPITests',
    'documentos.tests.DocumentosAPITests',
    'documentos.tests.DocumentosScopeAPITests',
    'canales.tests.CanalesAPITests',
    'canales.tests.CanalesScopeAPITests',
    'cobranza.tests.CobranzaAPITests',
    'cobranza.tests.DistribucionCobroConstraintTests',
    'cobranza.tests.CobranzaMigrationSafetyTests',
    'cobranza.tests.CobranzaRepairMigrationSafetyTests',
    'audit.tests.AuditAPITests',
    'conciliacion.tests.ConciliacionAPITests',
    'contabilidad.tests.ContabilidadAPITests',
    'reporting.tests.ReportingAPITests',
    'compliance.tests.ComplianceAPITests',
    'sii.tests.SiiAPITests',
    'sii.tests.SiiMigrationSafetyTests'
)

if (-not $OnlySmoke) {
    Step "Backend acceptance suite"
    $env:DATABASE_URL = $BackendTestDb
    $env:REDIS_URL = ''
    $env:CELERY_RESULT_BACKEND = ''
    $env:DJANGO_CACHE_URL = 'locmem://leasemanager-acceptance-cache'
    Push-Location $backendDir
    try {
        & $pythonExe manage.py test @testTargets --keepdb
        Assert-Condition ($LASTEXITCODE -eq 0) 'La suite backend de acceptance fallo.'

        Step "Backend system check"
        & $pythonExe manage.py check
        Assert-Condition ($LASTEXITCODE -eq 0) 'manage.py check fallo.'

        Step "Backend migration consistency"
        & $pythonExe manage.py makemigrations --check --dry-run
        Assert-Condition ($LASTEXITCODE -eq 0) 'makemigrations --check --dry-run detecto cambios pendientes.'

        Step "Stage 1 matrix audit guard"
        & $pythonExe manage.py migrate --noinput
        Assert-Condition ($LASTEXITCODE -eq 0) 'migrate para auditor Stage 1 fallo.'
        $stage1AuditOutput = & $pythonExe manage.py audit_stage1_matrix --source-kind local --source-label acceptance-local | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'audit_stage1_matrix fallo.'
        if ($stage1AuditOutput.Trim()) {
            Write-Host $stage1AuditOutput
        }
        $stage1Audit = $stage1AuditOutput | ConvertFrom-Json
        Assert-Condition ($stage1Audit.ready_for_stage1_close -eq $false) 'Una fuente local no evidencial no puede cerrar Etapa 1.'
        Assert-Condition ($stage1Audit.evidence_grade -eq $false) 'La auditoria local de Etapa 1 no debe marcar evidencia suficiente.'

        Step "Stage 7 readiness guard"
        Assert-Condition (Test-Path $stage7ReadinessScript) "No existe el guard de readiness Etapa 7 en $stage7ReadinessScript"
        $stage7OutputPath = Join-Path $repoRoot 'local-evidence\stage7\acceptance\stage7_readiness_acceptance.json'
        $stage7Output = & $stage7ReadinessScript -PythonExe $pythonExe -DatabaseUrl $BackendTestDb -OutputPath $stage7OutputPath -SkipMigrations | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-stage7-readiness-gate fallo.'
        if ($stage7Output.Trim()) {
            Write-Host $stage7Output
        }
        $stage7Readiness = Get-Content -LiteralPath $stage7OutputPath -Raw | ConvertFrom-Json
        Assert-Condition ($stage7Readiness.ready_for_stage7_close -eq $false) 'El guard local no puede cerrar Operacion productiva sin restore, smoke y aceptacion.'
        Assert-Condition ($stage7Readiness.classification -eq 'parcial') 'La readiness local Etapa 7 debe quedar parcial hasta evidencias externas/controladas.'
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
}

if ($shouldRunPublicSmoke) {
    Step "Public smoke via UI login"
    $smokeOutput = & node $smokeScript --allow-external --frontend-url $FrontendUrl --api-base-url $ApiBaseUrl | Out-String
    $smokeExitCode = $LASTEXITCODE
    if ($smokeOutput.Trim()) {
        Write-Host $smokeOutput
    }

    $smokeResults = $smokeOutput | ConvertFrom-Json
    Assert-Condition ($smokeExitCode -eq 0) 'La smoke publica fallo.'
    $adminResult = $smokeResults | Where-Object { $_.label -eq 'admin' } | Select-Object -First 1
    $operatorResult = $smokeResults | Where-Object { $_.label -eq 'operator' } | Select-Object -First 1
    $reviewerResult = $smokeResults | Where-Object { $_.label -eq 'reviewer' } | Select-Object -First 1
    $partnerResult = $smokeResults | Where-Object { $_.label -eq 'partner' } | Select-Object -First 1

    Assert-Condition ($null -ne $adminResult) 'La smoke no devolvio resultado admin.'
    Assert-Condition ($null -ne $operatorResult) 'La smoke no devolvio resultado operator.'
    Assert-Condition ($null -ne $reviewerResult) 'La smoke no devolvio resultado reviewer.'
    Assert-Condition ($null -ne $partnerResult) 'La smoke no devolvio resultado partner.'
    Assert-Condition ($adminResult.ok -eq $true) 'La smoke admin no quedo OK.'
    Assert-Condition ($operatorResult.ok -eq $true) 'La smoke operator no quedo OK.'
    Assert-Condition ($reviewerResult.ok -eq $true) 'La smoke reviewer no quedo OK.'
    Assert-Condition ($partnerResult.ok -eq $true) 'La smoke partner no quedo OK.'
    Assert-Condition ($adminResult.authFlow -eq 'ui-login') 'La smoke admin no paso por el login real del frontend.'
    Assert-Condition ($operatorResult.authFlow -eq 'ui-login') 'La smoke operator no paso por el login real del frontend.'
    Assert-Condition ($reviewerResult.authFlow -eq 'ui-login') 'La smoke reviewer no paso por el login real del frontend.'
    Assert-Condition ($partnerResult.authFlow -eq 'ui-login') 'La smoke partner no paso por el login real del frontend.'

    Assert-Condition ($adminResult.excerpt -match 'conciliacion\.ingreso desconocido') 'El overview admin no mostro la categoria real del backlog manual.'
    Assert-Condition ($adminResult.excerpt -notmatch 'Actualizando detalle de') 'El overview admin volvio a mostrar placeholder de backlog.'
    Assert-Condition ($operatorResult.excerpt -match 'Demo Operador de Cartera') 'La smoke operator no aterrizo en el perfil correcto.'
    Assert-Condition ($operatorResult.excerpt -match 'Resoluciones abiertas') 'La smoke operator no mostro el resumen operativo.'
    Assert-Condition ($operatorResult.excerpt -notmatch 'Contabilidad') 'La smoke operator expuso tabs de control no permitidas.'
    Assert-Condition ($reviewerResult.excerpt -match 'Configuración fiscal, eventos, asientos y cierres') 'Reviewer no aterrizo en Contabilidad.'
    Assert-Condition ($reviewerResult.excerpt -notmatch 'Cargando catálogo contable') 'Reviewer mostro carga residual de catalogo contable.'
    Assert-Condition ($reviewerResult.excerpt -notmatch 'Cargando actividad contable') 'Reviewer mostro carga residual de actividad contable.'
    Assert-Condition ($partnerResult.excerpt -match 'Resumen propio') 'El smoke partner no aterrizo en Reporting propio.'
    Assert-Condition ($partnerResult.excerpt -match 'Socio vinculado') 'El smoke partner no mostro el bloque de socio vinculado.'
    Assert-Condition ($partnerResult.excerpt -notmatch 'Sin resumen cargado') 'El smoke partner no alcanzo a cargar el resumen propio.'
    Assert-Condition ($partnerResult.excerpt -notmatch 'RUT\r?\nSin dato') 'El smoke partner no alcanzo a cargar el RUT del socio.'

    Step "Smoke summary"
    Write-Host ($smokeResults | ConvertTo-Json -Depth 6)
} else {
    Step "Public smoke skipped"
    Write-Host "Smoke publico omitido. Ejecutar con -RunPublicSmoke o -OnlySmoke y URLs explicitas solo con ambiente autorizado." -ForegroundColor Yellow
}

Step "Acceptance complete"
Write-Host "Workflow acceptance suite OK." -ForegroundColor Green

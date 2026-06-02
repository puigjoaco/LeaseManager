param(
    [string]$FrontendUrl = '',
    [string]$ApiBaseUrl = '',
    [string]$BackendTestDb = '',
    [string]$PythonExe = '',
    [string]$PublicSmokeSourceKind = '',
    [string]$PublicSmokeAuthorizationRef = '',
    [string]$PublicSmokeEnvironmentRef = '',
    [string]$PublicSmokeTargetRef = '',
    [string]$PublicSmokeResponsibleRef = '',
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

function Assert-ReadinessOutputGuard($scriptPath, $label, $blockedFileName, [hashtable]$extraParams = @{}) {
    Assert-Condition (Test-Path $scriptPath) "No existe el wrapper $label en $scriptPath"
    $blockedOutputPath = Join-Path $repoRoot "docs\$blockedFileName"
    Assert-Condition (-not (Test-Path $blockedOutputPath)) "La ruta bloqueada para $label ya existe: $blockedOutputPath"

    $guardFailed = $false
    $guardOutput = ''
    $commandParams = @{}
    foreach ($key in $extraParams.Keys) {
        $commandParams[$key] = $extraParams[$key]
    }
    $commandParams['PythonExe'] = $pythonExe
    $commandParams['OutputPath'] = $blockedOutputPath

    try {
        $guardOutput = & $scriptPath @commandParams 2>&1 | Out-String
    }
    catch {
        $guardOutput = "$($_.Exception.Message)`n$($_ | Out-String)"
        $guardFailed = $true
    }

    Assert-Condition $guardFailed "$label debe rechazar OutputPath versionable antes de generar auditoria."
    Assert-Condition ($guardOutput -match 'local-evidence') "El rechazo de OutputPath en $label debe indicar local-evidence como ubicacion permitida."
    Assert-Condition (-not (Test-Path $blockedOutputPath)) "$label no debe crear evidencia versionable bajo docs/."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'
$frontendDir = Join-Path $repoRoot 'frontend'
$pythonExe = $PythonExe
if ([string]::IsNullOrWhiteSpace($pythonExe)) {
    $pythonExe = Join-Path $backendDir '.venv\Scripts\python.exe'
}
$smokeScript = Join-Path $PSScriptRoot 'smoke-public-backoffice.mjs'
$stage1LocalReadinessScript = Join-Path $PSScriptRoot 'run-stage1-local-readiness.ps1'
$stage1SnapshotGateScript = Join-Path $PSScriptRoot 'run-stage1-snapshot-gate.ps1'
$stage2ReadinessScript = Join-Path $PSScriptRoot 'run-stage2-readiness-gate.ps1'
$stage3ReadinessScript = Join-Path $PSScriptRoot 'run-stage3-readiness-gate.ps1'
$stage4ReadinessScript = Join-Path $PSScriptRoot 'run-stage4-readiness-gate.ps1'
$stage5ReadinessScript = Join-Path $PSScriptRoot 'run-stage5-readiness-gate.ps1'
$stage5DocumentsReadinessScript = Join-Path $PSScriptRoot 'run-stage5-documents-readiness-gate.ps1'
$stage6ReadinessScript = Join-Path $PSScriptRoot 'run-stage6-readiness-gate.ps1'
$stage7ReadinessScript = Join-Path $PSScriptRoot 'run-stage7-readiness-gate.ps1'
$complianceDataReadinessScript = Join-Path $PSScriptRoot 'run-compliance-data-readiness-gate.ps1'
$restoreRehearsalScript = Join-Path $PSScriptRoot 'run-postgres-restore-rehearsal.ps1'
$repoHygieneScript = Join-Path $PSScriptRoot 'assert-repo-hygiene.ps1'

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
    'core.tests_stage2_cobranza_readiness.Stage2CobranzaReadinessTests',
    'core.tests_stage3_conciliacion_readiness.Stage3ConciliacionReadinessTests',
    'core.tests_stage4_sii_readiness.Stage4SiiReadinessTests',
    'core.tests_stage5_contabilidad_readiness.Stage5ContabilidadReadinessTests',
    'core.tests_stage6_renta_anual_readiness.Stage6RentaAnualReadinessTests',
    'core.tests_stage7_reporting_readiness.Stage7ReportingReadinessTests',
    'core.tests_compliance_data_readiness.ComplianceDataReadinessTests',
    'health.tests.HealthEndpointTests',
    'patrimonio.tests.PatrimonioAPITests',
    'patrimonio.tests.PatrimonioMigrationSafetyTests',
    'operacion.tests.OperacionAPITests',
    'contratos.tests.ContratosAPITests',
    'documentos.tests.DocumentosAPITests',
    'documentos.tests.DocumentosScopeAPITests',
    'documentos.tests_readiness.DocumentReadinessAuditTests',
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
    Step "Repo hygiene guard"
    Assert-Condition (Test-Path $repoHygieneScript) "No existe el guard de higiene del repo en $repoHygieneScript"
    & $repoHygieneScript
    Assert-Condition ($LASTEXITCODE -eq 0) 'assert-repo-hygiene fallo.'

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

        Step "Stage 1 local readiness wrapper"
        Assert-Condition (Test-Path $stage1LocalReadinessScript) "No existe el guard local de readiness Etapa 1 en $stage1LocalReadinessScript"
        $stage1LocalReadinessOutputPath = Join-Path $repoRoot 'local-evidence\stage1\acceptance\stage1_local_readiness_acceptance.json'
        $stage1LocalReadinessOutput = & $stage1LocalReadinessScript -PythonExe $pythonExe -OutputPath $stage1LocalReadinessOutputPath | Out-String
        if ($stage1LocalReadinessOutput.Trim()) {
            Write-Host $stage1LocalReadinessOutput
        }
        Assert-Condition (Test-Path $stage1LocalReadinessOutputPath) 'run-stage1-local-readiness no genero JSON de auditoria.'
        $stage1LocalReadiness = Get-Content -LiteralPath $stage1LocalReadinessOutputPath -Raw | ConvertFrom-Json
        $stage1LocalIssueCodes = @($stage1LocalReadiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage1LocalReadiness.source_kind -eq 'local') 'El readiness local debe declarar source_kind=local.'
        Assert-Condition ($stage1LocalReadiness.evidence_grade -eq $false) 'El readiness local no debe marcar evidence_grade.'
        Assert-Condition ($stage1LocalReadiness.ready_for_stage1_close -eq $false) 'El readiness local no puede cerrar Etapa 1.'
        Assert-Condition ($stage1LocalReadiness.classification -eq 'implementado_sin_evidencia') 'El readiness local debe quedar no evidencial.'
        Assert-Condition (-not ($stage1LocalIssueCodes -contains 'stage1.data_missing')) 'stage1.data_missing debe quedar reservado para el gate evidencial con require-data.'

        Step "Stage 1 snapshot gate empty evidence guard"
        Assert-Condition (Test-Path $stage1SnapshotGateScript) "No existe el snapshot gate Etapa 1 en $stage1SnapshotGateScript"
        $stage1SnapshotEmptyDbPath = Join-Path $repoRoot 'local-evidence\stage1\acceptance\stage1_snapshot_empty_acceptance.sqlite3'
        $stage1SnapshotEmptyOutputPath = Join-Path $repoRoot 'local-evidence\stage1\acceptance\stage1_snapshot_empty_acceptance.json'
        Remove-Item -LiteralPath $stage1SnapshotEmptyDbPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $stage1SnapshotEmptyOutputPath -Force -ErrorAction SilentlyContinue

        $stage1SnapshotEmptyFailed = $false
        try {
            $stage1SnapshotEmptyOutput = & $stage1SnapshotGateScript `
                -SourceKind snapshot_controlado `
                -SourceLabel 'stage1-empty-snapshot-acceptance' `
                -AuthorizationRef 'stage-one-empty-snapshot-authz' `
                -ResponsibleRef 'stage-one-empty-snapshot-owner' `
                -DatabaseUrl 'sqlite:///local-evidence/stage1/acceptance/stage1_snapshot_empty_acceptance.sqlite3' `
                -OutputPath $stage1SnapshotEmptyOutputPath `
                -PythonExe $pythonExe `
                -RunMigrations 2>&1 | Out-String
        }
        catch {
            $stage1SnapshotEmptyOutput = "$($_.Exception.Message)`n$($_ | Out-String)"
            $stage1SnapshotEmptyFailed = $true
        }
        if ($stage1SnapshotEmptyOutput.Trim()) {
            Write-Host $stage1SnapshotEmptyOutput
        }
        Assert-Condition $stage1SnapshotEmptyFailed 'El snapshot gate evidencial con SQLite vacio debe fallar, no cerrar Etapa 1.'
        Assert-Condition (Test-Path $stage1SnapshotEmptyOutputPath) 'El snapshot gate vacio debe dejar JSON de auditoria bajo local-evidence/.'
        $stage1SnapshotEmptyAudit = Get-Content -LiteralPath $stage1SnapshotEmptyOutputPath -Raw | ConvertFrom-Json
        $stage1SnapshotEmptyIssueCodes = @($stage1SnapshotEmptyAudit.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage1SnapshotEmptyAudit.source_kind -eq 'snapshot_controlado') 'El snapshot gate vacio debe declarar source_kind=snapshot_controlado.'
        Assert-Condition ($stage1SnapshotEmptyAudit.evidence_grade -eq $true) 'El snapshot gate vacio debe marcar la fuente como evidencial por tipo.'
        Assert-Condition ($stage1SnapshotEmptyAudit.has_required_stage1_data -eq $false) 'El snapshot gate vacio no debe marcar datos requeridos.'
        Assert-Condition ($stage1SnapshotEmptyAudit.ready_for_stage1_close -eq $false) 'El snapshot gate vacio no puede cerrar Etapa 1.'
        Assert-Condition ($stage1SnapshotEmptyAudit.classification -eq 'bloqueado_dato_real') 'El snapshot gate vacio debe clasificar bloqueado_dato_real.'
        Assert-Condition ($stage1SnapshotEmptyIssueCodes -contains 'stage1.data_missing') 'El snapshot gate vacio debe reportar stage1.data_missing.'

        Step "Stage 1 real source migration guard"
        $stage1RealMigrationOutputPath = Join-Path $repoRoot 'local-evidence\stage1\acceptance\stage1_real_migration_forbidden.json'
        Remove-Item -LiteralPath $stage1RealMigrationOutputPath -Force -ErrorAction SilentlyContinue

        $stage1RealMigrationFailed = $false
        try {
            $stage1RealMigrationOutput = & $stage1SnapshotGateScript `
                -SourceKind real_autorizado `
                -SourceLabel 'stage1-real-migration-guard' `
                -AuthorizationRef 'stage-one-real-migration-authz' `
                -ResponsibleRef 'stage-one-real-migration-owner' `
                -DatabaseUrl 'sqlite:///local-evidence/stage1/acceptance/stage1_real_migration_forbidden.sqlite3' `
                -OutputPath $stage1RealMigrationOutputPath `
                -PythonExe $pythonExe `
                -RunMigrations 2>&1 | Out-String
        }
        catch {
            $stage1RealMigrationOutput = "$($_.Exception.Message)`n$($_ | Out-String)"
            $stage1RealMigrationFailed = $true
        }
        if ($stage1RealMigrationOutput.Trim()) {
            Write-Host $stage1RealMigrationOutput
        }
        Assert-Condition $stage1RealMigrationFailed 'El snapshot gate debe rechazar -RunMigrations con real_autorizado.'
        Assert-Condition ($stage1RealMigrationOutput -match 'No se ejecutan migraciones contra real_autorizado') 'El rechazo debe explicar que no se migra real_autorizado desde este gate.'
        Assert-Condition (-not (Test-Path $stage1RealMigrationOutputPath)) 'El rechazo de migracion real_autorizado debe ocurrir antes de generar JSON de auditoria.'

        Step "Stage 2 readiness guard"
        Assert-Condition (Test-Path $stage2ReadinessScript) "No existe el guard de readiness Etapa 2 en $stage2ReadinessScript"
        $stage2OutputPath = Join-Path $repoRoot 'local-evidence\stage2\acceptance\stage2_readiness_acceptance.json'
        $stage2Output = & $stage2ReadinessScript -PythonExe $pythonExe -OutputPath $stage2OutputPath | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-stage2-readiness-gate fallo.'
        if ($stage2Output.Trim()) {
            Write-Host $stage2Output
        }
        $stage2Readiness = Get-Content -LiteralPath $stage2OutputPath -Raw | ConvertFrom-Json
        $stage2IssueCodes = @($stage2Readiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage2Readiness.source_kind -eq 'local') 'El guard Etapa 2 local debe declarar source_kind=local.'
        Assert-Condition ($stage2Readiness.source_kind_authorized_for_close -eq $false) 'El guard Etapa 2 local no puede quedar autorizado para cierre.'
        Assert-Condition ($stage2Readiness.ready_for_stage2_cobranza -eq $false) 'El guard Etapa 2 local no puede cerrar Cobranza.'
        Assert-Condition ($stage2Readiness.classification -eq 'parcial') 'El guard Etapa 2 local debe quedar parcial.'
        Assert-Condition ($stage2IssueCodes -contains 'stage2.source_kind_not_authorized') 'El guard Etapa 2 local debe reportar source_kind_not_authorized.'

        Step "Stage 3 readiness guard"
        Assert-Condition (Test-Path $stage3ReadinessScript) "No existe el guard de readiness Etapa 3 en $stage3ReadinessScript"
        $stage3OutputPath = Join-Path $repoRoot 'local-evidence\stage3\acceptance\stage3_readiness_acceptance.json'
        $stage3Output = & $stage3ReadinessScript -PythonExe $pythonExe -OutputPath $stage3OutputPath | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-stage3-readiness-gate fallo.'
        if ($stage3Output.Trim()) {
            Write-Host $stage3Output
        }
        $stage3Readiness = Get-Content -LiteralPath $stage3OutputPath -Raw | ConvertFrom-Json
        $stage3IssueCodes = @($stage3Readiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage3Readiness.source_kind -eq 'local') 'El guard Etapa 3 local debe declarar source_kind=local.'
        Assert-Condition ($stage3Readiness.source_kind_authorized_for_close -eq $false) 'El guard Etapa 3 local no puede quedar autorizado para cierre.'
        Assert-Condition ($stage3Readiness.ready_for_stage3_conciliacion -eq $false) 'El guard Etapa 3 local no puede cerrar Conciliacion.'
        Assert-Condition ($stage3Readiness.classification -eq 'parcial') 'El guard Etapa 3 local debe quedar parcial.'
        Assert-Condition ($stage3IssueCodes -contains 'stage3.source_kind_not_authorized') 'El guard Etapa 3 local debe reportar source_kind_not_authorized.'

        Step "Stage 4 readiness guard"
        Assert-Condition (Test-Path $stage4ReadinessScript) "No existe el guard de readiness Etapa 4 en $stage4ReadinessScript"
        $stage4OutputPath = Join-Path $repoRoot 'local-evidence\stage4\acceptance\stage4_readiness_acceptance.json'
        $stage4Output = & $stage4ReadinessScript -PythonExe $pythonExe -OutputPath $stage4OutputPath | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-stage4-readiness-gate fallo.'
        if ($stage4Output.Trim()) {
            Write-Host $stage4Output
        }
        $stage4Readiness = Get-Content -LiteralPath $stage4OutputPath -Raw | ConvertFrom-Json
        $stage4IssueCodes = @($stage4Readiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage4Readiness.source_kind -eq 'local') 'El guard Etapa 4 local debe declarar source_kind=local.'
        Assert-Condition ($stage4Readiness.source_kind_authorized_for_close -eq $false) 'El guard Etapa 4 local no puede quedar autorizado para cierre.'
        Assert-Condition ($stage4Readiness.ready_for_stage4_sii -eq $false) 'El guard Etapa 4 local no puede cerrar SII.'
        Assert-Condition ($stage4Readiness.classification -eq 'parcial') 'El guard Etapa 4 local debe quedar parcial.'
        Assert-Condition ($stage4IssueCodes -contains 'stage4.source_kind_not_authorized') 'El guard Etapa 4 local debe reportar source_kind_not_authorized.'

        Step "Stage 5 readiness guard"
        Assert-Condition (Test-Path $stage5ReadinessScript) "No existe el guard de readiness Etapa 5 en $stage5ReadinessScript"
        $stage5OutputPath = Join-Path $repoRoot 'local-evidence\stage5\acceptance\stage5_readiness_acceptance.json'
        $stage5Output = & $stage5ReadinessScript -PythonExe $pythonExe -OutputPath $stage5OutputPath | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-stage5-readiness-gate fallo.'
        if ($stage5Output.Trim()) {
            Write-Host $stage5Output
        }
        $stage5Readiness = Get-Content -LiteralPath $stage5OutputPath -Raw | ConvertFrom-Json
        $stage5IssueCodes = @($stage5Readiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage5Readiness.source_kind -eq 'local') 'El guard Etapa 5 local debe declarar source_kind=local.'
        Assert-Condition ($stage5Readiness.source_kind_authorized_for_close -eq $false) 'El guard Etapa 5 local no puede quedar autorizado para cierre.'
        Assert-Condition ($stage5Readiness.ready_for_stage5_contabilidad -eq $false) 'El guard Etapa 5 local no puede cerrar Contabilidad.'
        Assert-Condition ($stage5Readiness.classification -eq 'parcial') 'El guard Etapa 5 local debe quedar parcial.'
        Assert-Condition ($stage5IssueCodes -contains 'stage5.source_kind_not_authorized') 'El guard Etapa 5 local debe reportar source_kind_not_authorized.'

        Step "Stage 5 documents readiness guard"
        Assert-Condition (Test-Path $stage5DocumentsReadinessScript) "No existe el guard de readiness documental Etapa 5 en $stage5DocumentsReadinessScript"
        $stage5DocumentsOutputPath = Join-Path $repoRoot 'local-evidence\stage5-documents\acceptance\stage5_documents_readiness_acceptance.json'
        $stage5DocumentsOutput = & $stage5DocumentsReadinessScript -PythonExe $pythonExe -OutputPath $stage5DocumentsOutputPath | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-stage5-documents-readiness-gate fallo.'
        if ($stage5DocumentsOutput.Trim()) {
            Write-Host $stage5DocumentsOutput
        }
        $stage5DocumentsReadiness = Get-Content -LiteralPath $stage5DocumentsOutputPath -Raw | ConvertFrom-Json
        $stage5DocumentsIssueCodes = @($stage5DocumentsReadiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage5DocumentsReadiness.source_kind -eq 'local') 'El guard documental Etapa 5 local debe declarar source_kind=local.'
        Assert-Condition ($stage5DocumentsReadiness.source_kind_authorized_for_close -eq $false) 'El guard documental Etapa 5 local no puede quedar autorizado para cierre.'
        Assert-Condition ($stage5DocumentsReadiness.ready_for_stage5_documents -eq $false) 'El guard documental Etapa 5 local no puede cerrar Documentos.'
        Assert-Condition ($stage5DocumentsReadiness.classification -eq 'parcial') 'El guard documental Etapa 5 local debe quedar parcial.'
        Assert-Condition ($stage5DocumentsIssueCodes -contains 'documents.source_kind_not_authorized') 'El guard documental Etapa 5 local debe reportar source_kind_not_authorized.'

        Step "Stage 6 readiness guard"
        Assert-Condition (Test-Path $stage6ReadinessScript) "No existe el guard de readiness Etapa 6 en $stage6ReadinessScript"
        $stage6OutputPath = Join-Path $repoRoot 'local-evidence\stage6\acceptance\stage6_readiness_acceptance.json'
        $stage6Output = & $stage6ReadinessScript -PythonExe $pythonExe -OutputPath $stage6OutputPath | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-stage6-readiness-gate fallo.'
        if ($stage6Output.Trim()) {
            Write-Host $stage6Output
        }
        $stage6Readiness = Get-Content -LiteralPath $stage6OutputPath -Raw | ConvertFrom-Json
        $stage6IssueCodes = @($stage6Readiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage6Readiness.source_kind -eq 'local') 'El guard Etapa 6 local debe declarar source_kind=local.'
        Assert-Condition ($stage6Readiness.source_kind_authorized_for_close -eq $false) 'El guard Etapa 6 local no puede quedar autorizado para cierre.'
        Assert-Condition ($stage6Readiness.ready_for_stage6_renta_anual -eq $false) 'El guard Etapa 6 local no puede cerrar Renta anual.'
        Assert-Condition ($stage6Readiness.classification -eq 'parcial') 'El guard Etapa 6 local debe quedar parcial.'
        Assert-Condition ($stage6IssueCodes -contains 'stage6.source_kind_not_authorized') 'El guard Etapa 6 local debe reportar source_kind_not_authorized.'

        Step "Stage 7 readiness guard"
        Assert-Condition (Test-Path $stage7ReadinessScript) "No existe el guard de readiness Etapa 7 en $stage7ReadinessScript"
        $stage7OutputPath = Join-Path $repoRoot 'local-evidence\stage7\acceptance\stage7_readiness_acceptance.json'
        $stage7Output = & $stage7ReadinessScript -PythonExe $pythonExe -DatabaseUrl $BackendTestDb -OutputPath $stage7OutputPath -SkipMigrations | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-stage7-readiness-gate fallo.'
        if ($stage7Output.Trim()) {
            Write-Host $stage7Output
        }
        $stage7Readiness = Get-Content -LiteralPath $stage7OutputPath -Raw | ConvertFrom-Json
        $stage7IssueCodes = @($stage7Readiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage7Readiness.ready_for_stage7_close -eq $false) 'El guard local no puede cerrar Operacion productiva sin restore, smoke y aceptacion.'
        Assert-Condition ($stage7Readiness.classification -eq 'parcial') 'La readiness local Etapa 7 debe quedar parcial hasta evidencias externas/controladas.'
        Assert-Condition ($stage7Readiness.PSObject.Properties.Name -contains 'reporting') 'El guard Etapa 7 debe consolidar readiness de Reporting.'
        Assert-Condition ($stage7Readiness.reporting.ready_for_stage7_reporting -eq $false) 'El guard local no puede cerrar Operacion productiva si Reporting no esta listo.'
        Assert-Condition ($stage7Readiness.reporting.source_kind_authorized_for_close -eq $false) 'Reporting local no debe quedar autorizado para cierre productivo.'
        Assert-Condition ($stage7IssueCodes -contains 'stage7.reporting_not_ready') 'El guard Etapa 7 debe bloquear cierre cuando Reporting sigue parcial.'

        Step "Compliance data readiness guard"
        Assert-Condition (Test-Path $complianceDataReadinessScript) "No existe el guard de readiness Compliance en $complianceDataReadinessScript"
        $complianceDataOutputPath = Join-Path $repoRoot 'local-evidence\compliance\acceptance\compliance_data_readiness_acceptance.json'
        $complianceDataOutput = & $complianceDataReadinessScript -PythonExe $pythonExe -OutputPath $complianceDataOutputPath | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-compliance-data-readiness-gate fallo.'
        if ($complianceDataOutput.Trim()) {
            Write-Host $complianceDataOutput
        }
        $complianceDataReadiness = Get-Content -LiteralPath $complianceDataOutputPath -Raw | ConvertFrom-Json
        $complianceDataIssueCodes = @($complianceDataReadiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($complianceDataReadiness.source_kind -eq 'local') 'El guard Compliance local debe declarar source_kind=local.'
        Assert-Condition ($complianceDataReadiness.source_kind_authorized_for_close -eq $false) 'El guard Compliance local no puede quedar autorizado para cierre.'
        Assert-Condition ($complianceDataReadiness.ready_for_compliance_data -eq $false) 'El guard Compliance local no puede cerrar DatosPersonalesChile2026.'
        Assert-Condition ($complianceDataReadiness.classification -eq 'parcial') 'El guard Compliance local debe quedar parcial.'
        Assert-Condition ($complianceDataIssueCodes -contains 'compliance.source_kind_not_authorized') 'El guard Compliance local debe reportar source_kind_not_authorized.'

        Step "Stage 7 explicit evidence authorization guard"
        $stage7AcceptanceDir = Split-Path -Parent $stage7OutputPath
        New-Item -ItemType Directory -Force -Path $stage7AcceptanceDir | Out-Null

        $restoreMissingAuthorizationPath = Join-Path $stage7AcceptanceDir 'restore_missing_authorization_ref.json'
        $smokeMissingAuthorizationPath = Join-Path $stage7AcceptanceDir 'smoke_missing_authorization_ref.json'
        $smokeAuthorizedPath = Join-Path $stage7AcceptanceDir 'smoke_authorized.json'
        $finalAcceptanceAuthorizedPath = Join-Path $stage7AcceptanceDir 'final_acceptance_authorized.json'
        $stage7AuthorizationOutputPath = Join-Path $stage7AcceptanceDir 'stage7_restore_smoke_missing_authorization_ref.json'

        [ordered]@{
            restore_verified = $true
            source_kind = 'backup_autorizado'
            responsible_ref = 'restore-owner-v1'
            backup_ref = 'backup-snapshot-v1'
        } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $restoreMissingAuthorizationPath -Encoding UTF8

        [ordered]@{
            source_kind = 'public_smoke_autorizado'
            responsible_ref = 'smoke-owner-v1'
            environment_ref = 'staging-env-v1'
            target_ref = 'deployment-target-v1'
            results = @(
                [ordered]@{ label = 'admin'; ok = $true; authFlow = 'ui-login' },
                [ordered]@{ label = 'operator'; ok = $true; authFlow = 'ui-login' },
                [ordered]@{ label = 'reviewer'; ok = $true; authFlow = 'ui-login' },
                [ordered]@{ label = 'partner'; ok = $true; authFlow = 'ui-login' }
            )
        } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $smokeMissingAuthorizationPath -Encoding UTF8

        [ordered]@{
            source_kind = 'public_smoke_autorizado'
            authorization_ref = 'smoke-authorization-v1'
            environment_ref = 'staging-env-v1'
            target_ref = 'deployment-target-v1'
            results = @(
                [ordered]@{ label = 'admin'; ok = $true; authFlow = 'ui-login' },
                [ordered]@{ label = 'operator'; ok = $true; authFlow = 'ui-login' },
                [ordered]@{ label = 'reviewer'; ok = $true; authFlow = 'ui-login' },
                [ordered]@{ label = 'partner'; ok = $true; authFlow = 'ui-login' }
            )
        } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $smokeAuthorizedPath -Encoding UTF8

        [ordered]@{
            accepted = $true
            source_kind = 'aceptacion_final_autorizada'
            authorization_ref = 'final-authorization-v1'
            responsible_ref = 'final-owner-v1'
            scope_ref = 'release-candidate-v1'
            acceptance_ref = 'final-decision-v1'
        } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $finalAcceptanceAuthorizedPath -Encoding UTF8

        $stage7AuthorizationOutput = & $stage7ReadinessScript `
            -PythonExe $pythonExe `
            -DatabaseUrl $BackendTestDb `
            -OutputPath $stage7AuthorizationOutputPath `
            -RestoreEvidencePath $restoreMissingAuthorizationPath `
            -PublicSmokeEvidencePath $smokeMissingAuthorizationPath `
            -FinalAcceptanceEvidencePath $finalAcceptanceAuthorizedPath `
            -SkipMigrations | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-stage7-readiness-gate fallo al validar authorization_ref explicito.'
        if ($stage7AuthorizationOutput.Trim()) {
            Write-Host $stage7AuthorizationOutput
        }

        $stage7AuthorizationReadiness = Get-Content -LiteralPath $stage7AuthorizationOutputPath -Raw | ConvertFrom-Json
        $stage7AuthorizationIssueCodes = @($stage7AuthorizationReadiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage7AuthorizationIssueCodes -contains 'stage7.restore_authorization_ref_missing') 'Restore con responsible_ref no debe pasar como authorization_ref.'
        Assert-Condition ($stage7AuthorizationIssueCodes -contains 'stage7.public_smoke_authorization_ref_missing') 'Smoke con responsible_ref no debe pasar como authorization_ref.'
        Assert-Condition ($stage7AuthorizationReadiness.restore_evidence.has_authorization_ref -eq $false) 'Restore debe marcar has_authorization_ref=false si solo tiene responsible_ref.'
        Assert-Condition ($stage7AuthorizationReadiness.public_smoke_evidence.has_authorization_ref -eq $false) 'Smoke debe marcar has_authorization_ref=false si solo tiene responsible_ref.'

        $restoreSensitiveRefPath = Join-Path $stage7AcceptanceDir 'restore_sensitive_authorization_ref.json'
        $smokeSensitiveRefPath = Join-Path $stage7AcceptanceDir 'smoke_sensitive_environment_ref.json'
        $finalAcceptanceSensitiveRefPath = Join-Path $stage7AcceptanceDir 'final_acceptance_sensitive_ref.json'
        $stage7SensitiveRefOutputPath = Join-Path $stage7AcceptanceDir 'stage7_sensitive_release_refs.json'

        [ordered]@{
            restore_verified = $true
            source_kind = 'backup_autorizado'
            authorization_ref = 'https://evidence.example.test/restore?token=dummy'
            backup_ref = 'backup-snapshot-v1'
        } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $restoreSensitiveRefPath -Encoding UTF8

        [ordered]@{
            source_kind = 'public_smoke_autorizado'
            authorization_ref = 'smoke-authorization-v1'
            environment_ref = 'ops@example.test'
            target_ref = 'deployment-target-v1'
            results = @(
                [ordered]@{ label = 'admin'; ok = $true; authFlow = 'ui-login' },
                [ordered]@{ label = 'operator'; ok = $true; authFlow = 'ui-login' },
                [ordered]@{ label = 'reviewer'; ok = $true; authFlow = 'ui-login' },
                [ordered]@{ label = 'partner'; ok = $true; authFlow = 'ui-login' }
            )
        } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $smokeSensitiveRefPath -Encoding UTF8

        [ordered]@{
            accepted = $true
            source_kind = 'aceptacion_final_autorizada'
            authorization_ref = 'final-authorization-v1'
            responsible_ref = 'final-owner-v1'
            scope_ref = 'release-candidate-v1'
            acceptance_ref = 'https://decision.example.test/signoff?token=dummy'
        } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $finalAcceptanceSensitiveRefPath -Encoding UTF8

        $stage7SensitiveRefOutput = & $stage7ReadinessScript `
            -PythonExe $pythonExe `
            -DatabaseUrl $BackendTestDb `
            -OutputPath $stage7SensitiveRefOutputPath `
            -RestoreEvidencePath $restoreSensitiveRefPath `
            -PublicSmokeEvidencePath $smokeSensitiveRefPath `
            -FinalAcceptanceEvidencePath $finalAcceptanceSensitiveRefPath `
            -SkipMigrations | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-stage7-readiness-gate fallo al validar refs sensibles de release.'
        if ($stage7SensitiveRefOutput.Trim()) {
            Write-Host $stage7SensitiveRefOutput
        }

        $stage7SensitiveRefReadiness = Get-Content -LiteralPath $stage7SensitiveRefOutputPath -Raw | ConvertFrom-Json
        $stage7SensitiveRefIssueCodes = @($stage7SensitiveRefReadiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage7SensitiveRefIssueCodes -contains 'stage7.restore_authorization_ref_sensitive') 'Restore con authorization_ref sensible debe tener codigo especifico.'
        Assert-Condition ($stage7SensitiveRefIssueCodes -contains 'stage7.public_smoke_environment_ref_sensitive') 'Smoke con environment_ref sensible debe tener codigo especifico.'
        Assert-Condition ($stage7SensitiveRefIssueCodes -contains 'stage7.final_acceptance_ref_sensitive') 'Aceptacion final con acceptance_ref sensible debe tener codigo especifico.'
        Assert-Condition ($stage7SensitiveRefReadiness.restore_evidence.authorization_ref_sensitive -eq $true) 'Restore debe marcar authorization_ref_sensitive=true.'
        Assert-Condition ($stage7SensitiveRefReadiness.public_smoke_evidence.environment_ref_sensitive -eq $true) 'Smoke debe marcar environment_ref_sensitive=true.'
        Assert-Condition ($stage7SensitiveRefReadiness.final_acceptance_evidence.acceptance_ref_sensitive -eq $true) 'Aceptacion final debe marcar acceptance_ref_sensitive=true.'

        $restoreRawBackupFilePath = Join-Path $stage7AcceptanceDir 'restore_raw_backup_file.json'
        $stage7RawBackupFileOutputPath = Join-Path $stage7AcceptanceDir 'stage7_raw_restore_backup_file.json'
        $restoreBackupEvidenceRefPath = Join-Path $stage7AcceptanceDir 'restore_backup_evidence_ref.json'
        $stage7BackupEvidenceRefOutputPath = Join-Path $stage7AcceptanceDir 'stage7_restore_backup_evidence_ref.json'

        [ordered]@{
            restore_verified = $true
            source_kind = 'backup_autorizado'
            authorization_ref = 'restore-authorization-v1'
            backup_file = 'D:\private\backups\lease-manager-prod.dump'
        } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $restoreRawBackupFilePath -Encoding UTF8

        $stage7RawBackupFileOutput = & $stage7ReadinessScript `
            -PythonExe $pythonExe `
            -DatabaseUrl $BackendTestDb `
            -OutputPath $stage7RawBackupFileOutputPath `
            -RestoreEvidencePath $restoreRawBackupFilePath `
            -PublicSmokeEvidencePath $smokeAuthorizedPath `
            -FinalAcceptanceEvidencePath $finalAcceptanceAuthorizedPath `
            -SkipMigrations | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-stage7-readiness-gate fallo al validar restore con backup_file crudo.'
        if ($stage7RawBackupFileOutput.Trim()) {
            Write-Host $stage7RawBackupFileOutput
        }

        $stage7RawBackupFileReadiness = Get-Content -LiteralPath $stage7RawBackupFileOutputPath -Raw | ConvertFrom-Json
        $stage7RawBackupFileIssueCodes = @($stage7RawBackupFileReadiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage7RawBackupFileIssueCodes -contains 'stage7.restore_backup_file_not_allowed') 'Restore con backup_file crudo debe tener codigo especifico.'
        Assert-Condition ($stage7RawBackupFileReadiness.restore_evidence.has_backup_file -eq $true) 'Restore con backup_file crudo debe marcar has_backup_file=true.'
        Assert-Condition ($stage7RawBackupFileReadiness.restore_evidence.has_backup_ref -eq $false) 'Restore con solo backup_file no debe marcar has_backup_ref=true.'
        Assert-Condition ($stage7RawBackupFileReadiness.checks.restore_authorized_evidence -eq $false) 'Restore con backup_file crudo no debe quedar autorizado para cierre.'

        [ordered]@{
            restore_verified = $true
            source_kind = 'backup_autorizado'
            authorization_ref = 'restore-authorization-v1'
            backup_evidence_ref = 'restore-backup-evidence-v1'
        } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $restoreBackupEvidenceRefPath -Encoding UTF8

        $stage7BackupEvidenceRefOutput = & $stage7ReadinessScript `
            -PythonExe $pythonExe `
            -DatabaseUrl $BackendTestDb `
            -OutputPath $stage7BackupEvidenceRefOutputPath `
            -RestoreEvidencePath $restoreBackupEvidenceRefPath `
            -PublicSmokeEvidencePath $smokeAuthorizedPath `
            -FinalAcceptanceEvidencePath $finalAcceptanceAuthorizedPath `
            -SkipMigrations | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-stage7-readiness-gate fallo al validar restore con backup_evidence_ref.'
        if ($stage7BackupEvidenceRefOutput.Trim()) {
            Write-Host $stage7BackupEvidenceRefOutput
        }

        $stage7BackupEvidenceRefReadiness = Get-Content -LiteralPath $stage7BackupEvidenceRefOutputPath -Raw | ConvertFrom-Json
        $stage7BackupEvidenceRefIssueCodes = @($stage7BackupEvidenceRefReadiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage7BackupEvidenceRefIssueCodes -notcontains 'stage7.restore_backup_ref_missing') 'Restore con backup_evidence_ref no debe reportar backup_ref faltante.'
        Assert-Condition ($stage7BackupEvidenceRefIssueCodes -notcontains 'stage7.restore_backup_file_not_allowed') 'Restore con backup_evidence_ref no debe reportar backup_file crudo.'
        Assert-Condition ($stage7BackupEvidenceRefReadiness.restore_evidence.has_backup_file -eq $false) 'Restore con backup_evidence_ref no debe marcar has_backup_file=true.'
        Assert-Condition ($stage7BackupEvidenceRefReadiness.restore_evidence.has_backup_ref -eq $true) 'Restore con backup_evidence_ref debe marcar has_backup_ref=true.'
        Assert-Condition ($stage7BackupEvidenceRefReadiness.checks.restore_authorized_evidence -eq $true) 'Restore con backup_evidence_ref debe quedar autorizado dentro del subgate de restore.'

        $smokeUnredactedOutputPath = Join-Path $stage7AcceptanceDir 'smoke_unredacted_operational_output.json'
        $stage7UnredactedSmokeOutputPath = Join-Path $stage7AcceptanceDir 'stage7_unredacted_smoke_output.json'

        [ordered]@{
            source_kind = 'public_smoke_autorizado'
            authorization_ref = 'smoke-authorization-v1'
            environment_ref = 'staging-env-v1'
            target_ref = 'deployment-target-v1'
            results = @(
                [ordered]@{
                    label = 'admin'
                    ok = $true
                    authFlow = 'ui-login'
                    username = 'demo-admin'
                    excerpt = 'Dashboard body must not be persisted as release evidence.'
                },
                [ordered]@{
                    label = 'operator'
                    ok = $true
                    authFlow = 'ui-login'
                    screenshotPath = 'D:\private\screenshots\smoke-operator.png'
                },
                [ordered]@{
                    label = 'reviewer'
                    ok = $true
                    authFlow = 'ui-login'
                    error = 'Raw browser error with https://example.test/?token=dummy'
                },
                [ordered]@{ label = 'partner'; ok = $true; authFlow = 'ui-login' }
            )
        } | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $smokeUnredactedOutputPath -Encoding UTF8

        $stage7UnredactedSmokeOutput = & $stage7ReadinessScript `
            -PythonExe $pythonExe `
            -DatabaseUrl $BackendTestDb `
            -OutputPath $stage7UnredactedSmokeOutputPath `
            -RestoreEvidencePath $restoreMissingAuthorizationPath `
            -PublicSmokeEvidencePath $smokeUnredactedOutputPath `
            -FinalAcceptanceEvidencePath $finalAcceptanceAuthorizedPath `
            -SkipMigrations | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) 'run-stage7-readiness-gate fallo al validar smoke no redactado.'
        if ($stage7UnredactedSmokeOutput.Trim()) {
            Write-Host $stage7UnredactedSmokeOutput
        }

        $stage7UnredactedSmokeReadiness = Get-Content -LiteralPath $stage7UnredactedSmokeOutputPath -Raw | ConvertFrom-Json
        $stage7UnredactedSmokeIssueCodes = @($stage7UnredactedSmokeReadiness.issues | ForEach-Object { $_.code })
        Assert-Condition ($stage7UnredactedSmokeIssueCodes -contains 'stage7.public_smoke_output_not_redacted') 'Smoke con username/excerpt/screenshotPath/error crudos debe tener codigo especifico.'
        Assert-Condition ($stage7UnredactedSmokeReadiness.public_smoke_evidence.output_redacted -eq $false) 'Smoke no redactado debe marcar output_redacted=false.'
        Assert-Condition ($stage7UnredactedSmokeReadiness.public_smoke_evidence.has_raw_username -eq $true) 'Smoke no redactado debe marcar has_raw_username=true.'
        Assert-Condition ($stage7UnredactedSmokeReadiness.public_smoke_evidence.has_raw_excerpt -eq $true) 'Smoke no redactado debe marcar has_raw_excerpt=true.'
        Assert-Condition ($stage7UnredactedSmokeReadiness.public_smoke_evidence.has_raw_screenshot_path -eq $true) 'Smoke no redactado debe marcar has_raw_screenshot_path=true.'
        Assert-Condition ($stage7UnredactedSmokeReadiness.public_smoke_evidence.has_raw_error -eq $true) 'Smoke no redactado debe marcar has_raw_error=true.'
        Assert-Condition ($stage7UnredactedSmokeReadiness.checks.public_smoke_authorized_evidence -eq $false) 'Smoke no redactado no debe quedar autorizado para cierre.'

        Step "Readiness wrappers output guards"
        Assert-ReadinessOutputGuard $stage1LocalReadinessScript 'Stage 1 local readiness' 'stage1-local-readiness-should-not-be-versioned.json'
        Assert-ReadinessOutputGuard $stage1SnapshotGateScript 'Stage 1 snapshot gate' 'stage1-snapshot-gate-should-not-be-versioned.json' @{
            SourceKind = 'snapshot_controlado'
            SourceLabel = 'stage1-output-guard'
            AuthorizationRef = 'stage1-authz-output-guard'
            ResponsibleRef = 'stage1-owner-output-guard'
            DatabaseUrl = 'sqlite:///local-evidence/stage1/output_guard.sqlite3'
        }
        Assert-ReadinessOutputGuard $stage2ReadinessScript 'Stage 2 readiness gate' 'stage2-readiness-should-not-be-versioned.json'
        Assert-ReadinessOutputGuard $stage3ReadinessScript 'Stage 3 readiness gate' 'stage3-readiness-should-not-be-versioned.json'
        Assert-ReadinessOutputGuard $stage4ReadinessScript 'Stage 4 readiness gate' 'stage4-readiness-should-not-be-versioned.json'
        Assert-ReadinessOutputGuard $stage5ReadinessScript 'Stage 5 readiness gate' 'stage5-readiness-should-not-be-versioned.json'
        Assert-ReadinessOutputGuard $stage5DocumentsReadinessScript 'Stage 5 documents readiness gate' 'stage5-documents-readiness-should-not-be-versioned.json'
        Assert-ReadinessOutputGuard $stage6ReadinessScript 'Stage 6 readiness gate' 'stage6-readiness-should-not-be-versioned.json'
        Assert-ReadinessOutputGuard $stage7ReadinessScript 'Stage 7 readiness gate' 'stage7-readiness-should-not-be-versioned.json' @{
            DatabaseUrl = $BackendTestDb
            SkipMigrations = $true
        }
        Assert-ReadinessOutputGuard $complianceDataReadinessScript 'Compliance data readiness gate' 'compliance-data-readiness-should-not-be-versioned.json'

        Step "Restore rehearsal output guard"
        Assert-Condition (Test-Path $restoreRehearsalScript) "No existe el rehearsal de restore en $restoreRehearsalScript"
        $blockedRestoreOutputPath = Join-Path $repoRoot 'docs\restore-rehearsal-should-not-be-versioned.json'
        $restoreOutputGuardFailed = $false
        try {
            $blockedRestoreOutput = & $restoreRehearsalScript -PlanOnly -OutputPath $blockedRestoreOutputPath 2>&1 | Out-String
        }
        catch {
            $blockedRestoreOutput = $_ | Out-String
            $restoreOutputGuardFailed = $true
        }
        Assert-Condition $restoreOutputGuardFailed 'run-postgres-restore-rehearsal debe rechazar OutputPath versionable antes de generar evidencia.'
        Assert-Condition ($blockedRestoreOutput -match 'local-evidence') 'El rechazo de OutputPath debe indicar local-evidence como ubicacion permitida.'
        Assert-Condition (-not (Test-Path $blockedRestoreOutputPath)) 'El rehearsal de restore no debe crear evidencia versionable bajo docs/.'

        Step "External sibling output path boundary guard"
        $siblingEvidenceDir = Join-Path (Split-Path -Parent $repoRoot) 'LeaseManager-output-boundary-acceptance'
        $siblingOutputPath = Join-Path $siblingEvidenceDir ("restore-plan-boundary_{0}.json" -f ([guid]::NewGuid().ToString('N')))
        $siblingOutput = & $restoreRehearsalScript -PlanOnly -OutputPath $siblingOutputPath 2>&1 | Out-String
        Assert-Condition ($LASTEXITCODE -eq 0) "run-postgres-restore-rehearsal debe aceptar OutputPath externo hermano. Output: $siblingOutput"
        Assert-Condition (Test-Path $siblingOutputPath) 'El rehearsal de restore debe escribir evidencia plan-only en ruta externa hermana permitida.'
        $siblingEvidence = Get-Content -LiteralPath $siblingOutputPath -Raw | ConvertFrom-Json
        Assert-Condition ($siblingEvidence.checks.output_under_local_evidence -eq $false) 'La evidencia externa hermana no debe clasificarse como local-evidence.'
        $resolvedSiblingDir = [System.IO.Path]::GetFullPath($siblingEvidenceDir)
        $resolvedSiblingOutput = [System.IO.Path]::GetFullPath($siblingOutputPath)
        Assert-Condition ($resolvedSiblingOutput.StartsWith("$resolvedSiblingDir$([System.IO.Path]::DirectorySeparatorChar)", [System.StringComparison]::OrdinalIgnoreCase)) 'Cleanup externo abortado por ruta inesperada.'
        Remove-Item -LiteralPath $resolvedSiblingOutput -Force
        if (-not (Get-ChildItem -LiteralPath $resolvedSiblingDir -Force)) {
            Remove-Item -LiteralPath $resolvedSiblingDir -Force
        }
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
    $smokeArgs = @(
        $smokeScript,
        '--allow-external',
        '--frontend-url',
        $FrontendUrl,
        '--api-base-url',
        $ApiBaseUrl
    )
    $hasPublicSmokeEvidenceMetadata = $PublicSmokeSourceKind.Trim() `
        -or $PublicSmokeAuthorizationRef.Trim() `
        -or $PublicSmokeEnvironmentRef.Trim() `
        -or $PublicSmokeTargetRef.Trim() `
        -or $PublicSmokeResponsibleRef.Trim()
    if ($hasPublicSmokeEvidenceMetadata) {
        if ($PublicSmokeSourceKind.Trim()) {
            $smokeArgs += @('--evidence-source-kind', $PublicSmokeSourceKind)
        }
        else {
            $smokeArgs += @('--evidence-source-kind', 'public_smoke_autorizado')
        }
        if ($PublicSmokeAuthorizationRef.Trim()) {
            $smokeArgs += @('--authorization-ref', $PublicSmokeAuthorizationRef)
        }
        if ($PublicSmokeEnvironmentRef.Trim()) {
            $smokeArgs += @('--environment-ref', $PublicSmokeEnvironmentRef)
        }
        if ($PublicSmokeTargetRef.Trim()) {
            $smokeArgs += @('--target-ref', $PublicSmokeTargetRef)
        }
        if ($PublicSmokeResponsibleRef.Trim()) {
            $smokeArgs += @('--responsible-ref', $PublicSmokeResponsibleRef)
        }
    }
    $smokeOutput = & node @smokeArgs | Out-String
    $smokeExitCode = $LASTEXITCODE
    if ($smokeOutput.Trim()) {
        Write-Host $smokeOutput
    }
    Assert-Condition ($smokeOutput -notmatch '"username"\s*:') 'La smoke publica no debe emitir username en JSON.'
    Assert-Condition ($smokeOutput -notmatch '"excerpt"\s*:') 'La smoke publica no debe emitir excerpt de pantalla en JSON.'
    Assert-Condition ($smokeOutput -notmatch '"screenshotPath"\s*:') 'La smoke publica no debe emitir rutas de screenshot en JSON.'
    Assert-Condition ($smokeOutput -notmatch '"error"\s*:') 'La smoke publica no debe emitir errores crudos en JSON.'

    $smokePayload = $smokeOutput | ConvertFrom-Json
    if ($smokePayload.PSObject.Properties.Name -contains 'results') {
        $smokeResults = @($smokePayload.results)
    }
    else {
        $smokeResults = @($smokePayload)
    }
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
    Assert-Condition ($adminResult.screenshotCaptured -eq $true) 'La smoke admin no confirmo screenshot capturado.'
    Assert-Condition ($operatorResult.screenshotCaptured -eq $true) 'La smoke operator no confirmo screenshot capturado.'
    Assert-Condition ($reviewerResult.screenshotCaptured -eq $true) 'La smoke reviewer no confirmo screenshot capturado.'
    Assert-Condition ($partnerResult.screenshotCaptured -eq $true) 'La smoke partner no confirmo screenshot capturado.'

    Step "Smoke summary"
    Write-Host ($smokeResults | ConvertTo-Json -Depth 6)
} else {
    Step "Public smoke skipped"
    Write-Host "Smoke publico omitido. Ejecutar con -RunPublicSmoke o -OnlySmoke y URLs explicitas solo con ambiente autorizado." -ForegroundColor Yellow
}

Step "Acceptance complete"
Write-Host "Workflow acceptance suite OK." -ForegroundColor Green

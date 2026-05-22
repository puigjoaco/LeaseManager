param(
    [string]$PythonExe = '',
    [string]$DatabaseUrl = '',
    [string]$OutputPath = '',
    [string]$RestoreEvidencePath = '',
    [string]$PublicSmokeEvidencePath = '',
    [string]$FinalAcceptanceRef = '',
    [string]$FinalAcceptanceEvidencePath = '',
    [string]$ReportingSourceKind = 'local',
    [string]$ReportingSourceLabel = 'stage7-reporting-local-readiness',
    [string]$ReportingAuthorizationRef = '',
    [string]$ReportingStage5EvidenceRef = '',
    [string]$ReportingStage6EvidenceRef = '',
    [string]$ReportingApiProofRef = '',
    [string]$ReportingBackofficeVisualRef = '',
    [string]$ReportingResponsibleRef = '',
    [switch]$SkipMigrations,
    [switch]$RequireClosure
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Step([string]$message) {
    Write-Host ''
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Assert-Condition($condition, [string]$message) {
    if (-not $condition) {
        throw $message
    }
}

function Resolve-FullPath([string]$path) {
    if ([System.IO.Path]::IsPathRooted($path)) {
        return [System.IO.Path]::GetFullPath($path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $path))
}

function Resolve-SqliteDatabaseUrl([string]$databaseUrl) {
    if ($databaseUrl -notmatch '^sqlite:///(.+)$') {
        return $databaseUrl
    }
    $sqlitePath = $Matches[1]
    if ($sqlitePath -eq ':memory:') {
        return $databaseUrl
    }
    $sqlitePath = $sqlitePath -replace '/', '\'
    $resolvedSqlitePath = Resolve-FullPath $sqlitePath
    $sqliteDirectory = Split-Path -Parent $resolvedSqlitePath
    if (-not [string]::IsNullOrWhiteSpace($sqliteDirectory)) {
        New-Item -ItemType Directory -Force -Path $sqliteDirectory | Out-Null
    }
    return 'sqlite:///' + ($resolvedSqlitePath -replace '\\', '/')
}

function Assert-OutputPathSafe([string]$path, [string]$repoRoot) {
    $resolvedOutput = Resolve-FullPath $path
    $localEvidenceRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot 'local-evidence'))
    $repoRootFull = [System.IO.Path]::GetFullPath($repoRoot)

    if ($resolvedOutput.StartsWith($repoRootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        Assert-Condition `
            ($resolvedOutput.StartsWith($localEvidenceRoot, [System.StringComparison]::OrdinalIgnoreCase)) `
            'Si el output queda dentro del repo, debe estar bajo local-evidence/ para no versionar evidencia de readiness.'
    }

    return $resolvedOutput
}

function Test-NonSensitiveReference([string]$value) {
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $false
    }
    return $value -notmatch '(?i)(:\/\/|@|password|passwd|pwd|secret|token|bearer|api[_-]?key|credential|credencial)'
}

function Get-PayloadTextProperty($payload, [string[]]$names) {
    foreach ($name in $names) {
        if ($payload.PSObject.Properties.Name -contains $name) {
            $value = $payload.$name
            if ($null -ne $value -and -not [string]::IsNullOrWhiteSpace([string]$value)) {
                return [string]$value
            }
        }
    }
    return ''
}

function Get-PayloadBoolProperty($payload, [string[]]$names) {
    foreach ($name in $names) {
        if ($payload.PSObject.Properties.Name -contains $name) {
            $value = $payload.$name
            if ($value -eq $true) {
                return $true
            }
            if ($null -ne $value -and [string]$value -match '^(?i:true)$') {
                return $true
            }
        }
    }
    return $false
}

function Test-AuthorizedRestoreEvidence($payload) {
    $sourceKind = Get-PayloadTextProperty $payload @('source_kind', 'restore_source_kind', 'source')
    $rehearsalKind = Get-PayloadTextProperty $payload @('rehearsal_kind')
    $mode = Get-PayloadTextProperty $payload @('mode')
    $authorizationRef = Get-PayloadTextProperty $payload @('authorization_ref')
    $backupRef = Get-PayloadTextProperty $payload @('backup_ref', 'backup_evidence_ref', 'backup_file')
    $allowedSourceKinds = @('snapshot_controlado', 'real_autorizado', 'backup_autorizado', 'restore_autorizado')
    $verified = ($payload.PSObject.Properties.Name -contains 'restore_verified') -and $payload.restore_verified -eq $true
    $syntheticOnly = $sourceKind -eq 'synthetic_fixture' -or $rehearsalKind -eq 'postgres_local_synthetic_restore' -or $mode -eq 'plan_only'
    $hasAuthorizationRef = Test-NonSensitiveReference $authorizationRef
    $hasBackupRef = Test-NonSensitiveReference $backupRef
    $authorized = $verified `
        -and (-not $syntheticOnly) `
        -and ($allowedSourceKinds -contains $sourceKind) `
        -and $hasAuthorizationRef `
        -and $hasBackupRef

    $reason = ''
    if (-not $verified) {
        $reason = 'restore_not_verified'
    }
    elseif ($syntheticOnly) {
        $reason = 'synthetic_restore_not_authorized'
    }
    elseif (-not ($allowedSourceKinds -contains $sourceKind)) {
        $reason = 'restore_source_kind_invalid'
    }
    elseif (-not $hasAuthorizationRef) {
        $reason = 'restore_authorization_ref_missing'
    }
    elseif (-not $hasBackupRef) {
        $reason = 'restore_backup_ref_missing'
    }

    return [ordered]@{
        verified = $verified
        authorized = $authorized
        source_kind = $sourceKind
        synthetic_only = $syntheticOnly
        has_authorization_ref = $hasAuthorizationRef
        has_backup_ref = $hasBackupRef
        reason = $reason
    }
}

function Read-JsonFile([string]$path) {
    $resolvedPath = Resolve-FullPath $path
    Assert-Condition (Test-Path -LiteralPath $resolvedPath) "No existe evidencia JSON: $resolvedPath"
    return Get-Content -LiteralPath $resolvedPath -Raw | ConvertFrom-Json
}

function Test-SmokeEvidence($payload) {
    $items = @($payload)
    $hasResults = $payload.PSObject.Properties.Name -contains 'results'
    if ($items.Count -eq 1 -and $hasResults -and $null -ne $payload.results) {
        $items = @($payload.results)
    }
    $requiredLabels = @('admin', 'operator', 'reviewer', 'partner')
    foreach ($label in $requiredLabels) {
        $item = $items | Where-Object { $_.label -eq $label } | Select-Object -First 1
        if ($null -eq $item -or $item.ok -ne $true -or $item.authFlow -ne 'ui-login') {
            return $false
        }
    }
    return $true
}

function Test-AuthorizedSmokeEvidence($payload) {
    $sourceKind = Get-PayloadTextProperty $payload @('source_kind', 'smoke_source_kind', 'source')
    $mode = Get-PayloadTextProperty $payload @('mode')
    $authorizationRef = Get-PayloadTextProperty $payload @('authorization_ref')
    $environmentRef = Get-PayloadTextProperty $payload @('environment_ref', 'environment_evidence_ref', 'deployment_environment_ref')
    $targetRef = Get-PayloadTextProperty $payload @('target_ref', 'target_evidence_ref', 'deployment_ref', 'base_url_ref')
    $allowedSourceKinds = @('public_smoke_autorizado', 'ambiente_autorizado', 'staging_autorizado', 'real_autorizado')
    $syntheticSourceKinds = @('synthetic_fixture', 'local_fixture', 'mock')
    $syntheticModes = @('plan_only', 'local_only', 'mock', 'synthetic')
    $verified = Test-SmokeEvidence $payload
    $syntheticOnly = ($syntheticSourceKinds -contains $sourceKind) -or ($syntheticModes -contains $mode)
    $hasAuthorizationRef = Test-NonSensitiveReference $authorizationRef
    $hasEnvironmentRef = Test-NonSensitiveReference $environmentRef
    $hasTargetRef = Test-NonSensitiveReference $targetRef
    $authorized = $verified `
        -and (-not $syntheticOnly) `
        -and ($allowedSourceKinds -contains $sourceKind) `
        -and $hasAuthorizationRef `
        -and $hasEnvironmentRef `
        -and $hasTargetRef

    $reason = ''
    if (-not $verified) {
        $reason = 'public_smoke_invalid'
    }
    elseif ($syntheticOnly) {
        $reason = 'public_smoke_synthetic_not_authorized'
    }
    elseif (-not ($allowedSourceKinds -contains $sourceKind)) {
        $reason = 'public_smoke_source_kind_invalid'
    }
    elseif (-not $hasAuthorizationRef) {
        $reason = 'public_smoke_authorization_ref_missing'
    }
    elseif (-not $hasEnvironmentRef) {
        $reason = 'public_smoke_environment_ref_missing'
    }
    elseif (-not $hasTargetRef) {
        $reason = 'public_smoke_target_ref_missing'
    }

    return [ordered]@{
        verified = $verified
        authorized = $authorized
        source_kind = $sourceKind
        synthetic_only = $syntheticOnly
        has_authorization_ref = $hasAuthorizationRef
        has_environment_ref = $hasEnvironmentRef
        has_target_ref = $hasTargetRef
        reason = $reason
    }
}

function Test-AuthorizedFinalAcceptanceEvidence($payload, [string]$fallbackAcceptanceRef) {
    $sourceKind = Get-PayloadTextProperty $payload @('source_kind', 'final_acceptance_source_kind', 'source')
    $mode = Get-PayloadTextProperty $payload @('mode')
    $authorizationRef = Get-PayloadTextProperty $payload @('authorization_ref')
    $responsibleRef = Get-PayloadTextProperty $payload @('responsible_ref', 'accepted_by_ref')
    $scopeRef = Get-PayloadTextProperty $payload @('scope_ref', 'acceptance_scope_ref', 'release_candidate_ref', 'candidate_ref')
    $acceptanceRef = Get-PayloadTextProperty $payload @('acceptance_ref', 'decision_ref', 'signoff_ref')
    if ([string]::IsNullOrWhiteSpace($acceptanceRef)) {
        $acceptanceRef = $fallbackAcceptanceRef
    }
    $allowedSourceKinds = @('aceptacion_final_autorizada', 'final_acceptance_autorizada', 'cutover_autorizado', 'ambiente_autorizado', 'real_autorizado')
    $syntheticSourceKinds = @('synthetic_fixture', 'local_fixture', 'mock')
    $syntheticModes = @('plan_only', 'local_only', 'mock', 'synthetic')
    $accepted = Get-PayloadBoolProperty $payload @('accepted', 'final_accepted', 'acceptance_approved')
    $syntheticOnly = ($syntheticSourceKinds -contains $sourceKind) -or ($syntheticModes -contains $mode)
    $hasAuthorizationRef = Test-NonSensitiveReference $authorizationRef
    $hasResponsibleRef = Test-NonSensitiveReference $responsibleRef
    $hasScopeRef = Test-NonSensitiveReference $scopeRef
    $hasAcceptanceRef = Test-NonSensitiveReference $acceptanceRef
    $authorized = $accepted `
        -and (-not $syntheticOnly) `
        -and ($allowedSourceKinds -contains $sourceKind) `
        -and $hasAuthorizationRef `
        -and $hasResponsibleRef `
        -and $hasScopeRef `
        -and $hasAcceptanceRef

    $reason = ''
    if (-not $accepted) {
        $reason = 'final_acceptance_not_accepted'
    }
    elseif ($syntheticOnly) {
        $reason = 'final_acceptance_synthetic_not_authorized'
    }
    elseif (-not ($allowedSourceKinds -contains $sourceKind)) {
        $reason = 'final_acceptance_source_kind_invalid'
    }
    elseif (-not $hasAuthorizationRef) {
        $reason = 'final_acceptance_authorization_ref_missing'
    }
    elseif (-not $hasResponsibleRef) {
        $reason = 'final_acceptance_responsible_ref_missing'
    }
    elseif (-not $hasScopeRef) {
        $reason = 'final_acceptance_scope_ref_missing'
    }
    elseif (-not $hasAcceptanceRef) {
        $reason = 'final_acceptance_ref_missing'
    }

    return [ordered]@{
        accepted = $accepted
        authorized = $authorized
        source_kind = $sourceKind
        synthetic_only = $syntheticOnly
        has_authorization_ref = $hasAuthorizationRef
        has_responsible_ref = $hasResponsibleRef
        has_scope_ref = $hasScopeRef
        has_acceptance_ref = $hasAcceptanceRef
        reason = $reason
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$authorizedReportingSourceKinds = @('snapshot_controlado', 'real_autorizado')

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonExe = Join-Path $backendDir '.venv\Scripts\python.exe'
}
$PythonExe = Resolve-FullPath $PythonExe
Assert-Condition (Test-Path -LiteralPath $PythonExe) "No existe PythonExe: $PythonExe"

if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
    $resolvedDbPath = (Join-Path $repoRoot "local-evidence\stage7\readiness\stage7_readiness_$timestamp.sqlite3") -replace '\\', '/'
    $DatabaseUrl = "sqlite:///$resolvedDbPath"
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot "local-evidence\stage7\readiness\stage7_readiness_$timestamp.json"
}
$resolvedOutput = Assert-OutputPathSafe $OutputPath $repoRoot
$evidenceDir = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
$DatabaseUrl = Resolve-SqliteDatabaseUrl $DatabaseUrl
$observabilityOutput = Join-Path $evidenceDir "stage7_observability_$timestamp.json"
$reportingOutput = Join-Path $evidenceDir "stage7_reporting_$timestamp.json"
$reportingSourceKindAuthorizedByParam = $authorizedReportingSourceKinds -contains $ReportingSourceKind

Assert-Condition (Test-NonSensitiveReference $ReportingSourceLabel) 'ReportingSourceLabel debe ser una etiqueta no sensible.'
if ($reportingSourceKindAuthorizedByParam) {
    Assert-Condition (Test-NonSensitiveReference $ReportingAuthorizationRef) 'ReportingAuthorizationRef es obligatorio para fuente evidencial Reporting y debe ser no sensible.'
    Assert-Condition (Test-NonSensitiveReference $ReportingStage5EvidenceRef) 'ReportingStage5EvidenceRef es obligatorio para cierre Reporting y debe ser no sensible.'
    Assert-Condition (Test-NonSensitiveReference $ReportingStage6EvidenceRef) 'ReportingStage6EvidenceRef es obligatorio para cierre Reporting y debe ser no sensible.'
    Assert-Condition (Test-NonSensitiveReference $ReportingApiProofRef) 'ReportingApiProofRef es obligatorio para cierre Reporting y debe ser no sensible.'
    Assert-Condition (Test-NonSensitiveReference $ReportingBackofficeVisualRef) 'ReportingBackofficeVisualRef es obligatorio para cierre Reporting y debe ser no sensible.'
    Assert-Condition (Test-NonSensitiveReference $ReportingResponsibleRef) 'ReportingResponsibleRef es obligatorio para cierre Reporting y debe ser no sensible.'
}

$checks = [ordered]@{
    backend_check = $false
    migrations_applied = $false
    observability_audit = $false
    reporting_readiness = $false
    reporting_source_authorized_for_close = $false
    restore_evidence = $false
    restore_authorized_evidence = $false
    public_smoke_evidence = $false
    public_smoke_authorized_evidence = $false
    final_acceptance_ref = $false
    final_acceptance_evidence = $false
    final_acceptance_authorized_evidence = $false
}
$issues = @()
$restoreEvidenceSummary = [ordered]@{
    provided = $false
    verified = $false
    authorized = $false
    source_kind = ''
    synthetic_only = $false
    has_authorization_ref = $false
    has_backup_ref = $false
}
$publicSmokeEvidenceSummary = [ordered]@{
    provided = $false
    verified = $false
    authorized = $false
    source_kind = ''
    synthetic_only = $false
    has_authorization_ref = $false
    has_environment_ref = $false
    has_target_ref = $false
}
$finalAcceptanceEvidenceSummary = [ordered]@{
    provided = $false
    accepted = $false
    authorized = $false
    source_kind = ''
    synthetic_only = $false
    has_authorization_ref = $false
    has_responsible_ref = $false
    has_scope_ref = $false
    has_acceptance_ref = $false
}

Step 'Backend local checks'
$env:DATABASE_URL = $DatabaseUrl
$env:REDIS_URL = ''
$env:CELERY_RESULT_BACKEND = ''
$env:DJANGO_CACHE_URL = 'locmem://stage7-readiness-gate'

Push-Location $backendDir
try {
    & $PythonExe manage.py check
    Assert-Condition ($LASTEXITCODE -eq 0) 'manage.py check fallo.'
    $checks.backend_check = $true

    if (-not $SkipMigrations) {
        & $PythonExe manage.py migrate --noinput
        Assert-Condition ($LASTEXITCODE -eq 0) 'migrate para readiness Etapa 7 fallo.'
        $checks.migrations_applied = $true
    }
    else {
        $checks.migrations_applied = 'skipped'
    }

    & $PythonExe manage.py audit_operational_observability --output $observabilityOutput
    Assert-Condition ($LASTEXITCODE -eq 0) 'audit_operational_observability fallo.'
    $checks.observability_audit = $true

    $reportingArgs = @(
        'manage.py',
        'audit_stage7_reporting_readiness',
        '--source-kind',
        $ReportingSourceKind,
        '--source-label',
        $ReportingSourceLabel.Trim(),
        '--output',
        $reportingOutput
    )
    if (-not [string]::IsNullOrWhiteSpace($ReportingAuthorizationRef)) {
        $reportingArgs += @('--authorization-ref', $ReportingAuthorizationRef.Trim())
    }
    if (-not [string]::IsNullOrWhiteSpace($ReportingStage5EvidenceRef)) {
        $reportingArgs += @('--stage5-evidence-ref', $ReportingStage5EvidenceRef)
    }
    if (-not [string]::IsNullOrWhiteSpace($ReportingStage6EvidenceRef)) {
        $reportingArgs += @('--stage6-evidence-ref', $ReportingStage6EvidenceRef)
    }
    if (-not [string]::IsNullOrWhiteSpace($ReportingApiProofRef)) {
        $reportingArgs += @('--reporting-api-proof-ref', $ReportingApiProofRef)
    }
    if (-not [string]::IsNullOrWhiteSpace($ReportingBackofficeVisualRef)) {
        $reportingArgs += @('--backoffice-visual-ref', $ReportingBackofficeVisualRef)
    }
    if (-not [string]::IsNullOrWhiteSpace($ReportingResponsibleRef)) {
        $reportingArgs += @('--responsible-ref', $ReportingResponsibleRef)
    }
    & $PythonExe @reportingArgs
    Assert-Condition ($LASTEXITCODE -eq 0) 'audit_stage7_reporting_readiness fallo.'
    $checks.reporting_readiness = $true
}
finally {
    Pop-Location
}

$observability = Read-JsonFile $observabilityOutput
$reporting = Read-JsonFile $reportingOutput
$observabilityRuntimeAuthorized = $false
if (
    ($observability.PSObject.Properties.Name -contains 'sections') `
    -and ($null -ne $observability.sections) `
    -and ($observability.sections.PSObject.Properties.Name -contains 'runtime_signals') `
    -and ($null -ne $observability.sections.runtime_signals) `
    -and ($observability.sections.runtime_signals.PSObject.Properties.Name -contains 'authorized_for_stage7_close')
) {
    $observabilityRuntimeAuthorized = $observability.sections.runtime_signals.authorized_for_stage7_close -eq $true
}
if (
    ($observability.PSObject.Properties.Name -contains 'sections') `
    -and ($null -ne $observability.sections) `
    -and ($observability.sections.PSObject.Properties.Name -contains 'runtime_signals') `
    -and ($null -ne $observability.sections.runtime_signals)
) {
    foreach ($signalKey in @('monthly_calculation_latency', 'queue_runtime', 'failed_webhooks', 'failed_crons')) {
        Assert-Condition ($observability.sections.runtime_signals.PSObject.Properties.Name -contains $signalKey) "La auditoria de observabilidad debe exponer $signalKey."
        $runtimeSignal = $observability.sections.runtime_signals.$signalKey
        Assert-Condition ($runtimeSignal.PSObject.Properties.Name -contains 'source_trace') "La senal runtime $signalKey debe exponer source_trace."
    }
}
if ($observability.ready_for_stage7_observability -ne $true) {
    $issues += [ordered]@{
        code = 'stage7.observability_not_ready'
        severity = 'attention'
        message = 'La auditoria de observabilidad aun no esta lista para cierre con senales runtime autorizadas.'
    }
}

$reportingSourceAuthorized = $false
if ($reporting.PSObject.Properties.Name -contains 'source_kind_authorized_for_close') {
    $reportingSourceAuthorized = $reporting.source_kind_authorized_for_close -eq $true
}
$checks.reporting_source_authorized_for_close = $reportingSourceAuthorized
Assert-Condition (
    ($reporting.PSObject.Properties.Name -contains 'sections') `
    -and ($null -ne $reporting.sections) `
    -and ($reporting.sections.PSObject.Properties.Name -contains 'source_trace') `
    -and ($null -ne $reporting.sections.source_trace)
) 'La auditoria Reporting debe exponer sections.source_trace.'
if ($reportingSourceKindAuthorizedByParam) {
    Assert-Condition ($reportingSourceAuthorized -eq $true) 'La fuente evidencial Reporting debe quedar autorizada por tipo.'
    Assert-Condition ($reporting.sections.source_trace.source_label -eq $true) 'La fuente evidencial Reporting debe tener source_label trazable.'
    Assert-Condition ($reporting.sections.source_trace.authorization_ref -eq $true) 'La fuente evidencial Reporting debe tener authorization_ref trazable.'
}
if ($reporting.ready_for_stage7_reporting -ne $true) {
    $issues += [ordered]@{
        code = 'stage7.reporting_not_ready'
        severity = 'blocking'
        message = 'La readiness de Reporting aun no esta lista con fuente autorizada y evidencia trazable.'
    }
}

if ([string]::IsNullOrWhiteSpace($RestoreEvidencePath)) {
    $issues += [ordered]@{
        code = 'stage7.restore_evidence_missing'
        severity = 'blocking'
        message = 'Falta evidencia JSON de restore verificado.'
    }
}
else {
    $restoreEvidence = Read-JsonFile $RestoreEvidencePath
    $restoreCheck = Test-AuthorizedRestoreEvidence $restoreEvidence
    $checks.restore_evidence = $restoreCheck.verified
    $checks.restore_authorized_evidence = $restoreCheck.authorized
    $restoreEvidenceSummary = [ordered]@{
        provided = $true
        verified = $restoreCheck.verified
        authorized = $restoreCheck.authorized
        source_kind = $restoreCheck.source_kind
        synthetic_only = $restoreCheck.synthetic_only
        has_authorization_ref = $restoreCheck.has_authorization_ref
        has_backup_ref = $restoreCheck.has_backup_ref
    }
    if (-not $restoreCheck.verified) {
        $issues += [ordered]@{
            code = 'stage7.restore_not_verified'
            severity = 'blocking'
            message = 'La evidencia de restore no reporta restore_verified=true.'
        }
    }
    elseif (-not $restoreCheck.authorized) {
        $issueCode = switch ($restoreCheck.reason) {
            'restore_authorization_ref_missing' { 'stage7.restore_authorization_ref_missing' }
            'restore_backup_ref_missing' { 'stage7.restore_backup_ref_missing' }
            default { 'stage7.restore_authorized_backup_missing' }
        }
        $issueMessage = switch ($restoreCheck.reason) {
            'synthetic_restore_not_authorized' { 'El restore sintetico prepara el gate, pero no reemplaza restore de backup/snapshot autorizado.' }
            'restore_authorization_ref_missing' { 'La evidencia de restore requiere authorization_ref no sensible.' }
            'restore_backup_ref_missing' { 'La evidencia de restore requiere backup_ref o backup_file no sensible.' }
            default { 'La evidencia de restore debe declarar source_kind snapshot_controlado, real_autorizado, backup_autorizado o restore_autorizado.' }
        }
        $issues += [ordered]@{
            code = $issueCode
            severity = 'blocking'
            message = $issueMessage
        }
    }
}

if ([string]::IsNullOrWhiteSpace($PublicSmokeEvidencePath)) {
    $issues += [ordered]@{
        code = 'stage7.public_smoke_missing'
        severity = 'blocking'
        message = 'Falta evidencia JSON del smoke publico autorizado.'
    }
}
else {
    $smokeEvidence = Read-JsonFile $PublicSmokeEvidencePath
    $smokeCheck = Test-AuthorizedSmokeEvidence $smokeEvidence
    $checks.public_smoke_evidence = $smokeCheck.verified
    $checks.public_smoke_authorized_evidence = $smokeCheck.authorized
    $publicSmokeEvidenceSummary = [ordered]@{
        provided = $true
        verified = $smokeCheck.verified
        authorized = $smokeCheck.authorized
        source_kind = $smokeCheck.source_kind
        synthetic_only = $smokeCheck.synthetic_only
        has_authorization_ref = $smokeCheck.has_authorization_ref
        has_environment_ref = $smokeCheck.has_environment_ref
        has_target_ref = $smokeCheck.has_target_ref
    }
    if (-not $smokeCheck.verified) {
        $issues += [ordered]@{
            code = 'stage7.public_smoke_invalid'
            severity = 'blocking'
            message = 'La evidencia de smoke no cubre los cuatro roles con login real.'
        }
    }
    elseif (-not $smokeCheck.authorized) {
        $issueCode = switch ($smokeCheck.reason) {
            'public_smoke_authorization_ref_missing' { 'stage7.public_smoke_authorization_ref_missing' }
            'public_smoke_environment_ref_missing' { 'stage7.public_smoke_environment_ref_missing' }
            'public_smoke_target_ref_missing' { 'stage7.public_smoke_target_ref_missing' }
            default { 'stage7.public_smoke_authorized_environment_missing' }
        }
        $issueMessage = switch ($smokeCheck.reason) {
            'public_smoke_synthetic_not_authorized' { 'El smoke local/sintetico prepara el gate, pero no reemplaza un smoke publico con ambiente autorizado.' }
            'public_smoke_authorization_ref_missing' { 'La evidencia de smoke publico requiere authorization_ref no sensible.' }
            'public_smoke_environment_ref_missing' { 'La evidencia de smoke publico requiere environment_ref no sensible.' }
            'public_smoke_target_ref_missing' { 'La evidencia de smoke publico requiere target_ref o deployment_ref no sensible.' }
            default { 'La evidencia de smoke publico debe declarar source_kind public_smoke_autorizado, ambiente_autorizado, staging_autorizado o real_autorizado.' }
        }
        $issues += [ordered]@{
            code = $issueCode
            severity = 'blocking'
            message = $issueMessage
        }
    }
}

$checks.final_acceptance_ref = Test-NonSensitiveReference $FinalAcceptanceRef
if ([string]::IsNullOrWhiteSpace($FinalAcceptanceEvidencePath)) {
    $issues += [ordered]@{
        code = if ($checks.final_acceptance_ref) { 'stage7.final_acceptance_evidence_missing' } else { 'stage7.final_acceptance_missing' }
        severity = 'blocking'
        message = if ($checks.final_acceptance_ref) { 'La referencia simple de aceptacion final no reemplaza evidencia JSON autorizada.' } else { 'Falta evidencia JSON de aceptacion final autorizada.' }
    }
}
else {
    $finalAcceptanceEvidence = Read-JsonFile $FinalAcceptanceEvidencePath
    $finalAcceptanceCheck = Test-AuthorizedFinalAcceptanceEvidence $finalAcceptanceEvidence $FinalAcceptanceRef
    $checks.final_acceptance_evidence = $finalAcceptanceCheck.accepted
    $checks.final_acceptance_authorized_evidence = $finalAcceptanceCheck.authorized
    $finalAcceptanceEvidenceSummary = [ordered]@{
        provided = $true
        accepted = $finalAcceptanceCheck.accepted
        authorized = $finalAcceptanceCheck.authorized
        source_kind = $finalAcceptanceCheck.source_kind
        synthetic_only = $finalAcceptanceCheck.synthetic_only
        has_authorization_ref = $finalAcceptanceCheck.has_authorization_ref
        has_responsible_ref = $finalAcceptanceCheck.has_responsible_ref
        has_scope_ref = $finalAcceptanceCheck.has_scope_ref
        has_acceptance_ref = $finalAcceptanceCheck.has_acceptance_ref
    }
    if (-not $finalAcceptanceCheck.accepted) {
        $issues += [ordered]@{
            code = 'stage7.final_acceptance_not_accepted'
            severity = 'blocking'
            message = 'La evidencia de aceptacion final no reporta accepted=true.'
        }
    }
    elseif (-not $finalAcceptanceCheck.authorized) {
        $issueCode = switch ($finalAcceptanceCheck.reason) {
            'final_acceptance_authorization_ref_missing' { 'stage7.final_acceptance_authorization_ref_missing' }
            'final_acceptance_responsible_ref_missing' { 'stage7.final_acceptance_responsible_ref_missing' }
            'final_acceptance_scope_ref_missing' { 'stage7.final_acceptance_scope_ref_missing' }
            'final_acceptance_ref_missing' { 'stage7.final_acceptance_ref_missing' }
            default { 'stage7.final_acceptance_authorized_evidence_missing' }
        }
        $issueMessage = switch ($finalAcceptanceCheck.reason) {
            'final_acceptance_synthetic_not_authorized' { 'La aceptacion local/sintetica prepara el gate, pero no reemplaza aceptacion final autorizada.' }
            'final_acceptance_authorization_ref_missing' { 'La evidencia de aceptacion final requiere authorization_ref no sensible.' }
            'final_acceptance_responsible_ref_missing' { 'La evidencia de aceptacion final requiere responsible_ref o accepted_by_ref no sensible.' }
            'final_acceptance_scope_ref_missing' { 'La evidencia de aceptacion final requiere scope_ref, acceptance_scope_ref o release_candidate_ref no sensible.' }
            'final_acceptance_ref_missing' { 'La evidencia de aceptacion final requiere acceptance_ref, decision_ref, signoff_ref o FinalAcceptanceRef no sensible.' }
            default { 'La evidencia de aceptacion final debe declarar source_kind aceptacion_final_autorizada, final_acceptance_autorizada, cutover_autorizado, ambiente_autorizado o real_autorizado.' }
        }
        $issues += [ordered]@{
            code = $issueCode
            severity = 'blocking'
            message = $issueMessage
        }
    }
}

$blockingIssueCount = @($issues | Where-Object { $_.severity -eq 'blocking' }).Count
$readyForClose = $blockingIssueCount -eq 0 `
    -and $observability.ready_for_stage7_observability -eq $true `
    -and $reporting.ready_for_stage7_reporting -eq $true
$result = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('o')
    source_kind = 'local'
    classification = if ($readyForClose) { 'resuelto_confirmado' } else { 'parcial' }
    ready_for_stage7_close = $readyForClose
    checks = $checks
    observability = [ordered]@{
        output = ($observabilityOutput.Replace('\', '/'))
        classification = $observability.classification
        ready_for_stage7_observability = $observability.ready_for_stage7_observability
        runtime_signals_authorized_for_close = $observabilityRuntimeAuthorized
        issue_counts = $observability.issue_counts
    }
    reporting = [ordered]@{
        output = ($reportingOutput.Replace('\', '/'))
        source_kind = $reporting.source_kind
        classification = $reporting.classification
        ready_for_stage7_reporting = $reporting.ready_for_stage7_reporting
        source_kind_authorized_for_close = $reportingSourceAuthorized
        source_trace = $reporting.sections.source_trace
        issue_counts = $reporting.issue_counts
    }
    restore_evidence = $restoreEvidenceSummary
    public_smoke_evidence = $publicSmokeEvidenceSummary
    final_acceptance_evidence = $finalAcceptanceEvidenceSummary
    issues = $issues
    limitations = @(
        'Gate local de solo lectura para consolidar readiness de Etapa 7.',
        'No ejecuta smoke publico ni conecta proveedores externos.',
        'No usa secretos, .env, datos reales ni backups productivos.',
        'No cierra Operacion productiva sin Reporting listo, restore de backup/snapshot autorizado, smoke publico autorizado con referencias no sensibles, observabilidad lista y aceptacion final autorizada.'
    )
}

$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resolvedOutput -Encoding UTF8
Write-Host "Stage 7 readiness gate: classification=$($result.classification), ready_for_stage7_close=$($result.ready_for_stage7_close)"
Write-Host "Output: $resolvedOutput"

if ($RequireClosure -and -not $readyForClose) {
    throw 'Etapa 7 no cerrada: faltan evidencias obligatorias de operacion productiva.'
}

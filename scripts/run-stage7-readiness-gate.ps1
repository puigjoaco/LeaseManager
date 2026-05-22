param(
    [string]$PythonExe = '',
    [string]$DatabaseUrl = '',
    [string]$OutputPath = '',
    [string]$RestoreEvidencePath = '',
    [string]$PublicSmokeEvidencePath = '',
    [string]$FinalAcceptanceRef = '',
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

function Test-AuthorizedRestoreEvidence($payload) {
    $sourceKind = Get-PayloadTextProperty $payload @('source_kind', 'restore_source_kind', 'source')
    $rehearsalKind = Get-PayloadTextProperty $payload @('rehearsal_kind')
    $mode = Get-PayloadTextProperty $payload @('mode')
    $authorizationRef = Get-PayloadTextProperty $payload @('authorization_ref', 'responsible_ref')
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

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'

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

$checks = [ordered]@{
    backend_check = $false
    migrations_applied = $false
    observability_audit = $false
    restore_evidence = $false
    restore_authorized_evidence = $false
    public_smoke_evidence = $false
    final_acceptance_ref = $false
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
}
finally {
    Pop-Location
}

$observability = Read-JsonFile $observabilityOutput
if ($observability.ready_for_stage7_observability -ne $true) {
    $issues += [ordered]@{
        code = 'stage7.observability_not_ready'
        severity = 'attention'
        message = 'La auditoria local de observabilidad aun no esta lista para cierre.'
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
    $checks.public_smoke_evidence = Test-SmokeEvidence $smokeEvidence
    if (-not $checks.public_smoke_evidence) {
        $issues += [ordered]@{
            code = 'stage7.public_smoke_invalid'
            severity = 'blocking'
            message = 'La evidencia de smoke no cubre los cuatro roles con login real.'
        }
    }
}

$checks.final_acceptance_ref = Test-NonSensitiveReference $FinalAcceptanceRef
if (-not $checks.final_acceptance_ref) {
    $issues += [ordered]@{
        code = 'stage7.final_acceptance_missing'
        severity = 'blocking'
        message = 'Falta referencia no sensible de aceptacion final.'
    }
}

$blockingIssueCount = @($issues | Where-Object { $_.severity -eq 'blocking' }).Count
$readyForClose = $blockingIssueCount -eq 0 -and $observability.ready_for_stage7_observability -eq $true
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
        issue_counts = $observability.issue_counts
    }
    restore_evidence = $restoreEvidenceSummary
    issues = $issues
    limitations = @(
        'Gate local de solo lectura para consolidar readiness de Etapa 7.',
        'No ejecuta smoke publico ni conecta proveedores externos.',
        'No usa secretos, .env, datos reales ni backups productivos.',
        'No cierra Operacion productiva sin restore de backup/snapshot autorizado, smoke publico autorizado, observabilidad lista y aceptacion final.'
    )
}

$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resolvedOutput -Encoding UTF8
Write-Host "Stage 7 readiness gate: classification=$($result.classification), ready_for_stage7_close=$($result.ready_for_stage7_close)"
Write-Host "Output: $resolvedOutput"

if ($RequireClosure -and -not $readyForClose) {
    throw 'Etapa 7 no cerrada: faltan evidencias obligatorias de operacion productiva.'
}

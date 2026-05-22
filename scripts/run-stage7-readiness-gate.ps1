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
$observabilityOutput = Join-Path $evidenceDir "stage7_observability_$timestamp.json"

$checks = [ordered]@{
    backend_check = $false
    migrations_applied = $false
    observability_audit = $false
    restore_evidence = $false
    public_smoke_evidence = $false
    final_acceptance_ref = $false
}
$issues = @()

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
    $checks.restore_evidence = ($restoreEvidence.restore_verified -eq $true)
    if (-not $checks.restore_evidence) {
        $issues += [ordered]@{
            code = 'stage7.restore_not_verified'
            severity = 'blocking'
            message = 'La evidencia de restore no reporta restore_verified=true.'
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

$readyForClose = ($issues | Where-Object { $_.severity -eq 'blocking' }).Count -eq 0 -and $observability.ready_for_stage7_observability -eq $true
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
    issues = $issues
    limitations = @(
        'Gate local de solo lectura para consolidar readiness de Etapa 7.',
        'No ejecuta smoke publico ni conecta proveedores externos.',
        'No usa secretos, .env, datos reales ni backups productivos.',
        'No cierra Operacion productiva sin restore verificado, smoke publico autorizado, observabilidad lista y aceptacion final.'
    )
}

$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $resolvedOutput -Encoding UTF8
Write-Host "Stage 7 readiness gate: classification=$($result.classification), ready_for_stage7_close=$($result.ready_for_stage7_close)"
Write-Host "Output: $resolvedOutput"

if ($RequireClosure -and -not $readyForClose) {
    throw 'Etapa 7 no cerrada: faltan evidencias obligatorias de operacion productiva.'
}

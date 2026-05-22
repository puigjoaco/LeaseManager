param(
    [string]$SourceLabel = 'stage1-local-readiness',

    [string]$DatabaseUrl = '',

    [string]$OutputPath = '',

    [string]$PythonExe = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Condition($condition, $message) {
    if (-not $condition) {
        throw $message
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'

if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
    $DatabaseUrl = "sqlite:///local-evidence/stage1/readiness/stage1_empty_$timestamp.sqlite3"
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot "local-evidence\stage1\readiness\stage1_local_readiness_$timestamp.json"
}

$wrapper = Join-Path $repoRoot 'scripts\run-stage1-snapshot-gate.ps1'
Assert-Condition (Test-Path $wrapper) "No existe el wrapper de gate Etapa 1 en $wrapper"

$wrapperArgs = @{
    SourceKind = 'snapshot_controlado'
    SourceLabel = $SourceLabel
    AuthorizationRef = 'stage1-local-readiness-self-test'
    ResponsibleRef = 'codex-local-readiness'
    DatabaseUrl = $DatabaseUrl
    OutputPath = $OutputPath
    RunMigrations = $true
}

if (-not [string]::IsNullOrWhiteSpace($PythonExe)) {
    $wrapperArgs['PythonExe'] = $PythonExe
}

Write-Host "Stage 1 local readiness" -ForegroundColor Cyan
Write-Host "Expected result: blocked by missing data, without external source."

try {
    & $wrapper @wrapperArgs
    throw 'El gate cerro Etapa 1 con una fuente vacia; esto no debe ocurrir.'
}
catch {
    Write-Host "Gate failed as expected for local readiness: $($_.Exception.Message)"
}

Assert-Condition (Test-Path $OutputPath) "No se genero JSON de auditoria en $OutputPath"
$audit = Get-Content -LiteralPath $OutputPath -Raw | ConvertFrom-Json

$issueCodes = @($audit.issues | ForEach-Object { $_.code })
$aggregateNames = @($audit.aggregate_classification.PSObject.Properties.Name)
$blockingCount = 0
if ($audit.issue_counts.PSObject.Properties.Name -contains 'blocking') {
    $blockingCount = [int]$audit.issue_counts.blocking
}

Assert-Condition ($audit.source_kind -eq 'snapshot_controlado') 'La fuente local de readiness debe reportar source_kind=snapshot_controlado.'
Assert-Condition ($audit.evidence_grade -eq $true) 'La fuente controlada local debe calificar como evidence_grade para probar el gate.'
Assert-Condition ($audit.has_required_stage1_data -eq $false) 'La fuente local vacia no debe tener datos requeridos de Etapa 1.'
Assert-Condition ($audit.ready_for_stage1_close -eq $false) 'La fuente local vacia no puede cerrar Etapa 1.'
Assert-Condition ($audit.classification -eq 'bloqueado_dato_real') 'La fuente local vacia debe clasificar como bloqueado_dato_real.'
Assert-Condition ($issueCodes -contains 'stage1.data_missing') 'La auditoria local debe incluir stage1.data_missing.'
Assert-Condition ($blockingCount -gt 0) 'La auditoria local debe reportar al menos un issue blocking.'
Assert-Condition ($aggregateNames -contains 'socios') 'El JSON debe incluir aggregate_classification.'

Write-Host "Stage 1 local readiness OK: gate healthy and closure remains blocked without data." -ForegroundColor Green
Write-Host "Output: $OutputPath"

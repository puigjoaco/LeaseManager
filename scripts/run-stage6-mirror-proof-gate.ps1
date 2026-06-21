param(
    [Parameter(Mandatory = $true)]
    [int]$EmpresaId,

    [Parameter(Mandatory = $true)]
    [int]$CommercialYear,

    [Parameter(Mandatory = $true)]
    [int]$TaxYear,

    [Parameter(Mandatory = $true)]
    [string]$ManifestPath,

    [string]$OwnershipEvidencePath = '',

    [string]$MirrorRunPath = '',

    [string]$SourceRoot = '',

    [ValidateSet('local', 'fixture', 'demo', 'snapshot_controlado', 'real_autorizado')]
    [string]$SourceKind = 'snapshot_controlado',

    [Parameter(Mandatory = $true)]
    [string]$SourceLabel,

    [Parameter(Mandatory = $true)]
    [string]$AuthorizationRef,

    [Parameter(Mandatory = $true)]
    [string]$Stage5EvidenceRef,

    [Parameter(Mandatory = $true)]
    [string]$Stage4SiiEvidenceRef,

    [Parameter(Mandatory = $true)]
    [string]$FiscalRuleRef,

    [Parameter(Mandatory = $true)]
    [string]$CertificatesProofRef,

    [Parameter(Mandatory = $true)]
    [string]$ResponsibleRef,

    [string]$DatabaseUrl = $env:DATABASE_URL,

    [string]$OutputPath = '',

    [string]$PythonExe = '',

    [switch]$RunMigrations,

    [switch]$FailOnIncomplete
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Condition($condition, $message) {
    if (-not $condition) {
        throw $message
    }
}

function Test-NonSensitiveReference([string]$value) {
    return -not [string]::IsNullOrWhiteSpace($value) `
        -and $value.Trim().Length -ge 3 `
        -and $value -notmatch '://|@|password|passwd|pwd|secret|token|bearer|api[_-]?key|credential|credencial|[0-9]{7,}-?[0-9kK]'
}

function Resolve-FullPath([string]$path) {
    if ([System.IO.Path]::IsPathRooted($path)) {
        return [System.IO.Path]::GetFullPath($path)
    }
    return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $path))
}

function Test-PathInsideDirectory([string]$path, [string]$directory) {
    $resolvedPath = [System.IO.Path]::GetFullPath($path)
    $resolvedDirectory = [System.IO.Path]::GetFullPath($directory).TrimEnd(
        [System.IO.Path]::DirectorySeparatorChar,
        [System.IO.Path]::AltDirectorySeparatorChar
    )
    return $resolvedPath.Equals($resolvedDirectory, [System.StringComparison]::OrdinalIgnoreCase) `
        -or $resolvedPath.StartsWith(
            "$resolvedDirectory$([System.IO.Path]::DirectorySeparatorChar)",
            [System.StringComparison]::OrdinalIgnoreCase
        )
}

function Resolve-DatabaseUrl([string]$databaseUrl, [string]$rootPath) {
    if ($databaseUrl -notmatch '^sqlite:///(?<Path>[^?]+)(?<Query>\?.*)?$') {
        return $databaseUrl
    }

    $rawSqlitePath = $Matches['Path']
    if ($rawSqlitePath -eq ':memory:' -or $rawSqlitePath -match '^[A-Za-z]:[\/\\]' -or $rawSqlitePath.StartsWith('/')) {
        return $databaseUrl
    }

    $query = $Matches['Query']
    if ($null -eq $query) {
        $query = ''
    }

    $sqlitePath = [System.Uri]::UnescapeDataString($rawSqlitePath)
    $absolutePath = [System.IO.Path]::GetFullPath((Join-Path $rootPath ($sqlitePath -replace '/', '\')))
    $parentDir = Split-Path -Parent $absolutePath
    if (-not [string]::IsNullOrWhiteSpace($parentDir)) {
        New-Item -ItemType Directory -Force -Path $parentDir | Out-Null
    }

    $normalizedPath = $absolutePath -replace '\\', '/'
    return "sqlite:///$normalizedPath$query"
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot 'backend'
$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot "local-evidence\stage6\mirror-proof\stage6_mirror_proof_$timestamp.json"
}
if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonExe = Join-Path $backendDir '.venv\Scripts\python.exe'
}

$pythonExe = Resolve-FullPath $PythonExe
$resolvedOutput = Resolve-FullPath $OutputPath
$resolvedManifest = Resolve-FullPath $ManifestPath
$resolvedOwnershipEvidence = ''
if (-not [string]::IsNullOrWhiteSpace($OwnershipEvidencePath)) {
    $resolvedOwnershipEvidence = Resolve-FullPath $OwnershipEvidencePath
}
$resolvedMirrorRun = ''
if (-not [string]::IsNullOrWhiteSpace($MirrorRunPath)) {
    $resolvedMirrorRun = Resolve-FullPath $MirrorRunPath
}
$resolvedSourceRoot = ''
if (-not [string]::IsNullOrWhiteSpace($SourceRoot)) {
    $resolvedSourceRoot = Resolve-FullPath $SourceRoot
}
$localEvidenceRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot 'local-evidence'))

Assert-Condition (Test-Path $pythonExe) "No existe el Python del backend en $pythonExe"
Assert-Condition (-not [string]::IsNullOrWhiteSpace($DatabaseUrl)) 'DATABASE_URL o -DatabaseUrl es obligatorio.'
Assert-Condition ($CommercialYear -ge 2000 -and $CommercialYear -le 2100) 'CommercialYear fuera de rango operativo.'
Assert-Condition ($TaxYear -eq ($CommercialYear + 1)) 'TaxYear debe corresponder al ano tributario inmediatamente posterior al ano comercial.'
Assert-Condition (Test-NonSensitiveReference $SourceLabel) 'SourceLabel debe ser una etiqueta no sensible.'
Assert-Condition (Test-NonSensitiveReference $AuthorizationRef) 'AuthorizationRef debe ser una referencia no sensible.'
Assert-Condition (Test-NonSensitiveReference $Stage5EvidenceRef) 'Stage5EvidenceRef debe ser una referencia no sensible.'
Assert-Condition (Test-NonSensitiveReference $Stage4SiiEvidenceRef) 'Stage4SiiEvidenceRef debe ser una referencia no sensible.'
Assert-Condition (Test-NonSensitiveReference $FiscalRuleRef) 'FiscalRuleRef debe ser una referencia no sensible.'
Assert-Condition (Test-NonSensitiveReference $CertificatesProofRef) 'CertificatesProofRef debe ser una referencia no sensible.'
Assert-Condition (Test-NonSensitiveReference $ResponsibleRef) 'ResponsibleRef debe ser una referencia no sensible.'
Assert-Condition (-not ($SourceKind -eq 'real_autorizado' -and $RunMigrations)) 'No se ejecutan migraciones contra real_autorizado desde este gate.'

if (Test-PathInsideDirectory $resolvedOutput $repoRoot) {
    Assert-Condition (Test-PathInsideDirectory $resolvedOutput $localEvidenceRoot) 'Si el output queda dentro del repo, debe estar bajo local-evidence/ para no versionar auditorias.'
}
if (Test-PathInsideDirectory $resolvedManifest $repoRoot) {
    Assert-Condition (Test-PathInsideDirectory $resolvedManifest $localEvidenceRoot) 'Si el manifiesto queda dentro del repo, debe estar bajo local-evidence/ para no versionar fuentes tributarias.'
}
if (-not [string]::IsNullOrWhiteSpace($resolvedOwnershipEvidence) -and (Test-PathInsideDirectory $resolvedOwnershipEvidence $repoRoot)) {
    Assert-Condition (Test-PathInsideDirectory $resolvedOwnershipEvidence $localEvidenceRoot) 'Si ownership evidence queda dentro del repo, debe estar bajo local-evidence/ para no versionar evidencia societaria.'
}
if (-not [string]::IsNullOrWhiteSpace($resolvedMirrorRun) -and (Test-PathInsideDirectory $resolvedMirrorRun $repoRoot)) {
    Assert-Condition (Test-PathInsideDirectory $resolvedMirrorRun $localEvidenceRoot) 'Si mirror run queda dentro del repo, debe estar bajo local-evidence/ para no versionar evidencia contable o tributaria.'
}
if (-not [string]::IsNullOrWhiteSpace($resolvedSourceRoot) -and (Test-PathInsideDirectory $resolvedSourceRoot $repoRoot)) {
    Assert-Condition (Test-PathInsideDirectory $resolvedSourceRoot $localEvidenceRoot) 'Si source-root queda dentro del repo, debe estar bajo local-evidence/ para no leer outputs versionados como evidencia.'
}

Assert-Condition (Test-Path -LiteralPath $resolvedManifest -PathType Leaf) "No existe manifest JSON: $resolvedManifest"
if (-not [string]::IsNullOrWhiteSpace($resolvedOwnershipEvidence)) {
    Assert-Condition (Test-Path -LiteralPath $resolvedOwnershipEvidence -PathType Leaf) "No existe ownership evidence JSON: $resolvedOwnershipEvidence"
}
if (-not [string]::IsNullOrWhiteSpace($resolvedMirrorRun)) {
    Assert-Condition (Test-Path -LiteralPath $resolvedMirrorRun -PathType Leaf) "No existe mirror run JSON: $resolvedMirrorRun"
}
if (-not [string]::IsNullOrWhiteSpace($resolvedSourceRoot)) {
    Assert-Condition (Test-Path -LiteralPath $resolvedSourceRoot -PathType Container) "No existe source-root: $resolvedSourceRoot"
}

Write-Host "Stage 6 mirror proof gate" -ForegroundColor Cyan
Write-Host "Empresa ID: $EmpresaId"
Write-Host "Commercial year: $CommercialYear"
Write-Host "Tax year: $TaxYear"
Write-Host "Source kind: $SourceKind"
Write-Host "Source label: $($SourceLabel.Trim())"
Write-Host "Run migrations: $($RunMigrations.IsPresent)"
Write-Host "Fail on incomplete: $($FailOnIncomplete.IsPresent)"
Write-Host "Output: $resolvedOutput"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedOutput) | Out-Null
$previousDatabaseUrl = $env:DATABASE_URL
$resolvedDatabaseUrl = Resolve-DatabaseUrl $DatabaseUrl $repoRoot
if ($resolvedDatabaseUrl -ne $DatabaseUrl) {
    Write-Host "Database URL: SQLite relativa resuelta contra el root del repo."
}
$env:DATABASE_URL = $resolvedDatabaseUrl

Push-Location $backendDir
try {
    & $pythonExe manage.py check
    Assert-Condition ($LASTEXITCODE -eq 0) 'manage.py check fallo.'

    if ($RunMigrations) {
        & $pythonExe manage.py migrate --noinput
        Assert-Condition ($LASTEXITCODE -eq 0) 'manage.py migrate fallo para mirror proof Etapa 6.'
    }

    $auditArgs = @(
        'manage.py',
        'audit_annual_tax_mirror_proof',
        '--empresa-id', $EmpresaId,
        '--commercial-year', $CommercialYear,
        '--tax-year', $TaxYear,
        '--manifest', $resolvedManifest,
        '--source-kind', $SourceKind,
        '--source-label', $SourceLabel.Trim(),
        '--authorization-ref', $AuthorizationRef.Trim(),
        '--stage5-evidence-ref', $Stage5EvidenceRef.Trim(),
        '--stage4-sii-evidence-ref', $Stage4SiiEvidenceRef.Trim(),
        '--fiscal-rule-ref', $FiscalRuleRef.Trim(),
        '--certificates-proof-ref', $CertificatesProofRef.Trim(),
        '--responsible-ref', $ResponsibleRef.Trim(),
        '--output', $resolvedOutput
    )
    if (-not [string]::IsNullOrWhiteSpace($resolvedSourceRoot)) {
        $auditArgs += @('--source-root', $resolvedSourceRoot)
    }
    if (-not [string]::IsNullOrWhiteSpace($resolvedOwnershipEvidence)) {
        $auditArgs += @('--ownership-evidence', $resolvedOwnershipEvidence)
    }
    if (-not [string]::IsNullOrWhiteSpace($resolvedMirrorRun)) {
        $auditArgs += @('--mirror-run', $resolvedMirrorRun)
    }
    if ($FailOnIncomplete) {
        $auditArgs += '--fail-on-incomplete'
    }

    & $pythonExe @auditArgs
    Assert-Condition ($LASTEXITCODE -eq 0) 'audit_annual_tax_mirror_proof fallo.'
}
finally {
    Pop-Location
    $env:DATABASE_URL = $previousDatabaseUrl
}

Assert-Condition (Test-Path -LiteralPath $resolvedOutput -PathType Leaf) "No se genero JSON de auditoria en $resolvedOutput"
$audit = Get-Content -LiteralPath $resolvedOutput -Raw | ConvertFrom-Json

Assert-Condition ($audit.schema_version -eq 'annual-tax-mirror-proof.v1') 'El JSON no reporta schema_version esperado.'
Assert-Condition ($audit.empresa_id -eq $EmpresaId) 'El JSON no reporta empresa_id esperado.'
Assert-Condition ($audit.commercial_year -eq $CommercialYear) 'El JSON no reporta commercial_year esperado.'
Assert-Condition ($audit.tax_year -eq $TaxYear) 'El JSON no reporta tax_year esperado.'
Assert-Condition ($audit.source_kind -eq $SourceKind) 'El JSON no reporta source_kind esperado.'
Assert-Condition ($audit.source_label -eq $SourceLabel.Trim()) 'El JSON no reporta source_label esperado.'
Assert-Condition ($audit.authorization_ref -eq $AuthorizationRef.Trim()) 'El JSON no reporta authorization_ref esperado.'
Assert-Condition ($audit.checks.PSObject.Properties.Name -contains 'source_documentation_confirmed') 'El JSON debe exponer source_documentation_confirmed.'
Assert-Condition ($audit.checks.PSObject.Properties.Name -contains 'architecture_complete_for_mirror_run') 'El JSON debe exponer architecture_complete_for_mirror_run.'
Assert-Condition ($audit.checks.PSObject.Properties.Name -contains 'comparison_ready_for_mirror_conclusion') 'El JSON debe exponer comparison_ready_for_mirror_conclusion.'
Assert-Condition ($audit.checks.PSObject.Properties.Name -contains 'stage6_ready_for_renta_anual') 'El JSON debe exponer stage6_ready_for_renta_anual.'
Assert-Condition ($audit.checks.PSObject.Properties.Name -contains 'mirror_run_evidence_confirmed') 'El JSON debe exponer mirror_run_evidence_confirmed.'
Assert-Condition ($audit.checks.PSObject.Properties.Name -contains 'safety_boundary_ok') 'El JSON debe exponer safety_boundary_ok.'
Assert-Condition ($audit.summary.PSObject.Properties.Name -contains 'ready_for_objective_completion') 'El JSON debe exponer ready_for_objective_completion.'
Assert-Condition ($audit.summary.PSObject.Properties.Name -contains 'classification') 'El JSON debe exponer classification.'
Assert-Condition ($audit.safety.writes_database -eq $false) 'El mirror proof no debe escribir DB.'
Assert-Condition ($audit.safety.uses_sii_real -eq $false) 'El mirror proof no debe usar SII real.'
Assert-Condition ($audit.safety.uses_credentials -eq $false) 'El mirror proof no debe usar credenciales.'
Assert-Condition ($audit.safety.uses_expected_outputs_as_inputs -eq $false) 'El mirror proof no debe usar outputs finales como input.'
Assert-Condition ($audit.safety.expected_outputs_used_as_comparison_only -eq $true) 'Los outputs esperados deben usarse solo como comparacion.'
Assert-Condition ($audit.safety.final_tax_calculation -eq $false) 'El mirror proof no debe declarar calculo tributario final.'
if ($FailOnIncomplete) {
    Assert-Condition ($audit.summary.ready_for_objective_completion -eq $true) 'FailOnIncomplete exige ready_for_objective_completion=true.'
    Assert-Condition ($audit.summary.classification -eq 'resuelto_confirmado') 'FailOnIncomplete exige classification=resuelto_confirmado.'
}

Write-Host "Stage 6 mirror proof gate OK: classification=$($audit.summary.classification), ready_for_objective_completion=$($audit.summary.ready_for_objective_completion)" -ForegroundColor Green
Write-Host "Output: $resolvedOutput"

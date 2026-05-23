param(
    [ValidateSet('local', 'fixture', 'demo', 'snapshot_controlado', 'real_autorizado')]
    [string]$SourceKind = 'local',

    [string]$SourceLabel = 'compliance-data-local-readiness',

    [string]$AuthorizationRef = '',

    [string]$PolicyApprovalRef = '',

    [string]$ResponsibleRef = '',

    [string]$ControlsEvidenceRef = '',

    [string]$ArchivedEvidenceRef = '',

    [string]$LegalReviewRef = '',

    [string]$AsOfDate = '',

    [string]$DatabaseUrl = '',

    [string]$OutputPath = '',

    [string]$PythonExe = '',

    [switch]$RunMigrations,

    [switch]$RequireReady
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
$usesDefaultDatabase = [string]::IsNullOrWhiteSpace($DatabaseUrl)
$authorizedSourceKinds = @('snapshot_controlado', 'real_autorizado')

if ($usesDefaultDatabase) {
    $DatabaseUrl = "sqlite:///local-evidence/compliance/readiness/compliance_data_empty_$timestamp.sqlite3"
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot "local-evidence\compliance\readiness\compliance_data_readiness_$timestamp.json"
}

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonExe = Join-Path $backendDir '.venv\Scripts\python.exe'
}

$pythonExe = Resolve-FullPath $PythonExe
$resolvedOutput = Resolve-FullPath $OutputPath
$localEvidenceRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot 'local-evidence'))
$shouldRunMigrations = $RunMigrations.IsPresent -or $usesDefaultDatabase
$isAuthorizedSourceKind = $authorizedSourceKinds -contains $SourceKind

Assert-Condition (Test-Path $pythonExe) "No existe el Python del backend en $pythonExe"
Assert-Condition (Test-NonSensitiveReference $SourceLabel) 'SourceLabel debe ser una etiqueta no sensible.'
Assert-Condition (-not ($SourceKind -eq 'real_autorizado' -and $shouldRunMigrations)) 'No se ejecutan migraciones contra real_autorizado desde este gate.'
if (-not [string]::IsNullOrWhiteSpace($AsOfDate)) {
    Assert-Condition ($AsOfDate -match '^\d{4}-\d{2}-\d{2}$') 'AsOfDate debe usar formato ISO YYYY-MM-DD.'
}
if ($isAuthorizedSourceKind) {
    Assert-Condition (Test-NonSensitiveReference $AuthorizationRef) 'AuthorizationRef es obligatorio para fuente evidencial y debe ser no sensible.'
    Assert-Condition (Test-NonSensitiveReference $PolicyApprovalRef) 'PolicyApprovalRef es obligatorio para cierre Compliance y debe ser no sensible.'
    Assert-Condition (Test-NonSensitiveReference $ResponsibleRef) 'ResponsibleRef es obligatorio para cierre Compliance y debe ser no sensible.'
    Assert-Condition (Test-NonSensitiveReference $ControlsEvidenceRef) 'ControlsEvidenceRef es obligatorio para cierre Compliance y debe ser no sensible.'
    Assert-Condition (Test-NonSensitiveReference $ArchivedEvidenceRef) 'ArchivedEvidenceRef es obligatorio para cierre Compliance y debe ser no sensible.'
    Assert-Condition (Test-NonSensitiveReference $LegalReviewRef) 'LegalReviewRef es obligatorio para cierre Compliance y debe ser no sensible.'
}
if (Test-PathInsideDirectory $resolvedOutput $repoRoot) {
    Assert-Condition (Test-PathInsideDirectory $resolvedOutput $localEvidenceRoot) 'Si el output queda dentro del repo, debe estar bajo local-evidence/ para no versionar auditorias.'
}

Write-Host "Compliance data readiness gate" -ForegroundColor Cyan
Write-Host "Source kind: $SourceKind"
Write-Host "Source label: $($SourceLabel.Trim())"
Write-Host "Run migrations: $shouldRunMigrations"
Write-Host "Require ready: $($RequireReady.IsPresent)"
Write-Host "Output: $resolvedOutput"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedOutput) | Out-Null
$previousDatabaseUrl = $env:DATABASE_URL
$previousCacheUrl = $env:DJANGO_CACHE_URL
$resolvedDatabaseUrl = Resolve-DatabaseUrl $DatabaseUrl $repoRoot
if ($resolvedDatabaseUrl -ne $DatabaseUrl) {
    Write-Host "Database URL: SQLite relativa resuelta contra el root del repo."
}
$env:DATABASE_URL = $resolvedDatabaseUrl
$env:DJANGO_CACHE_URL = 'locmem://compliance-data-readiness-gate'

Push-Location $backendDir
try {
    & $pythonExe manage.py check
    Assert-Condition ($LASTEXITCODE -eq 0) 'manage.py check fallo.'

    if ($shouldRunMigrations) {
        & $pythonExe manage.py migrate --noinput
        Assert-Condition ($LASTEXITCODE -eq 0) 'manage.py migrate fallo para readiness Compliance.'
    }

    $auditArgs = @(
        'manage.py',
        'audit_compliance_data_readiness',
        '--source-kind', $SourceKind,
        '--source-label', $SourceLabel.Trim(),
        '--output', $resolvedOutput
    )
    if (-not [string]::IsNullOrWhiteSpace($AuthorizationRef)) {
        $auditArgs += @('--authorization-ref', $AuthorizationRef.Trim())
    }
    if (-not [string]::IsNullOrWhiteSpace($PolicyApprovalRef)) {
        $auditArgs += @('--policy-approval-ref', $PolicyApprovalRef.Trim())
    }
    if (-not [string]::IsNullOrWhiteSpace($ResponsibleRef)) {
        $auditArgs += @('--responsible-ref', $ResponsibleRef.Trim())
    }
    if (-not [string]::IsNullOrWhiteSpace($ControlsEvidenceRef)) {
        $auditArgs += @('--controls-evidence-ref', $ControlsEvidenceRef.Trim())
    }
    if (-not [string]::IsNullOrWhiteSpace($ArchivedEvidenceRef)) {
        $auditArgs += @('--archived-evidence-ref', $ArchivedEvidenceRef.Trim())
    }
    if (-not [string]::IsNullOrWhiteSpace($LegalReviewRef)) {
        $auditArgs += @('--legal-review-ref', $LegalReviewRef.Trim())
    }
    if (-not [string]::IsNullOrWhiteSpace($AsOfDate)) {
        $auditArgs += @('--as-of-date', $AsOfDate.Trim())
    }
    if ($RequireReady) {
        $auditArgs += '--fail-on-attention'
    }

    & $pythonExe @auditArgs
    Assert-Condition ($LASTEXITCODE -eq 0) 'audit_compliance_data_readiness fallo.'
}
finally {
    Pop-Location
    $env:DATABASE_URL = $previousDatabaseUrl
    $env:DJANGO_CACHE_URL = $previousCacheUrl
}

Assert-Condition (Test-Path $resolvedOutput) "No se genero JSON de auditoria en $resolvedOutput"
$audit = Get-Content -LiteralPath $resolvedOutput -Raw | ConvertFrom-Json
$issueCodes = @($audit.issues | ForEach-Object { $_.code })

Assert-Condition ($audit.source_kind -eq $SourceKind) 'El JSON no reporta el source_kind solicitado.'
Assert-Condition ($audit.gate -eq 'Compliance.DatosPersonalesChile2026') 'El JSON debe declarar el gate canonico de Compliance.'
Assert-Condition ($audit.PSObject.Properties.Name -contains 'source_kind_authorized_for_close') 'El JSON debe exponer source_kind_authorized_for_close.'
Assert-Condition ($audit.PSObject.Properties.Name -contains 'ready_for_compliance_data') 'El JSON debe exponer ready_for_compliance_data.'
Assert-Condition ($audit.sections.PSObject.Properties.Name -contains 'source_trace') 'El JSON debe exponer source_trace.'
Assert-Condition ($audit.sections.PSObject.Properties.Name -contains 'final_evidence') 'El JSON debe exponer final_evidence.'
if ($isAuthorizedSourceKind) {
    Assert-Condition ($audit.source_kind_authorized_for_close -eq $true) 'La fuente evidencial debe quedar autorizada por tipo.'
    Assert-Condition ($audit.sections.source_trace.source_label -eq $true) 'La fuente evidencial debe tener source_label trazable.'
    Assert-Condition ($audit.sections.source_trace.authorization_ref -eq $true) 'La fuente evidencial debe tener authorization_ref trazable.'
    Assert-Condition ($audit.sections.final_evidence.policy_approval_ref -eq $true) 'La fuente evidencial debe tener politica aprobada trazable.'
    Assert-Condition ($audit.sections.final_evidence.responsible_ref -eq $true) 'La fuente evidencial debe tener responsables trazables.'
    Assert-Condition ($audit.sections.final_evidence.controls_evidence_ref -eq $true) 'La fuente evidencial debe tener controles trazables.'
    Assert-Condition ($audit.sections.final_evidence.archived_evidence_ref -eq $true) 'La fuente evidencial debe tener evidencia archivada trazable.'
    Assert-Condition ($audit.sections.final_evidence.legal_review_ref -eq $true) 'La fuente evidencial debe tener validacion legal-operativa trazable.'
}
else {
    Assert-Condition ($audit.source_kind_authorized_for_close -eq $false) 'La fuente local/fixture/demo no puede quedar autorizada para cierre.'
    Assert-Condition ($audit.ready_for_compliance_data -eq $false) 'La fuente local/fixture/demo no puede cerrar Compliance.'
    Assert-Condition ($issueCodes -contains 'compliance.source_kind_not_authorized') 'La auditoria local debe reportar compliance.source_kind_not_authorized.'
}
if ($RequireReady) {
    Assert-Condition ($audit.ready_for_compliance_data -eq $true) 'RequireReady exige ready_for_compliance_data=true.'
    Assert-Condition ($audit.classification -eq 'resuelto_confirmado') 'RequireReady exige classification=resuelto_confirmado.'
}

Write-Host "Compliance data readiness gate OK: classification=$($audit.classification), ready_for_compliance_data=$($audit.ready_for_compliance_data)" -ForegroundColor Green
Write-Host "Output: $resolvedOutput"

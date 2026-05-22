param(
    [ValidateSet('local', 'fixture', 'demo', 'snapshot_controlado', 'real_autorizado')]
    [string]$SourceKind = 'local',

    [string]$SourceLabel = 'stage5-documents-local-readiness',

    [string]$AuthorizationRef = '',

    [string]$FinalPolicyRef = '',

    [string]$ControlledPdfRef = '',

    [string]$ResponsibleRef = '',

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
    $DatabaseUrl = "sqlite:///local-evidence/stage5-documents/readiness/stage5_documents_empty_$timestamp.sqlite3"
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot "local-evidence\stage5-documents\readiness\stage5_documents_readiness_$timestamp.json"
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
if ($isAuthorizedSourceKind) {
    Assert-Condition (Test-NonSensitiveReference $AuthorizationRef) 'AuthorizationRef es obligatorio para fuente evidencial y debe ser no sensible.'
    Assert-Condition (Test-NonSensitiveReference $FinalPolicyRef) 'FinalPolicyRef es obligatorio para cierre documental y debe ser no sensible.'
    Assert-Condition (Test-NonSensitiveReference $ControlledPdfRef) 'ControlledPdfRef es obligatorio para cierre documental y debe ser no sensible.'
    Assert-Condition (Test-NonSensitiveReference $ResponsibleRef) 'ResponsibleRef es obligatorio para cierre documental y debe ser no sensible.'
}
if (Test-PathInsideDirectory $resolvedOutput $repoRoot) {
    Assert-Condition (Test-PathInsideDirectory $resolvedOutput $localEvidenceRoot) 'Si el output queda dentro del repo, debe estar bajo local-evidence/ para no versionar auditorias.'
}

Write-Host "Stage 5 documents readiness gate" -ForegroundColor Cyan
Write-Host "Source kind: $SourceKind"
Write-Host "Source label: $($SourceLabel.Trim())"
Write-Host "Run migrations: $shouldRunMigrations"
Write-Host "Require ready: $($RequireReady.IsPresent)"
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

    if ($shouldRunMigrations) {
        & $pythonExe manage.py migrate --noinput
        Assert-Condition ($LASTEXITCODE -eq 0) 'manage.py migrate fallo para readiness documental Etapa 5.'
    }

    $auditArgs = @(
        'manage.py',
        'audit_document_readiness',
        '--source-kind', $SourceKind,
        '--source-label', $SourceLabel.Trim(),
        '--output', $resolvedOutput
    )
    if (-not [string]::IsNullOrWhiteSpace($AuthorizationRef)) {
        $auditArgs += @('--authorization-ref', $AuthorizationRef.Trim())
    }
    if (-not [string]::IsNullOrWhiteSpace($FinalPolicyRef)) {
        $auditArgs += @('--final-policy-ref', $FinalPolicyRef.Trim())
    }
    if (-not [string]::IsNullOrWhiteSpace($ControlledPdfRef)) {
        $auditArgs += @('--controlled-pdf-ref', $ControlledPdfRef.Trim())
    }
    if (-not [string]::IsNullOrWhiteSpace($ResponsibleRef)) {
        $auditArgs += @('--responsible-ref', $ResponsibleRef.Trim())
    }
    if ($RequireReady) {
        $auditArgs += '--fail-on-attention'
    }

    & $pythonExe @auditArgs
    Assert-Condition ($LASTEXITCODE -eq 0) 'audit_document_readiness fallo.'
}
finally {
    Pop-Location
    $env:DATABASE_URL = $previousDatabaseUrl
}

Assert-Condition (Test-Path $resolvedOutput) "No se genero JSON de auditoria en $resolvedOutput"
$audit = Get-Content -LiteralPath $resolvedOutput -Raw | ConvertFrom-Json
$issueCodes = @($audit.issues | ForEach-Object { $_.code })

Assert-Condition ($audit.source_kind -eq $SourceKind) 'El JSON no reporta el source_kind solicitado.'
Assert-Condition ($audit.PSObject.Properties.Name -contains 'source_kind_authorized_for_close') 'El JSON debe exponer source_kind_authorized_for_close.'
Assert-Condition ($audit.PSObject.Properties.Name -contains 'ready_for_stage5_documents') 'El JSON debe exponer ready_for_stage5_documents.'
Assert-Condition ($audit.sections.PSObject.Properties.Name -contains 'source_trace') 'El JSON debe exponer source_trace.'
if ($isAuthorizedSourceKind) {
    Assert-Condition ($audit.source_kind_authorized_for_close -eq $true) 'La fuente evidencial debe quedar autorizada por tipo.'
    Assert-Condition ($audit.sections.source_trace.source_label -eq $true) 'La fuente evidencial debe tener source_label trazable.'
    Assert-Condition ($audit.sections.source_trace.authorization_ref -eq $true) 'La fuente evidencial debe tener authorization_ref trazable.'
}
else {
    Assert-Condition ($audit.source_kind_authorized_for_close -eq $false) 'La fuente local/fixture/demo no puede quedar autorizada para cierre.'
    Assert-Condition ($audit.ready_for_stage5_documents -eq $false) 'La fuente local/fixture/demo no puede cerrar Documentos.'
    Assert-Condition ($issueCodes -contains 'documents.source_kind_not_authorized') 'La auditoria local debe reportar documents.source_kind_not_authorized.'
}
if ($RequireReady) {
    Assert-Condition ($audit.ready_for_stage5_documents -eq $true) 'RequireReady exige ready_for_stage5_documents=true.'
    Assert-Condition ($audit.classification -eq 'resuelto_confirmado') 'RequireReady exige classification=resuelto_confirmado.'
}

Write-Host "Stage 5 documents readiness gate OK: classification=$($audit.classification), ready_for_stage5_documents=$($audit.ready_for_stage5_documents)" -ForegroundColor Green
Write-Host "Output: $resolvedOutput"

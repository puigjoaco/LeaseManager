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

if ($usesDefaultDatabase) {
    $DatabaseUrl = "sqlite:///local-evidence/stage1/readiness/stage1_empty_$timestamp.sqlite3"
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot "local-evidence\stage1\readiness\stage1_local_readiness_$timestamp.json"
}

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonExe = Join-Path $backendDir '.venv\Scripts\python.exe'
}
$pythonExe = Resolve-FullPath $PythonExe
$resolvedOutput = Resolve-FullPath $OutputPath
$localEvidenceRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot 'local-evidence'))

Assert-Condition (Test-Path $pythonExe) "No existe el Python del backend en $pythonExe"
Assert-Condition (Test-NonSensitiveReference $SourceLabel) 'SourceLabel debe ser una etiqueta local no sensible.'
if (Test-PathInsideDirectory $resolvedOutput $repoRoot) {
    Assert-Condition (Test-PathInsideDirectory $resolvedOutput $localEvidenceRoot) 'Si el output queda dentro del repo, debe estar bajo local-evidence/ para no versionar auditorias locales.'
}

Write-Host "Stage 1 local readiness" -ForegroundColor Cyan
Write-Host "Source kind: local"
Write-Host "Source label: $($SourceLabel.Trim())"
Write-Host "Expected result: diagnostic only; no evidence-grade closure."
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

    & $pythonExe manage.py migrate --noinput
    Assert-Condition ($LASTEXITCODE -eq 0) 'manage.py migrate fallo para readiness local.'

    & $pythonExe manage.py audit_stage1_matrix `
        --source-kind local `
        --source-label $SourceLabel.Trim() `
        --output $resolvedOutput
    Assert-Condition ($LASTEXITCODE -eq 0) 'audit_stage1_matrix local fallo.'
}
finally {
    Pop-Location
    $env:DATABASE_URL = $previousDatabaseUrl
}

Assert-Condition (Test-Path $resolvedOutput) "No se genero JSON de auditoria en $resolvedOutput"
$audit = Get-Content -LiteralPath $resolvedOutput -Raw | ConvertFrom-Json

$issueCodes = @($audit.issues | ForEach-Object { $_.code })
$aggregateNames = @($audit.aggregate_classification.PSObject.Properties.Name)

Assert-Condition ($audit.source_kind -eq 'local') 'El readiness local debe reportar source_kind=local.'
Assert-Condition ($audit.evidence_grade -eq $false) 'El readiness local no debe calificar como evidencia de cierre.'
Assert-Condition ($audit.ready_for_stage1_close -eq $false) 'El readiness local no puede cerrar Etapa 1.'
Assert-Condition ($audit.classification -eq 'implementado_sin_evidencia') 'El readiness local debe quedar como implementado_sin_evidencia.'
Assert-Condition (-not ($issueCodes -contains 'stage1.data_missing')) 'stage1.data_missing corresponde al gate evidencial con require-data, no al readiness local.'
Assert-Condition ($aggregateNames -contains 'socios') 'El JSON debe incluir aggregate_classification.'
if ($usesDefaultDatabase) {
    Assert-Condition ($audit.has_required_stage1_data -eq $false) 'La SQLite local vacia no debe tener datos requeridos de Etapa 1.'
}

Write-Host "Stage 1 local readiness OK: diagnostic remains non-evidential." -ForegroundColor Green
Write-Host "Output: $resolvedOutput"

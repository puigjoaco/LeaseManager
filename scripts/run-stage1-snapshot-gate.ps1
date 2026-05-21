param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('snapshot_controlado', 'real_autorizado')]
    [string]$SourceKind,

    [Parameter(Mandatory = $true)]
    [string]$SourceLabel,

    [string]$DatabaseUrl = $env:DATABASE_URL,

    [string]$OutputPath = '',

    [string]$PythonExe = '',

    [switch]$RunMigrations
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Condition($condition, $message) {
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
if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $PythonExe = Join-Path $backendDir '.venv\Scripts\python.exe'
}
$pythonExe = Resolve-FullPath $PythonExe

Assert-Condition (Test-Path $pythonExe) "No existe el Python del backend en $pythonExe"
Assert-Condition (-not [string]::IsNullOrWhiteSpace($DatabaseUrl)) 'DATABASE_URL o -DatabaseUrl es obligatorio.'
Assert-Condition (-not [string]::IsNullOrWhiteSpace($SourceLabel)) 'SourceLabel es obligatorio y no debe contener datos sensibles.'
Assert-Condition ($SourceLabel.Trim().Length -ge 3) 'SourceLabel debe ser una etiqueta no sensible y trazable.'
Assert-Condition ($SourceLabel -notmatch '://|@|password|passwd|pwd|secret|token|[0-9]{7,}-?[0-9kK]') 'SourceLabel parece contener URL, secreto o RUT; usa una etiqueta no sensible.'
Assert-Condition (-not ($SourceKind -eq 'real_autorizado' -and $RunMigrations)) 'No se ejecutan migraciones contra real_autorizado desde este gate; usa snapshot_controlado para clones migrables.'

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $OutputPath = Join-Path $repoRoot "local-evidence\stage1\stage1_matrix_audit_$timestamp.json"
}

$resolvedOutput = Resolve-FullPath $OutputPath
$localEvidenceRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot 'local-evidence'))
if ($resolvedOutput.StartsWith([System.IO.Path]::GetFullPath($repoRoot), [System.StringComparison]::OrdinalIgnoreCase)) {
    Assert-Condition ($resolvedOutput.StartsWith($localEvidenceRoot, [System.StringComparison]::OrdinalIgnoreCase)) 'Si el output queda dentro del repo, debe estar bajo local-evidence/ para no versionar datos de auditoria.'
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $resolvedOutput) | Out-Null

Write-Host "Stage 1 snapshot gate" -ForegroundColor Cyan
Write-Host "Source kind: $SourceKind"
Write-Host "Source label: $($SourceLabel.Trim())"
Write-Host "Run migrations: $($RunMigrations.IsPresent)"
Write-Host "Output: $resolvedOutput"

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
        Assert-Condition ($LASTEXITCODE -eq 0) 'manage.py migrate fallo sobre snapshot_controlado.'
    }

    & $pythonExe manage.py audit_stage1_matrix `
        --source-kind $SourceKind `
        --source-label $SourceLabel.Trim() `
        --require-data `
        --fail-on-violations `
        --output $resolvedOutput
    Assert-Condition ($LASTEXITCODE -eq 0) 'audit_stage1_matrix no cerro Etapa 1; revisa el JSON de salida.'

    $audit = Get-Content -LiteralPath $resolvedOutput -Raw | ConvertFrom-Json
    Assert-Condition ($audit.ready_for_stage1_close -eq $true) 'El auditor no marco ready_for_stage1_close=true.'
    Assert-Condition ($audit.evidence_grade -eq $true) 'La fuente no califica como evidencia de cierre.'
    Write-Host "Stage 1 matrix gate OK." -ForegroundColor Green
}
finally {
    Pop-Location
    $env:DATABASE_URL = $previousDatabaseUrl
}

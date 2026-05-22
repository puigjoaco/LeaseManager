param(
    [string]$ComposeFile = '',

    [string]$OutputPath = '',

    [switch]$PlanOnly,

    [switch]$SkipComposeUp,

    [switch]$KeepDatabases
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

function Invoke-External([string]$file, [string[]]$arguments) {
    Write-Host "+ $file $($arguments -join ' ')"
    & $file @arguments
    Assert-Condition ($LASTEXITCODE -eq 0) "$file fallo con codigo $LASTEXITCODE."
}

function Get-ExternalOutput([string]$file, [string[]]$arguments) {
    Write-Host "+ $file $($arguments -join ' ')"
    $output = & $file @arguments
    Assert-Condition ($LASTEXITCODE -eq 0) "$file fallo con codigo $LASTEXITCODE."
    return ($output | Out-String).Trim()
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

function Assert-OutputPathSafe([string]$path, [string]$repoRoot) {
    $resolvedOutput = Resolve-FullPath $path
    $localEvidenceRoot = [System.IO.Path]::GetFullPath((Join-Path $repoRoot 'local-evidence'))
    $repoRootFull = [System.IO.Path]::GetFullPath($repoRoot)

    if (Test-PathInsideDirectory $resolvedOutput $repoRootFull) {
        Assert-Condition `
            (Test-PathInsideDirectory $resolvedOutput $localEvidenceRoot) `
            'Si el output queda dentro del repo, debe estar bajo local-evidence/ para no versionar evidencia de restore.'
    }

    return $resolvedOutput
}

function Invoke-Compose([string[]]$arguments) {
    Invoke-External 'docker' (@('compose', '-f', $script:resolvedComposeFile) + $arguments)
}

function Get-ComposeOutput([string[]]$arguments) {
    return Get-ExternalOutput 'docker' (@('compose', '-f', $script:resolvedComposeFile) + $arguments)
}

function Invoke-Postgres([string]$databaseName, [string]$sql) {
    return Get-ComposeOutput @(
        'exec', '-T', 'postgres',
        'psql', '-U', 'leasemanager', '-d', $databaseName,
        '-v', 'ON_ERROR_STOP=1',
        '-X', '-q', '-At', '-F', '|',
        '-c', $sql
    )
}

function Invoke-PostgresCommand([string]$databaseName, [string]$sql) {
    Invoke-Compose @(
        'exec', '-T', 'postgres',
        'psql', '-U', 'leasemanager', '-d', $databaseName,
        '-v', 'ON_ERROR_STOP=1',
        '-X', '-q',
        '-c', $sql
    )
}

$repoRoot = Split-Path -Parent $PSScriptRoot
if ([string]::IsNullOrWhiteSpace($ComposeFile)) {
    $ComposeFile = Join-Path $repoRoot 'infra\docker-compose.yml'
}

$script:resolvedComposeFile = Resolve-FullPath $ComposeFile
Assert-Condition (Test-Path $script:resolvedComposeFile) "No existe ComposeFile: $script:resolvedComposeFile"

$timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$suffix = ([guid]::NewGuid().ToString('N')).Substring(0, 8)
$sourceDb = "lm_restore_src_${timestamp}_$suffix".ToLowerInvariant()
$targetDb = "lm_restore_dst_${timestamp}_$suffix".ToLowerInvariant()
$containerDump = "/tmp/leasemanager_restore_rehearsal_${timestamp}_$suffix.sql"

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot "local-evidence\restore\restore_rehearsal_$timestamp.json"
}
$resolvedOutput = Assert-OutputPathSafe $OutputPath $repoRoot
$evidenceDir = Split-Path -Parent $resolvedOutput
New-Item -ItemType Directory -Force -Path $evidenceDir | Out-Null
$localDumpPath = Join-Path $evidenceDir "restore_rehearsal_$timestamp.sql"

if ($PlanOnly) {
    $result = [ordered]@{
        generated_at = (Get-Date).ToUniversalTime().ToString('o')
        rehearsal_kind = 'postgres_local_synthetic_restore'
        mode = 'plan_only'
        compose_file = ($script:resolvedComposeFile.Replace('\', '/'))
        planned_backup_file = ($localDumpPath.Replace('\', '/'))
        planned_source_database = $sourceDb
        planned_target_database = $targetDb
        restore_verified = $false
        checks = [ordered]@{
            compose_file_exists = $true
            output_under_local_evidence = Test-PathInsideDirectory `
                $resolvedOutput `
                ([System.IO.Path]::GetFullPath((Join-Path $repoRoot 'local-evidence')))
        }
        next_command = '.\scripts\run-postgres-restore-rehearsal.ps1'
        limitations = @(
            'PlanOnly no ejecuta Docker, pg_dump ni restore.',
            'Sirve para validar rutas y preflight documental sin tocar datos.',
            'No reemplaza el rehearsal ejecutado ni cierra Operacion productiva.'
        )
    }
    $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resolvedOutput -Encoding UTF8
    Write-Host "PostgreSQL restore rehearsal plan OK." -ForegroundColor Green
    Write-Host "Plan evidence: $resolvedOutput"
    exit 0
}

Step 'Preflight Docker/PostgreSQL local'
Invoke-External 'docker' @('version', '--format', '{{.Server.Version}}')
if (-not $SkipComposeUp) {
    Invoke-Compose @('up', '-d', 'postgres')
}

$ready = $false
for ($attempt = 1; $attempt -le 30; $attempt++) {
    & docker compose -f $script:resolvedComposeFile exec -T postgres pg_isready -U leasemanager -d leasemanager *> $null
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    Start-Sleep -Seconds 2
}
Assert-Condition $ready 'PostgreSQL local no quedo listo dentro del tiempo esperado.'

try {
    Step 'Crear base sintetica de origen'
    Invoke-PostgresCommand 'postgres' "DROP DATABASE IF EXISTS $sourceDb WITH (FORCE);"
    Invoke-PostgresCommand 'postgres' "DROP DATABASE IF EXISTS $targetDb WITH (FORCE);"
    Invoke-Compose @('exec', '-T', 'postgres', 'createdb', '-U', 'leasemanager', $sourceDb)

    $seedSql = @"
CREATE TABLE restore_rehearsal_items (
    id integer PRIMARY KEY,
    lease_code text NOT NULL,
    amount_cents integer NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
INSERT INTO restore_rehearsal_items (id, lease_code, amount_cents)
VALUES
    (1, 'LM-RESTORE-001', 125000),
    (2, 'LM-RESTORE-002', 275000),
    (3, 'LM-RESTORE-003', 60000);
"@
    Invoke-PostgresCommand $sourceDb $seedSql

    $digestSql = "SELECT count(*)::int, COALESCE(sum(amount_cents), 0)::bigint, string_agg(lease_code, ',' ORDER BY id) FROM restore_rehearsal_items;"
    $sourceDigest = Invoke-Postgres $sourceDb $digestSql
    Assert-Condition (-not [string]::IsNullOrWhiteSpace($sourceDigest)) 'No se pudo calcular digest de origen.'

    Step 'Generar backup sintetico'
    Invoke-Compose @(
        'exec', '-T', 'postgres',
        'sh', '-lc',
        "pg_dump -U leasemanager --format=plain --no-owner --no-privileges --dbname=$sourceDb > $containerDump"
    )
    Invoke-Compose @('cp', "postgres:$containerDump", $localDumpPath)
    Assert-Condition (Test-Path $localDumpPath) "No se copio dump local en $localDumpPath"

    Step 'Restaurar en base destino y comparar'
    Invoke-Compose @('exec', '-T', 'postgres', 'createdb', '-U', 'leasemanager', $targetDb)
    Invoke-Compose @(
        'exec', '-T', 'postgres',
        'sh', '-lc',
        "psql -U leasemanager -v ON_ERROR_STOP=1 -d $targetDb < $containerDump"
    )

    $targetDigest = Invoke-Postgres $targetDb $digestSql
    Assert-Condition ($sourceDigest -eq $targetDigest) "Restore no reprodujo digest: origen=$sourceDigest destino=$targetDigest"

    $digestParts = $targetDigest.Split('|')
    $result = [ordered]@{
        generated_at = (Get-Date).ToUniversalTime().ToString('o')
        rehearsal_kind = 'postgres_local_synthetic_restore'
        source = 'synthetic_fixture'
        compose_file = ($script:resolvedComposeFile.Replace('\', '/'))
        backup_file = ($localDumpPath.Replace('\', '/'))
        source_database = $sourceDb
        target_database = $targetDb
        row_count = [int]$digestParts[0]
        amount_cents_sum = [int64]$digestParts[1]
        code_digest = $digestParts[2]
        restore_verified = $true
        cleanup = if ($KeepDatabases) { 'kept_temp_databases' } else { 'dropped_temp_databases' }
        limitations = @(
            'Ensayo local con datos sinteticos.',
            'No usa datos reales, secretos, .env ni snapshots externos.',
            'No reemplaza restore con backup autorizado ni cierra Operacion productiva.'
        )
    }
    $result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $resolvedOutput -Encoding UTF8

    Write-Host "PostgreSQL restore rehearsal OK." -ForegroundColor Green
    Write-Host "Evidence: $resolvedOutput"
}
finally {
    if ($KeepDatabases) {
        Write-Host "KeepDatabases activo: no se eliminan $sourceDb ni $targetDb." -ForegroundColor Yellow
    }
    else {
        Step 'Cleanup'
        & docker compose -f $script:resolvedComposeFile exec -T postgres psql -U leasemanager -d postgres -X -q -c "DROP DATABASE IF EXISTS $targetDb WITH (FORCE);" *> $null
        & docker compose -f $script:resolvedComposeFile exec -T postgres psql -U leasemanager -d postgres -X -q -c "DROP DATABASE IF EXISTS $sourceDb WITH (FORCE);" *> $null
        & docker compose -f $script:resolvedComposeFile exec -T postgres sh -lc "rm -f $containerDump" *> $null
    }
}

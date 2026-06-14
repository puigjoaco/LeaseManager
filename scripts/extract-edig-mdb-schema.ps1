param(
    [string]$EdigRoot,
    [string]$OutputDir,
    [string[]]$ProviderCandidates = @(
        'Microsoft.ACE.OLEDB.16.0',
        'Microsoft.ACE.OLEDB.12.0',
        'Microsoft.Jet.OLEDB.4.0'
    ),
    [switch]$KeepTempCopies
)

if ([Environment]::Is64BitProcess) {
    $powershell32 = Join-Path $env:WINDIR 'SysWOW64\WindowsPowerShell\v1.0\powershell.exe'
    if (Test-Path -LiteralPath $powershell32) {
        $forwardArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $PSCommandPath)
        if ($PSBoundParameters.ContainsKey('EdigRoot')) {
            $forwardArgs += @('-EdigRoot', $EdigRoot)
        }
        if ($PSBoundParameters.ContainsKey('OutputDir')) {
            $forwardArgs += @('-OutputDir', $OutputDir)
        }
        if ($PSBoundParameters.ContainsKey('ProviderCandidates')) {
            $forwardArgs += '-ProviderCandidates'
            $forwardArgs += $ProviderCandidates
        }
        if ($KeepTempCopies) {
            $forwardArgs += '-KeepTempCopies'
        }
        & $powershell32 @forwardArgs
        exit $LASTEXITCODE
    }
}

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Assert-Condition($condition, [string]$message) {
    if (-not $condition) {
        throw $message
    }
}

function Get-GitRoot {
    $root = & git rev-parse --show-toplevel
    Assert-Condition ($LASTEXITCODE -eq 0) 'No se pudo resolver el root Git.'
    return ($root | Select-Object -First 1)
}

function ConvertTo-RelativePath([string]$root, [string]$path) {
    return $path.Substring($root.Length).TrimStart('\', '/')
}

function Get-CoreMdbRelativePaths {
    return @(
        'CENTRAL\comun.MDB',
        'CENTRAL\prtRegAT21.MDB',
        'CENTRAL\R14PARA26.MDB',
        'DATOS\CANova.mdb',
        'DATOS\F29LGH.MDB',
        'DATOS\PRO26.MDB',
        'DATOS\Reg14.MDB'
    )
}

function ConvertTo-SafeFileName([string]$relativePath) {
    return (($relativePath -replace '[\\/:*?"<>|]', '_') -replace '\s+', '_')
}

function Get-DataRowValue($row, [string]$columnName) {
    if ($row.Table.Columns.Contains($columnName) -and $row[$columnName] -ne [DBNull]::Value) {
        return $row[$columnName]
    }
    return $null
}

function Redact-SensitiveName([string]$name) {
    if ([string]::IsNullOrWhiteSpace($name)) {
        return $name
    }
    if ($name -match '(?i)(clave|password|passwd|token|secret|licen|serial|cert|x509|pfx|private|rut|mail|correo)') {
        return '<redacted_sensitive_name>'
    }
    return $name
}

function Open-OleDbConnection([string]$provider, [string]$path) {
    $connectionString = "Provider=$provider;Data Source=$path;Persist Security Info=False;"
    $connection = [System.Data.OleDb.OleDbConnection]::new($connectionString)
    $connection.Open()
    return $connection
}

function Resolve-WorkingProvider([string[]]$providers, [string]$path) {
    $failures = @()
    foreach ($provider in $providers) {
        try {
            $connection = Open-OleDbConnection $provider $path
            $connection.Close()
            $connection.Dispose()
            return [pscustomobject]@{
                provider = $provider
                failures = $failures
            }
        }
        catch {
            $failures += [pscustomobject]@{
                provider = $provider
                error = $_.Exception.Message
            }
            continue
        }
    }
    return [pscustomobject]@{
        provider = $null
        failures = $failures
    }
}

function Get-SignalDefinitions {
    return @(
        [pscustomobject]@{ key = 'contribuyente_configuracion'; label = 'Contribuyente/configuracion'; pattern = 'contrib|empresa|usuario|user|config|producto|capacidad' },
        [pscustomobject]@{ key = 'formulario_22'; label = 'Formulario 22'; pattern = 'f22|formulario|pro26|codf22|nf22' },
        [pscustomobject]@{ key = 'f29_ppm'; label = 'F29/PPM'; pattern = 'f29|iva|ppm|retenc|mensual' },
        [pscustomobject]@{ key = 'regimen_14'; label = 'Regimenes 14'; pattern = '14a|14d3|14d8|14g|reg14|r14' },
        [pscustomobject]@{ key = 'rli'; label = 'RLI'; pattern = 'rli|renta_liquida|renta.*liquida|parrli|rlitotal|rlideta' },
        [pscustomobject]@{ key = 'cpt'; label = 'CPT'; pattern = 'cpt|capital.*propio|rz.*cpt|razon.*cpt' },
        [pscustomobject]@{ key = 'rai'; label = 'RAI'; pattern = 'rai|rentas.*afectas|monrai' },
        [pscustomobject]@{ key = 'sac'; label = 'SAC'; pattern = 'sac|credito|creditos' },
        [pscustomobject]@{ key = 'ddjj_certificados'; label = 'DDJJ/certificados'; pattern = 'ddjj|dj|coddj|cod_dj|certificado|cert' },
        [pscustomobject]@{ key = 'balance_contabilidad'; label = 'Balance/contabilidad'; pattern = 'balance|contab|cuenta|asiento|mayor|resultado' },
        [pscustomobject]@{ key = 'socios_retiros_dividendos'; label = 'Socios/retiros/dividendos'; pattern = 'socio|accionista|retiro|retiros|dividendo|dividendos' },
        [pscustomobject]@{ key = 'bienes_raices'; label = 'Bienes raices/arriendos'; pattern = 'bien|raiz|raices|bieraiz|propiedad|arriendo|contribucion' },
        [pscustomobject]@{ key = 'upload_export'; label = 'Upload/export'; pattern = 'upload|export|import|archivo|envio|respuesta|folio|sii' }
    )
}

function Get-SchemaSignalMatrix($tables) {
    $matrix = @()
    foreach ($definition in Get-SignalDefinitions) {
        $matchedTables = @()
        foreach ($table in $tables) {
            $columnText = (@($table.columns | ForEach-Object { $_.column_name }) -join ' ')
            $searchable = "$($table.table_name) $columnText"
            if ($searchable -match $definition.pattern) {
                $matchedTables += $table
            }
        }
        $matrix += [pscustomobject]@{
            key = $definition.key
            label = $definition.label
            table_count = $matchedTables.Count
            column_count = (@($matchedTables | ForEach-Object { $_.columns }).Count)
            sample_tables = @($matchedTables | ForEach-Object { Redact-SensitiveName $_.table_name } | Select-Object -First 12)
        }
    }
    return @($matrix)
}

function Get-PrimaryKeyMap($connection) {
    $map = @{}
    try {
        $schema = $connection.GetOleDbSchemaTable([System.Data.OleDb.OleDbSchemaGuid]::Primary_Keys, $null)
        foreach ($row in $schema.Rows) {
            $tableName = [string](Get-DataRowValue $row 'TABLE_NAME')
            $columnName = [string](Get-DataRowValue $row 'COLUMN_NAME')
            if ([string]::IsNullOrWhiteSpace($tableName) -or [string]::IsNullOrWhiteSpace($columnName)) {
                continue
            }
            if (-not $map.ContainsKey($tableName)) {
                $map[$tableName] = @()
            }
            $map[$tableName] += $columnName
        }
    }
    catch {
        return @{}
    }
    return $map
}

function Get-MdbSchema([string]$relativePath, [string]$copiedPath, [string[]]$providers) {
    $providerResult = Resolve-WorkingProvider $providers $copiedPath
    $provider = $providerResult.provider
    if ([string]::IsNullOrWhiteSpace($provider)) {
        return [pscustomobject]@{
            relative_path = $relativePath
            status = 'provider_unavailable_or_open_failed'
            provider = $null
            provider_failures = @($providerResult.failures)
            table_count = 0
            column_count = 0
            primary_key_count = 0
            tables = @()
            schema_signal_matrix = @()
        }
    }

    $connection = $null
    try {
        $connection = Open-OleDbConnection $provider $copiedPath
        $tableSchema = $connection.GetOleDbSchemaTable([System.Data.OleDb.OleDbSchemaGuid]::Tables, $null)
        $columnSchema = $connection.GetOleDbSchemaTable([System.Data.OleDb.OleDbSchemaGuid]::Columns, $null)
        $primaryKeyMap = Get-PrimaryKeyMap $connection

        $tableNames = @()
        foreach ($row in $tableSchema.Rows) {
            $tableName = [string](Get-DataRowValue $row 'TABLE_NAME')
            $tableType = [string](Get-DataRowValue $row 'TABLE_TYPE')
            if ([string]::IsNullOrWhiteSpace($tableName)) {
                continue
            }
            if ($tableType -ne 'TABLE') {
                continue
            }
            if ($tableName -like 'MSys*' -or $tableName -like '~*') {
                continue
            }
            $tableNames += $tableName
        }

        $columnsByTable = @{}
        foreach ($row in $columnSchema.Rows) {
            $tableName = [string](Get-DataRowValue $row 'TABLE_NAME')
            if ($tableNames -notcontains $tableName) {
                continue
            }
            $columnName = [string](Get-DataRowValue $row 'COLUMN_NAME')
            if ([string]::IsNullOrWhiteSpace($columnName)) {
                continue
            }
            if (-not $columnsByTable.ContainsKey($tableName)) {
                $columnsByTable[$tableName] = @()
            }
            $columnsByTable[$tableName] += [pscustomobject]@{
                column_name = $columnName
                data_type = Get-DataRowValue $row 'DATA_TYPE'
                ordinal_position = Get-DataRowValue $row 'ORDINAL_POSITION'
                is_nullable = Get-DataRowValue $row 'IS_NULLABLE'
                max_length = Get-DataRowValue $row 'CHARACTER_MAXIMUM_LENGTH'
                numeric_precision = Get-DataRowValue $row 'NUMERIC_PRECISION'
                numeric_scale = Get-DataRowValue $row 'NUMERIC_SCALE'
            }
        }

        $tables = @()
        foreach ($tableName in ($tableNames | Sort-Object)) {
            $columns = @()
            if ($columnsByTable.ContainsKey($tableName)) {
                $columns = @($columnsByTable[$tableName] | Sort-Object @{ Expression = { $_.ordinal_position }; Ascending = $true })
            }
            $pkColumns = @()
            if ($primaryKeyMap.ContainsKey($tableName)) {
                $pkColumns = @($primaryKeyMap[$tableName])
            }
            $tables += [pscustomobject]@{
                table_name = $tableName
                column_count = $columns.Count
                primary_key_columns = $pkColumns
                columns = $columns
            }
        }

        return [pscustomobject]@{
            relative_path = $relativePath
            status = 'schema_extracted_no_row_data'
            provider = $provider
            provider_failures = @($providerResult.failures)
            table_count = $tables.Count
            column_count = (@($tables | ForEach-Object { $_.columns }).Count)
            primary_key_count = (@($primaryKeyMap.Keys)).Count
            tables = $tables
            schema_signal_matrix = @(Get-SchemaSignalMatrix $tables)
        }
    }
    finally {
        if ($null -ne $connection) {
            $connection.Close()
            $connection.Dispose()
        }
    }
}

$repoRoot = Get-GitRoot
if ([string]::IsNullOrWhiteSpace($EdigRoot)) {
    $EdigRoot = Join-Path $repoRoot 'EDIG AT2026 SOFTWARE RENTA'
}
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $repoRoot 'local-evidence\edig-at2026-mdb-schema'
}

$EdigRoot = [IO.Path]::GetFullPath($EdigRoot)
$OutputDir = [IO.Path]::GetFullPath($OutputDir)
Assert-Condition (Test-Path -LiteralPath $EdigRoot -PathType Container) "No existe EdigRoot: $EdigRoot"
Assert-Condition ($EdigRoot -like '*EDIG AT2026 SOFTWARE RENTA*') 'EdigRoot debe apuntar a la carpeta EDIG AT2026 SOFTWARE RENTA.'

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$workDir = Join-Path $OutputDir ('work-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $workDir | Out-Null

$schemas = @()
try {
    foreach ($relativePath in Get-CoreMdbRelativePaths) {
        $sourcePath = Join-Path $EdigRoot $relativePath
        if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
            $schemas += [pscustomobject]@{
                relative_path = $relativePath
                status = 'missing'
                provider = $null
                provider_failures = @()
                table_count = 0
                column_count = 0
                primary_key_count = 0
                tables = @()
                schema_signal_matrix = @()
            }
            continue
        }

        $copyPath = Join-Path $workDir (ConvertTo-SafeFileName $relativePath)
        Copy-Item -LiteralPath $sourcePath -Destination $copyPath -Force
        $schemas += Get-MdbSchema $relativePath $copyPath $ProviderCandidates
    }
}
finally {
    if (-not $KeepTempCopies -and (Test-Path -LiteralPath $workDir)) {
        Remove-Item -LiteralPath $workDir -Recurse -Force
    }
}

$payload = [pscustomobject]@{
    generated_at = (Get-Date).ToString('s')
    mode = 'read_only_mdb_schema_from_temp_copies_no_rows_no_exe_execution'
    edig_root = $EdigRoot
    provider_candidates = $ProviderCandidates
    core_mdb_count = @($schemas).Count
    extracted_mdb_count = @($schemas | Where-Object { $_.status -eq 'schema_extracted_no_row_data' }).Count
    temp_copies_removed = -not $KeepTempCopies
    schemas = $schemas
}

$jsonPath = Join-Path $OutputDir 'edig-at2026-mdb-schema.json'
$mdPath = Join-Path $OutputDir 'edig-at2026-mdb-schema-summary.md'
$payload | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$summary = @()
$summary += '# EDIG AT2026 MDB schema summary'
$summary += ''
$summary += "Mode: $($payload.mode)"
$summary += "Core MDB count: $($payload.core_mdb_count)"
$summary += "Extracted MDB count: $($payload.extracted_mdb_count)"
$summary += "Temp copies removed: $($payload.temp_copies_removed)"
$summary += ''
$summary += '## Databases'
foreach ($schema in $payload.schemas) {
    $summary += "- $($schema.relative_path): status=$($schema.status), provider=$($schema.provider), tables=$($schema.table_count), columns=$($schema.column_count)"
    $topTables = @($schema.tables | Sort-Object column_count -Descending | Select-Object -First 10)
    foreach ($table in $topTables) {
        $columnSample = (@($table.columns | Select-Object -First 8 | ForEach-Object { Redact-SensitiveName $_.column_name }) -join ', ')
        $summary += "  - $(Redact-SensitiveName $table.table_name): columns=$($table.column_count); sample=$columnSample"
    }
}
$summary += ''
$summary += '## Schema signal matrix'
foreach ($schema in $payload.schemas) {
    $summary += "- $($schema.relative_path)"
    foreach ($signal in @($schema.schema_signal_matrix | Where-Object { $_.table_count -gt 0 })) {
        $samples = (@($signal.sample_tables | Select-Object -First 6) -join ', ')
        $summary += "  - $($signal.label): tables=$($signal.table_count), columns=$($signal.column_count), samples=$samples"
    }
}

$summary | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Host 'EDIG MDB schema inventory written:'
Write-Host "  $jsonPath"
Write-Host "  $mdPath"

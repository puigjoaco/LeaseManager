param(
    [string]$EdigRoot,
    [string]$OutputDir,
    [int]$MaxTokensPerFile = 120
)

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

function Get-LengthSum($items) {
    [int64]$total = 0
    foreach ($item in @($items)) {
        if ($null -ne $item -and $null -ne $item.PSObject.Properties['Length']) {
            $total += [int64]$item.Length
        }
    }
    return $total
}

function Get-ReadableTokens([string]$path, [int]$maxTokens) {
    $bytes = [IO.File]::ReadAllBytes($path)
    $texts = @(
        [Text.Encoding]::GetEncoding(1252).GetString($bytes),
        [Text.Encoding]::Unicode.GetString($bytes)
    )

    $allowed = 'tbl|Tables|RLI|RAI|SAC|CPT|F22|F29|DJ|PROY|Contab|Balance|Cuenta|Renta|Certificado|Contribuyente|Socio|Accionista|Retiro|Retiros|Dividendos|PPM|IVA|UTM|UF'
    $blocked = '^\d{7,8}-?[0-9Kk]$|@|password|passwd|clave|token|secret|licen|x509|cert'
    $tokens = New-Object System.Collections.Generic.List[string]

    foreach ($text in $texts) {
        foreach ($match in [regex]::Matches($text, '[A-Za-z0-9_#]{4,}')) {
            $value = $match.Value.Trim()
            if (($value -match $allowed) -and ($value -notmatch $blocked)) {
                $tokens.Add($value)
            }
        }
    }

    return @($tokens | Sort-Object -Unique | Select-Object -First $maxTokens)
}

function Get-HtmlTemplateInfo([string]$root) {
    $items = @()
    $htmlFiles = Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.Extension -ieq '.htm' }
    foreach ($file in $htmlFiles) {
        $text = [Text.Encoding]::GetEncoding(1252).GetString([IO.File]::ReadAllBytes($file.FullName))
        $f22Fields = @([regex]::Matches($text, '#fld(\d+)#') | ForEach-Object { $_.Groups[1].Value } | Sort-Object {[int]$_} -Unique)
        $f29Fields = @([regex]::Matches($text, '\$[A-Za-z0-9_]+\$') | ForEach-Object { $_.Value } | Sort-Object -Unique)
        if ($f22Fields.Count -gt 0 -or $f29Fields.Count -gt 0) {
            $items += [pscustomobject]@{
                path = ConvertTo-RelativePath $root $file.FullName
                f22_field_count = $f22Fields.Count
                f22_first_fields = @($f22Fields | Select-Object -First 20)
                f22_last_fields = @($f22Fields | Select-Object -Last 20)
                placeholder_count = $f29Fields.Count
                placeholder_sample = @($f29Fields | Select-Object -First 20)
            }
        }
    }
    return @($items)
}

$repoRoot = Get-GitRoot
if ([string]::IsNullOrWhiteSpace($EdigRoot)) {
    $EdigRoot = Join-Path $repoRoot 'EDIG AT2026 SOFTWARE RENTA'
}
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $repoRoot 'local-evidence\edig-at2026-static'
}

$EdigRoot = [IO.Path]::GetFullPath($EdigRoot)
$OutputDir = [IO.Path]::GetFullPath($OutputDir)
Assert-Condition (Test-Path -LiteralPath $EdigRoot -PathType Container) "No existe EdigRoot: $EdigRoot"
Assert-Condition ($EdigRoot -like '*EDIG AT2026 SOFTWARE RENTA*') 'EdigRoot debe apuntar a la carpeta EDIG AT2026 SOFTWARE RENTA.'

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$files = @(Get-ChildItem -LiteralPath $EdigRoot -Recurse -File -Force)
$directories = @(Get-ChildItem -LiteralPath $EdigRoot -Recurse -Directory -Force)

$extensions = @(
    $files |
        Group-Object Extension |
        Sort-Object @{ Expression = { Get-LengthSum $_.Group }; Descending = $true } |
        ForEach-Object {
            [pscustomobject]@{
                extension = if ([string]::IsNullOrWhiteSpace($_.Name)) { '<none>' } else { $_.Name }
                count = $_.Count
                mb = [math]::Round(((Get-LengthSum $_.Group) / 1MB), 2)
            }
        }
)

$folders = @(
    Get-ChildItem -LiteralPath $EdigRoot -Directory -Force | ForEach-Object {
        $childFiles = @(Get-ChildItem -LiteralPath $_.FullName -Recurse -File -Force)
        [pscustomobject]@{
            folder = $_.Name
            files = $childFiles.Count
            mb = [math]::Round(((Get-LengthSum $childFiles) / 1MB), 2)
        }
    } | Sort-Object mb -Descending
)

$executables = @(
    Get-ChildItem -LiteralPath $EdigRoot -Recurse -File |
        Where-Object { $_.Extension -ieq '.exe' -or $_.Extension -ieq '.dll' } |
        ForEach-Object {
        [pscustomobject]@{
            path = ConvertTo-RelativePath $EdigRoot $_.FullName
            product = $_.VersionInfo.ProductName
            file_version = $_.VersionInfo.FileVersion
            company = $_.VersionInfo.CompanyName
            description = $_.VersionInfo.FileDescription
            kb = [math]::Round($_.Length / 1KB, 1)
        }
    } | Sort-Object path
)

$taxCoreMdbPaths = @(
    'central\comun.mdb',
    'central\prtregat21.mdb',
    'central\r14para26.mdb',
    'datos\canova.mdb',
    'datos\f29lgh.mdb',
    'datos\pro26.mdb',
    'datos\reg14.mdb'
)

$mdbFiles = @(
    Get-ChildItem -LiteralPath $EdigRoot -Recurse -File |
        Where-Object { $_.Extension -ieq '.mdb' } |
        ForEach-Object {
        $relativeMdbPath = (ConvertTo-RelativePath $EdigRoot $_.FullName).ToLowerInvariant()
        $isTaxCore = $taxCoreMdbPaths -contains $relativeMdbPath
        [pscustomobject]@{
            path = ConvertTo-RelativePath $EdigRoot $_.FullName
            kb = [math]::Round($_.Length / 1KB, 1)
            structural_tokens = if ($isTaxCore) {
                @(Get-ReadableTokens $_.FullName $MaxTokensPerFile)
            } else {
                @('skipped_non_tax_core_or_potential_user_license_data')
            }
        }
    } | Sort-Object path
)

$reportFiles = @(
    Get-ChildItem -LiteralPath $EdigRoot -Recurse -File |
        Where-Object { $_.Extension -ieq '.rpt' } |
        ForEach-Object {
        [pscustomobject]@{
            path = ConvertTo-RelativePath $EdigRoot $_.FullName
            kb = [math]::Round($_.Length / 1KB, 1)
        }
    } | Sort-Object path
)

$payload = [pscustomobject]@{
    generated_at = (Get-Date).ToString('s')
    mode = 'read_only_static_inventory_no_exe_execution'
    edig_root = $EdigRoot
    totals = [pscustomobject]@{
        files = $files.Count
        directories = $directories.Count
        mb = [math]::Round(((Get-LengthSum $files) / 1MB), 2)
    }
    extensions = $extensions
    folders = $folders
    executables = $executables
    mdb_structural_tokens = $mdbFiles
    html_templates = @(Get-HtmlTemplateInfo $EdigRoot)
    report_files = $reportFiles
}

$jsonPath = Join-Path $OutputDir 'edig-at2026-static-inventory.json'
$mdPath = Join-Path $OutputDir 'edig-at2026-static-summary.md'
$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$summary = @()
$summary += '# EDIG AT2026 static summary'
$summary += ''
$summary += "Mode: $($payload.mode)"
$summary += "Files: $($payload.totals.files)"
$summary += "Directories: $($payload.totals.directories)"
$summary += "Total MB: $($payload.totals.mb)"
$summary += ''
$summary += '## Top folders'
$payload.folders | Select-Object -First 12 | ForEach-Object {
    $summary += "- $($_.folder): $($_.files) files, $($_.mb) MB"
}
$summary += ''
$summary += '## Executable products'
$payload.executables | Where-Object { $_.product -or $_.description } | Select-Object -First 40 | ForEach-Object {
    $summary += "- $($_.path): $($_.product) $($_.file_version)"
}
$summary += ''
$summary += '## HTML templates'
$payload.html_templates | ForEach-Object {
    $summary += "- $($_.path): f22_fields=$($_.f22_field_count), placeholders=$($_.placeholder_count)"
}
$summary += ''
$summary += '## MDB structural tokens'
$payload.mdb_structural_tokens | ForEach-Object {
    $sample = ($_.structural_tokens | Select-Object -First 30) -join ', '
    $summary += "- $($_.path): $sample"
}

$summary | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Host "EDIG static inventory written:"
Write-Host "  $jsonPath"
Write-Host "  $mdPath"

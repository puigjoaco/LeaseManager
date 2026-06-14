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

function Get-TopLevelSegment([string]$relativePath) {
    $parts = $relativePath -split '[\\/]'
    if ($parts.Count -eq 0) {
        return ''
    }
    return $parts[0].ToLowerInvariant()
}

function Test-SensitiveRelativePath([string]$relativePath) {
    $sensitiveRoots = @('contrib', 'licencias', 'respuesta', 'upload')
    return $sensitiveRoots -contains (Get-TopLevelSegment $relativePath)
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

    $allowed = 'tbl|Tables|RLI|RAI|SAC|CPT|F22|F29|DJ|PROY|Contab|Balance|Cuenta|Renta|Certificado|Contribuyente|Socio|Accionista|Retiro|Retiros|Dividendos|PPM|IVA|UTM|UF|Folio|Upload|Import|Export|Bien|BieRaiz|Raiz|Raices|Propiedad|Arriendo|Contribucion|Contribuciones'
    $blocked = '^\d{7,8}-?[0-9Kk]$|@|password|passwd|clave|token|secret|licen|x509|privatekey|pfx'
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

function Get-SignalDefinitions {
    return @(
        [pscustomobject]@{
            key = 'administracion_contribuyente'
            label = 'Administracion, contribuyentes y capacidades'
            pattern = 'admin|comun|contribuyente|empresa|usuario|user|producto|licen|capacidad'
            interpretation = 'Maestros y permisos que definen que modulo tributario puede operar por contribuyente.'
            lease_manager_target = 'Empresa, ConfiguracionFiscalEmpresa, capacidades SII, responsables y auditoria.'
        },
        [pscustomobject]@{
            key = 'formulario_22'
            label = 'Formulario 22 anual'
            pattern = 'f22|formulario\s*22|gnpro|pro26|plantillapro|compactopro|#fld'
            interpretation = 'Preparacion, render, validacion y export del F22 anual.'
            lease_manager_target = 'F22PreparacionAnual, preview, validaciones por codigo y export certificable.'
        },
        [pscustomobject]@{
            key = 'f29_ppm_mensual'
            label = 'F29, IVA y PPM mensual'
            pattern = 'f29|iva|ppm|ivastd|plantillaf29|retencion|mensual'
            interpretation = 'Obligaciones mensuales que alimentan creditos, PPM y consistencia anual.'
            lease_manager_target = 'F29PreparacionMensual, cierres mensuales aprobados y base anual.'
        },
        [pscustomobject]@{
            key = 'regimen_14a'
            label = 'Regimen 14A'
            pattern = '14a|r14a|er14a'
            interpretation = 'Motor especifico para regimen 14A y sus registros empresariales.'
            lease_manager_target = 'TaxYearRuleSet.Regimen14A, si existe fuente oficial/experta vigente.'
        },
        [pscustomobject]@{
            key = 'regimen_14d3'
            label = 'Regimen 14D3'
            pattern = '14d3|d326|r14d3|er14d3'
            interpretation = 'Motor especifico ProPyme general.'
            lease_manager_target = 'TaxYearRuleSet.Regimen14D3.'
        },
        [pscustomobject]@{
            key = 'regimen_14d8'
            label = 'Regimen 14D8'
            pattern = '14d8|d826|r14d8|er14d8'
            interpretation = 'Motor especifico ProPyme transparente.'
            lease_manager_target = 'TaxYearRuleSet.Regimen14D8.'
        },
        [pscustomobject]@{
            key = 'regimen_14g'
            label = 'Regimen 14G'
            pattern = '14g|r14g|er14g'
            interpretation = 'Motor para organizaciones sin fines de lucro u otro regimen especializado.'
            lease_manager_target = 'TaxYearRuleSet.Regimen14G, fuera de v1 salvo ADR/gate.'
        },
        [pscustomobject]@{
            key = 'rli'
            label = 'RLI'
            pattern = 'rli|renta\s*liquida|rlitotal|rlideta|itemrli'
            interpretation = 'Construccion de renta liquida imponible antes de mapear F22.'
            lease_manager_target = 'AnnualTaxNormalizer.RLI con ajustes, fuentes y respaldo.'
        },
        [pscustomobject]@{
            key = 'cpt'
            label = 'CPT'
            pattern = 'cpt|capital\s*propio|rz?cpt|ctotal'
            interpretation = 'Capital propio tributario calculado desde balance, clasificacion y ajustes.'
            lease_manager_target = 'AnnualTaxNormalizer.CPT y mapping plan de cuentas -> DJ/F22.'
        },
        [pscustomobject]@{
            key = 'rai'
            label = 'RAI'
            pattern = 'rai|rentas\s*afectas'
            interpretation = 'Registro de rentas afectas y consistencia con RLI/CPT/retiros.'
            lease_manager_target = 'AnnualTaxNormalizer.RAI y registros empresariales.'
        },
        [pscustomobject]@{
            key = 'sac'
            label = 'SAC'
            pattern = 'sac|credito|creditos'
            interpretation = 'Saldos acumulados de creditos y arrastres tributarios.'
            lease_manager_target = 'AnnualTaxNormalizer.SAC con fuente mensual/anual trazada.'
        },
        [pscustomobject]@{
            key = 'ddjj'
            label = 'DDJJ'
            pattern = 'ddjj|dj|cod[d]?j|declaracion\s*jurada|certificado'
            interpretation = 'Declaraciones juradas y certificados como capa previa o paralela al F22.'
            lease_manager_target = 'DDJJPreparacionAnual, certificados y media matrix SII.'
        },
        [pscustomobject]@{
            key = 'balance_contabilidad'
            label = 'Balance y contabilidad'
            pattern = 'balance|contab|cuenta|cuentas|ledger|asiento|mayor|resultado'
            interpretation = 'Entrada contable normalizada antes de reglas tributarias.'
            lease_manager_target = 'CierreMensualContable aprobado, ledger balanceado y plan de cuentas fiscal.'
        },
        [pscustomobject]@{
            key = 'bienes_raices'
            label = 'Bienes raices y arriendos'
            pattern = 'bien|raiz|raices|arriendo|propiedad|contribucion|contribuciones|bie[ _]?raiz'
            interpretation = 'Datos de inmuebles, arriendos y contribuciones que alimentan renta anual.'
            lease_manager_target = 'Propiedad, Contrato, pagos, contribuciones y mapping F22/DDJJ.'
        },
        [pscustomobject]@{
            key = 'reportes_respaldo'
            label = 'Reportes y respaldos'
            pattern = '\.rpt|reporte|rep_|respaldo|pdf|html|plantilla'
            interpretation = 'Evidencia generada para revision tributaria y auditoria.'
            lease_manager_target = 'AnnualTaxDossier, PDF canonico, HTML preview y hash de evidencia.'
        },
        [pscustomobject]@{
            key = 'upload_export'
            label = 'Upload/export y respuesta'
            pattern = 'upload|export|import|respuesta|envio|archivo|validacion|folio|sii'
            interpretation = 'Generacion de archivo, validacion, envio o respuesta externa.'
            lease_manager_target = 'AnnualTaxExport bajo gate SII, responsable y autorizacion explicita.'
        },
        [pscustomobject]@{
            key = 'conectividad_auxiliar'
            label = 'Conectividad auxiliar'
            pattern = 'ws|wapp|webservice|connect|dte|utm|uf|folios'
            interpretation = 'Servicios auxiliares; no prueba API REST publica para F22.'
            lease_manager_target = 'Capacidades SII separadas por gate e integracion controlada.'
        }
    )
}

function Get-ArtifactRows($root, $files, $executables, $mdbFiles, $htmlTemplates, $reportFiles) {
    $rows = @()

    foreach ($file in $files) {
        $relativePath = ConvertTo-RelativePath $root $file.FullName
        if (Test-SensitiveRelativePath $relativePath) {
            continue
        }
        $rows += [pscustomobject]@{
            kind = 'file_name'
            path = $relativePath
            searchable = "$relativePath $($file.Extension)"
        }
    }

    foreach ($exe in $executables) {
        $rows += [pscustomobject]@{
            kind = 'executable_metadata'
            path = $exe.path
            searchable = "$($exe.path) $($exe.product) $($exe.description)"
        }
    }

    foreach ($mdb in $mdbFiles) {
        $tokens = ($mdb.structural_tokens -join ' ')
        $rows += [pscustomobject]@{
            kind = 'mdb_structural_tokens'
            path = $mdb.path
            searchable = "$($mdb.path) $tokens"
        }
    }

    foreach ($template in $htmlTemplates) {
        $rows += [pscustomobject]@{
            kind = 'html_template'
            path = $template.path
            searchable = "$($template.path) #fld $($template.placeholder_sample -join ' ')"
        }
    }

    foreach ($report in $reportFiles) {
        $rows += [pscustomobject]@{
            kind = 'report'
            path = $report.path
            searchable = $report.path
        }
    }

    return @($rows)
}

function Get-FunctionalSignalMatrix($artifactRows) {
    $matrix = @()
    foreach ($definition in Get-SignalDefinitions) {
        $matches = @(
            $artifactRows | Where-Object {
                $_.searchable -match $definition.pattern
            }
        )
        $matrix += [pscustomobject]@{
            key = $definition.key
            label = $definition.label
            evidence_count = $matches.Count
            artifact_kinds = @($matches | Group-Object kind | Sort-Object Count -Descending | ForEach-Object { "$($_.Name):$($_.Count)" })
            sample_paths = @($matches | Select-Object -ExpandProperty path -Unique | Select-Object -First 18)
            interpretation = $definition.interpretation
            lease_manager_target = $definition.lease_manager_target
        }
    }
    return @($matrix)
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
        $isSensitive = Test-SensitiveRelativePath $relativeMdbPath
        [pscustomobject]@{
            path = if ($isSensitive) {
                '<redacted_sensitive_root>/' + $_.Name
            } else {
                ConvertTo-RelativePath $EdigRoot $_.FullName
            }
            kb = [math]::Round($_.Length / 1KB, 1)
            structural_tokens = if ($isTaxCore) {
                @(Get-ReadableTokens $_.FullName $MaxTokensPerFile)
            } elseif ($isSensitive) {
                @('skipped_sensitive_user_license_or_upload_data')
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

$artifactRows = Get-ArtifactRows $EdigRoot $files $payload.executables $payload.mdb_structural_tokens $payload.html_templates $payload.report_files
$payload | Add-Member -MemberType NoteProperty -Name functional_signal_matrix -Value @(Get-FunctionalSignalMatrix $artifactRows)

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
$summary += ''
$summary += '## Functional signal matrix'
$payload.functional_signal_matrix | ForEach-Object {
    $samples = ($_.sample_paths | Select-Object -First 6) -join '; '
    $kinds = ($_.artifact_kinds | Select-Object -First 5) -join ', '
    $summary += "- $($_.label): evidence=$($_.evidence_count), kinds=$kinds"
    if (-not [string]::IsNullOrWhiteSpace($samples)) {
        $summary += "  samples: $samples"
    }
    $summary += "  LeaseManager: $($_.lease_manager_target)"
}

$summary | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Host "EDIG static inventory written:"
Write-Host "  $jsonPath"
Write-Host "  $mdPath"

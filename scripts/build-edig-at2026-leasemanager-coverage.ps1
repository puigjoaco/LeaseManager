param(
    [string]$StaticInventoryPath,
    [string]$MdbSchemaPath,
    [string]$OutputDir
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

function Resolve-PathOrThrow([string]$path, [string]$label) {
    Assert-Condition (Test-Path -LiteralPath $path -PathType Leaf) "No existe ${label}: $path"
    return [IO.Path]::GetFullPath($path)
}

function Assert-OutputUnderLocalEvidence([string]$repoRoot, [string]$path) {
    $full = [IO.Path]::GetFullPath($path)
    $allowed = [IO.Path]::GetFullPath((Join-Path $repoRoot 'local-evidence'))
    Assert-Condition ($full.StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase)) `
        'OutputDir debe quedar dentro de local-evidence/ para no versionar evidencia EDIG.'
}

function Get-StaticSignalCount($staticInventory, [string[]]$keys) {
    $total = 0
    foreach ($key in $keys) {
        $signal = @($staticInventory.functional_signal_matrix | Where-Object { $_.key -eq $key } | Select-Object -First 1)
        if ($signal.Count -gt 0) {
            $total += [int]$signal[0].evidence_count
        }
    }
    return $total
}

function Get-SchemaSignalCount($schemaInventory, [string[]]$keys) {
    $tables = 0
    $columns = 0
    foreach ($schema in @($schemaInventory.schemas)) {
        foreach ($signal in @($schema.schema_signal_matrix)) {
            if ($keys -contains $signal.key) {
                $tables += [int]$signal.table_count
                $columns += [int]$signal.column_count
            }
        }
    }
    return [pscustomobject]@{
        tables = $tables
        columns = $columns
    }
}

function Test-RepoToken([string]$repoRoot, [string]$token) {
    $matches = & git -C $repoRoot grep -n --fixed-strings $token -- backend docs 2>$null
    return ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace(($matches | Out-String)))
}

function Get-RequirementDefinitions {
    return @(
        [pscustomobject]@{
            key = 'contribuyente_configuracion'
            label = 'Contribuyente, regimen y capacidades'
            static_keys = @('administracion_contribuyente')
            schema_keys = @('contribuyente_configuracion')
            lease_manager_components = @('Empresa', 'ConfiguracionFiscalEmpresa', 'CapacidadSII', 'TaxYearRuleSet')
            current_status = 'implemented_local_foundation'
            next_action = 'Mantener gate de configuracion fiscal y responsable; no habilita SII real.'
        },
        [pscustomobject]@{
            key = 'f29_ppm_monthly'
            label = 'F29, IVA y PPM mensual como insumo anual'
            static_keys = @('f29_ppm_mensual')
            schema_keys = @('f29_ppm')
            lease_manager_components = @('F29PreparacionMensual', 'MonthlyTaxFact', 'AnnualTaxSourceBundle')
            current_status = 'implemented_preparatory'
            next_action = 'Conectar fuentes oficiales/experto para PPM y F29 finales antes de cierre tributario.'
        },
        [pscustomobject]@{
            key = 'tax_year_rules'
            label = 'Parametria AT/regimen'
            static_keys = @('regimen_14a', 'regimen_14d3', 'regimen_14d8', 'regimen_14g')
            schema_keys = @('regimen_14')
            lease_manager_components = @('TaxYearRuleSet', 'TaxCodeMapping')
            current_status = 'implemented_shell_blocked_final_rules'
            next_action = 'Cargar reglas AT solo desde fuente SII/experta aprobada; EDIG no es fuente normativa.'
        },
        [pscustomobject]@{
            key = 'rli_cpt'
            label = 'RLI y CPT'
            static_keys = @('rli', 'cpt', 'balance_contabilidad')
            schema_keys = @('rli', 'cpt', 'balance_contabilidad')
            lease_manager_components = @('AnnualTaxWorkbook', 'AnnualTaxWorkbookLine')
            current_status = 'implemented_skeleton'
            next_action = 'Completar mapeo plan de cuentas -> RLI/CPT con DJ/F22 oficial o revision experta.'
        },
        [pscustomobject]@{
            key = 'enterprise_registers'
            label = 'RAI, SAC, retiros y dividendos'
            static_keys = @('rai', 'sac')
            schema_keys = @('rai', 'sac', 'socios_retiros_dividendos')
            lease_manager_components = @('AnnualEnterpriseRegisterSet', 'AnnualEnterpriseRegisterMovement')
            current_status = 'implemented_preparatory'
            next_action = 'Requiere saldos historicos y decision experta antes de declarar cierre fiscal.'
        },
        [pscustomobject]@{
            key = 'real_estate'
            label = 'Bienes raices, arriendos y contribuciones'
            static_keys = @('bienes_raices')
            schema_keys = @('bienes_raices')
            lease_manager_components = @('AnnualRealEstateSection', 'AnnualRealEstateItem')
            current_status = 'implemented_with_source_gap'
            next_action = 'Cargar contribuciones/codigos F22 desde fuente oficial/experta; mantener warning hasta entonces.'
        },
        [pscustomobject]@{
            key = 'ddjj_f22_matrix'
            label = 'Matriz DDJJ/F22'
            static_keys = @('ddjj', 'formulario_22')
            schema_keys = @('ddjj_certificados', 'formulario_22')
            lease_manager_components = @('AnnualTaxArtifactMatrix', 'DDJJPreparacionAnual', 'F22PreparacionAnual')
            current_status = 'implemented_review_matrix'
            next_action = 'No marcar medio/formato oficial sin evidencia SII vigente y responsable.'
        },
        [pscustomobject]@{
            key = 'dossier'
            label = 'Dossier y respaldos'
            static_keys = @('reportes_respaldo')
            schema_keys = @()
            lease_manager_components = @('AnnualTaxDossier', 'DocumentoEmitido', 'PlantillaDocumental')
            current_status = 'implemented_review_package'
            next_action = 'Mantener dossier como evidencia revisable; no como decision tributaria final.'
        },
        [pscustomobject]@{
            key = 'export_upload'
            label = 'Export/upload/presentacion'
            static_keys = @('upload_export', 'conectividad_auxiliar')
            schema_keys = @('upload_export')
            lease_manager_components = @('AnnualTaxExport', 'CapacidadSII')
            current_status = 'implemented_local_export_blocked_external'
            next_action = 'Presentacion final sigue bloqueada hasta formato/certificacion SII, autorizacion y responsable.'
        }
    )
}

$repoRoot = Get-GitRoot
if ([string]::IsNullOrWhiteSpace($StaticInventoryPath)) {
    $StaticInventoryPath = Join-Path $repoRoot 'local-evidence\edig-at2026-static\edig-at2026-static-inventory.json'
}
if ([string]::IsNullOrWhiteSpace($MdbSchemaPath)) {
    $MdbSchemaPath = Join-Path $repoRoot 'local-evidence\edig-at2026-mdb-schema\edig-at2026-mdb-schema.json'
}
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $repoRoot 'local-evidence\edig-at2026-coverage'
}

$StaticInventoryPath = Resolve-PathOrThrow $StaticInventoryPath 'StaticInventoryPath'
$MdbSchemaPath = Resolve-PathOrThrow $MdbSchemaPath 'MdbSchemaPath'
$OutputDir = [IO.Path]::GetFullPath($OutputDir)
Assert-OutputUnderLocalEvidence $repoRoot $OutputDir
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$staticInventory = Get-Content -LiteralPath $StaticInventoryPath -Raw | ConvertFrom-Json
$schemaInventory = Get-Content -LiteralPath $MdbSchemaPath -Raw | ConvertFrom-Json

$requirements = @()
foreach ($definition in Get-RequirementDefinitions) {
    $schemaSignal = Get-SchemaSignalCount $schemaInventory $definition.schema_keys
    $components = @()
    foreach ($component in $definition.lease_manager_components) {
        $components += [pscustomobject]@{
            name = $component
            observed_in_repo = Test-RepoToken $repoRoot $component
        }
    }

    $requirements += [pscustomobject]@{
        key = $definition.key
        label = $definition.label
        edig_static_evidence_count = Get-StaticSignalCount $staticInventory $definition.static_keys
        edig_schema_table_count = $schemaSignal.tables
        edig_schema_column_count = $schemaSignal.columns
        lease_manager_components = $components
        lease_manager_components_observed = @($components | Where-Object { $_.observed_in_repo }).Count
        current_status = $definition.current_status
        next_action = $definition.next_action
    }
}

$payload = [pscustomobject]@{
    generated_at = (Get-Date).ToString('s')
    mode = 'safe_coverage_from_sanitized_inventories_no_edig_content_no_rows'
    source_static_inventory = $StaticInventoryPath
    source_mdb_schema = $MdbSchemaPath
    totals = [pscustomobject]@{
        edig_files = $staticInventory.totals.files
        edig_directories = $staticInventory.totals.directories
        edig_mb = $staticInventory.totals.mb
        functional_signals = @($staticInventory.functional_signal_matrix).Count
        core_mdb_count = $schemaInventory.core_mdb_count
        extracted_mdb_count = $schemaInventory.extracted_mdb_count
        schema_tables = (@($schemaInventory.schemas) | Measure-Object table_count -Sum).Sum
        schema_columns = (@($schemaInventory.schemas) | Measure-Object column_count -Sum).Sum
    }
    requirements = $requirements
}

$jsonPath = Join-Path $OutputDir 'edig-at2026-lease-manager-coverage.json'
$mdPath = Join-Path $OutputDir 'edig-at2026-lease-manager-coverage.md'
$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$summary = @()
$summary += '# EDIG AT2026 -> LeaseManager coverage'
$summary += ''
$summary += "Mode: $($payload.mode)"
$summary += "Static files: $($payload.totals.edig_files)"
$summary += "Functional signals: $($payload.totals.functional_signals)"
$summary += "Core MDB extracted: $($payload.totals.extracted_mdb_count)/$($payload.totals.core_mdb_count)"
$summary += "Schema tables/columns: $($payload.totals.schema_tables)/$($payload.totals.schema_columns)"
$summary += ''
$summary += '| Area | EDIG signals | MDB tables | LeaseManager components observed | Status | Next action |'
$summary += '| --- | ---: | ---: | ---: | --- | --- |'
foreach ($row in $requirements) {
    $summary += "| $($row.label) | $($row.edig_static_evidence_count) | $($row.edig_schema_table_count) | $($row.lease_manager_components_observed)/$(@($row.lease_manager_components).Count) | $($row.current_status) | $($row.next_action) |"
}
$summary += ''
$summary += 'Notes: this report is derived from sanitized local-evidence inventories. It does not include EDIG binaries, code, formulas, rows, RUTs, licenses, credentials, certificates or upload artifacts.'
$summary | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Host 'EDIG -> LeaseManager coverage written:'
Write-Host "  $jsonPath"
Write-Host "  $mdPath"

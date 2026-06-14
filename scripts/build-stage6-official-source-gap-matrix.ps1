param(
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

function Assert-OutputUnderLocalEvidence([string]$repoRoot, [string]$path) {
    $full = [IO.Path]::GetFullPath($path)
    $allowed = [IO.Path]::GetFullPath((Join-Path $repoRoot 'local-evidence'))
    Assert-Condition ($full.StartsWith($allowed, [StringComparison]::OrdinalIgnoreCase)) `
        'OutputDir debe quedar dentro de local-evidence/ para no versionar matriz operativa de fuentes.'
}

function Test-OfficialSourceUrl([string]$url) {
    if ([string]::IsNullOrWhiteSpace($url)) {
        return $true
    }
    return $url -match '^https://(www\.sii\.cl|www4\.sii\.cl|zeus\.sii\.cl|api\.sii\.cl)/'
}

function Get-SourceGapDefinitions {
    return @(
        [pscustomobject]@{
            key = 'dte_technical_services'
            capability = 'DTE y documentos electronicos'
            official_source = 'Instructivo tecnico DTE y servicios para factura electronica de mercado'
            source_url = 'https://www.sii.cl/ayudas/ayudas_por_servicios/2004-instructivo-2007.html'
            evidence_reading = 'SII publica web services/documentacion tecnica DTE y exige certificado digital para opciones identificadas.'
            lease_manager_boundary = 'Integracion tecnica posible bajo gate DTE, certificado/CAF seguro, auditoria y rollback.'
            current_status = 'external_gate_required'
            next_safe_action = 'Mantener DTE separado de renta anual; no usar como prueba de API F22/DDJJ.'
        },
        [pscustomobject]@{
            key = 'f29_upload_certification'
            capability = 'F29 mensual'
            official_source = 'Proceso de certificacion para declarar F29 por software'
            source_url = 'https://www.sii.cl/ayudas/ayudas_por_servicios/2055-procesocertificacion-2056.html'
            evidence_reading = 'SII describe archivo/upload, certificacion de formato, validaciones y responsabilidad de la casa de software.'
            lease_manager_boundary = 'Preparar hechos mensuales y paquete revisable; presentacion F29 queda bajo gate externo.'
            current_status = 'preparation_allowed_submission_blocked'
            next_safe_action = 'Usar F29 como fuente anual trazable solo con evidencia/control autorizado.'
        },
        [pscustomobject]@{
            key = 'ddjj_media_2026'
            capability = 'DDJJ Renta 2026'
            official_source = 'Medios para declaraciones juradas de Renta 2026'
            source_url = 'https://www.sii.cl/ayudas/ayudas_por_servicios/2120-medios_dj_renta_2026-2171.html'
            evidence_reading = 'SII publica por formulario los medios disponibles: formulario electronico, transferencia, upload, software comercial y asistentes.'
            lease_manager_boundary = 'AnnualTaxArtifactMatrix puede clasificar medio revisable; no presentar sin matriz oficial por formulario y responsable.'
            current_status = 'media_matrix_required'
            next_safe_action = 'Construir matriz DDJJ aplicable a LeaseManager desde esta fuente y revision experta.'
        },
        [pscustomobject]@{
            key = 'dj1847_balance_rli_cpt'
            capability = 'DJ1847, balance, RLI y CPT'
            official_source = 'Instrucciones SII DJ1847 AT2026'
            source_url = 'https://www.sii.cl/ayudas/ayudas_por_servicios/renta/2026/instrucciones_dj1847.pdf'
            evidence_reading = 'La fuente oficial exige balance de ocho columnas, clasificacion de cuentas, ajustes RLI y valor tributario de activos/pasivos para CPT.'
            lease_manager_boundary = 'Mapping plan de cuentas -> RLI/CPT/DJ1847 puede prepararse solo con fuente oficial/experta; no por EDIG ni inferencia libre.'
            current_status = 'official_mapping_required'
            next_safe_action = 'Abrir paquete de mapping DJ1847 solo con codigos/fuente/responsable no sensibles.'
        },
        [pscustomobject]@{
            key = 'f22_certification_2026'
            capability = 'F22 Renta anual'
            official_source = 'Certificacion AT2026 para software que genera archivos Formulario 22'
            source_url = 'https://www.sii.cl/noticias/2026/060226noti02pcr.htm'
            evidence_reading = 'SII invita a certificarse para generar archivos F22 AT2026; el proceso acredita recepcion, no certifica contenido ni consistencia tributaria.'
            lease_manager_boundary = 'AnnualTaxExport permanece como preview local con official_format=false, sii_submission=false y final_tax_calculation=false.'
            current_status = 'local_export_only'
            next_safe_action = 'No convertir a formato oficial ni presentar hasta certificacion/formato, autorizacion y responsable.'
        },
        [pscustomobject]@{
            key = 'f22_instructions_2026'
            capability = 'Instrucciones operativas F22 2026'
            official_source = 'Suplemento Tributario y Guia Renta 2026'
            source_url = 'https://www.sii.cl/servicios_online/renta/guia_trib_suplemento_2026.html'
            evidence_reading = 'SII publica instrucciones operativas, codigos, ejemplos y actualizaciones del F22 AT2026.'
            lease_manager_boundary = 'TaxCodeMapping y warnings pueden apuntar a instrucciones oficiales; la decision final requiere revision tributaria.'
            current_status = 'review_source_required'
            next_safe_action = 'Cargar referencias por codigo solo como source_ref no sensible, nunca como calculo autonomo final.'
        },
        [pscustomobject]@{
            key = 'real_estate_contributions'
            capability = 'Bienes raices, arriendos y contribuciones'
            official_source = 'Fuente oficial/experta pendiente'
            source_url = ''
            evidence_reading = 'LeaseManager tiene contratos, distribuciones y propiedades; faltan respaldo oficial/experto para contribuciones/codigos F22 aplicables.'
            lease_manager_boundary = 'AnnualRealEstateItem conserva contribuciones como not_loaded_v1 o warning hasta fuente aprobada.'
            current_status = 'source_gap'
            next_safe_action = 'No cerrar warning inmobiliario sin fuente SII/experta y responsable.'
        },
        [pscustomobject]@{
            key = 'browser_assisted_submission'
            capability = 'Automatizacion por navegador SII'
            official_source = 'Sin API REST publica F22/DDJJ identificada en fuentes verificadas'
            source_url = ''
            evidence_reading = 'Las fuentes revisadas hablan de web services DTE y de archivo/upload/certificacion para F29/F22/DDJJ; no prueban API REST general para presentar renta.'
            lease_manager_boundary = 'Solo puede ser asistencia supervisada, reversible y con usuario responsable; no forma parte del core automatico v1.'
            current_status = 'last_resort_supervised'
            next_safe_action = 'Preferir dossier/export controlado; evaluar browser solo con runbook, datos controlados y autorizacion explicita.'
        }
    )
}

$repoRoot = Get-GitRoot
if ([string]::IsNullOrWhiteSpace($OutputDir)) {
    $OutputDir = Join-Path $repoRoot 'local-evidence\stage6\official-source-gaps'
}

$OutputDir = [IO.Path]::GetFullPath($OutputDir)
Assert-OutputUnderLocalEvidence $repoRoot $OutputDir
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$requirements = @()
foreach ($definition in Get-SourceGapDefinitions) {
    Assert-Condition (Test-OfficialSourceUrl $definition.source_url) "Fuente no permitida para $($definition.key): $($definition.source_url)"
    $requirements += $definition
}

$payload = [pscustomobject]@{
    generated_at = (Get-Date).ToString('s')
    mode = 'stage6_official_source_gap_matrix_no_network_no_credentials'
    source_policy = 'Only official SII URLs or explicit pending expert/source gaps; no secrets, no SII session, no browser automation.'
    requirements = $requirements
}

$jsonPath = Join-Path $OutputDir 'stage6-official-source-gaps.json'
$mdPath = Join-Path $OutputDir 'stage6-official-source-gaps.md'
$payload | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$summary = @()
$summary += '# Stage 6 official source gaps'
$summary += ''
$summary += "Mode: $($payload.mode)"
$summary += ''
$summary += '| Capability | Status | LeaseManager boundary | Next safe action | Source |'
$summary += '| --- | --- | --- | --- | --- |'
foreach ($row in $requirements) {
    $source = if ([string]::IsNullOrWhiteSpace($row.source_url)) { $row.official_source } else { "$($row.official_source) ($($row.source_url))" }
    $summary += "| $($row.capability) | $($row.current_status) | $($row.lease_manager_boundary) | $($row.next_safe_action) | $source |"
}
$summary += ''
$summary += 'This matrix is generated from static definitions and official-source references. It does not call SII, execute EDIG, use credentials, read .env, inspect real data or produce official tax submissions.'
$summary | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Host 'Stage 6 official source gap matrix written:'
Write-Host "  $jsonPath"
Write-Host "  $mdPath"

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEGACY_ROOT = PROJECT_ROOT.parent
OUTPUT_DIR = PROJECT_ROOT / 'migration' / 'inventory'

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from migration.contracts import (  # noqa: E402
    LegacyIntegrationAsset,
    LegacySecretAsset,
    LegacyTableInventory,
    LegacyToCanonicalMapping,
    ManualResolutionQueue,
    MigrationDecision,
)

ENV_FILES = ['.env', '.env.local', '.env.production', '.env.example']


def ensure_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_env_keys():
    results = []
    pattern = re.compile(r'^([A-Z0-9_]+)\s*=')
    for file_name in ENV_FILES:
        file_path = LEGACY_ROOT / file_name
        if not file_path.exists():
            continue
        for line in file_path.read_text(encoding='utf-8', errors='ignore').splitlines():
            match = pattern.match(line.strip())
            if not match:
                continue
            key = match.group(1)
            category = key.split('_')[0].lower()
            environments = ['example'] if file_name.endswith('example') else [file_name.replace('.env', '').strip('.') or 'default']
            results.append(
                LegacySecretAsset(
                    name=key,
                    category=category,
                    source_files=[file_name],
                    environments=environments,
                    status='placeholder' if file_name.endswith('example') else 'configured',
                ).__dict__
            )
    return results


def collect_sensitive_assets():
    assets = []
    certificates_dir = LEGACY_ROOT / 'certificados'
    if certificates_dir.exists():
        for path in certificates_dir.rglob('*'):
            if path.is_file():
                assets.append(
                    {
                        'category': 'certificate',
                        'name': path.name,
                        'relative_path': str(path.relative_to(LEGACY_ROOT)),
                    }
                )

    for folder in ['contabilidad', 'api-banco', 'supabase', 'lib/integrations']:
        folder_path = LEGACY_ROOT / folder
        if folder_path.exists():
            assets.append(
                {
                    'category': 'repository_asset',
                    'name': folder_path.name,
                    'relative_path': str(folder_path.relative_to(LEGACY_ROOT)),
                }
            )
    return assets


def collect_table_inventory():
    table_inventory = []
    types_file = LEGACY_ROOT / 'types' / 'supabase.ts'
    if types_file.exists():
        inside_tables = False
        for line in types_file.read_text(encoding='utf-8', errors='ignore').splitlines():
            stripped = line.rstrip()
            if stripped.strip() == 'Tables: {':
                inside_tables = True
                continue
            if inside_tables and stripped.strip() == 'Views: {':
                break
            if inside_tables:
                match = re.match(r'^\s{6}([a-zA-Z0-9_]+): \{$', stripped)
                if match:
                    table_inventory.append(
                        LegacyTableInventory(
                            table_name=match.group(1),
                            source='types/supabase.ts',
                            migration_files=[],
                        ).__dict__
                    )
    migration_names = [path.name for path in (LEGACY_ROOT / 'supabase' / 'migrations').glob('*.sql')]
    for row in table_inventory:
        row['migration_files'] = migration_names
    return table_inventory


def collect_integrations():
    integrations = []
    integrations_dir = LEGACY_ROOT / 'lib' / 'integrations'
    if not integrations_dir.exists():
        return integrations

    for provider_dir in sorted(path for path in integrations_dir.iterdir() if path.is_dir()):
        source_paths = [str(path.relative_to(LEGACY_ROOT)) for path in provider_dir.rglob('*') if path.is_file()]
        integrations.append(
            LegacyIntegrationAsset(
                provider=provider_dir.name,
                capability=f'{provider_dir.name}_integration',
                source_paths=source_paths,
                status='implemented_in_legacy',
            ).__dict__
        )
    return integrations


def collect_mapping_matrix():
    mappings = [
        LegacyToCanonicalMapping('socios', 'Socio', 'migrable_directo', 'Mantener RUT e identidad, revisar scopes.'),
        LegacyToCanonicalMapping('empresas', 'Empresa', 'requiere_transformacion', 'Separar ConfiguracionFiscalEmpresa del agregado empresa.'),
        LegacyToCanonicalMapping('participaciones', 'ParticipacionPatrimonial', 'requiere_transformacion', 'Normalizar owner_tipo y vigencia.'),
        LegacyToCanonicalMapping('propiedades', 'Propiedad', 'requiere_transformacion', 'Mover ownership y codigo operacional al modelo canónico.'),
        LegacyToCanonicalMapping('cuentas_bancarias', 'CuentaRecaudadora', 'requiere_transformacion', 'Reexpresar titularidad y provider activo.'),
        LegacyToCanonicalMapping('contratos', 'Contrato', 'requiere_transformacion', 'Separar MandatoOperacion, ContratoPropiedad y AvisoTermino.'),
        LegacyToCanonicalMapping('periodos_contractuales', 'PeriodoContractual', 'migrable_directo', 'Preserva el historial contractual.'),
        LegacyToCanonicalMapping('pagos_mensuales', 'PagoMensual', 'requiere_transformacion', 'Adaptar fechas bancarias y código de conciliación efectivo.'),
        LegacyToCanonicalMapping('movimientos_bancarios', 'Conciliacion/Banca', 'requiere_transformacion', 'Mapeo hacia movimientos importados y resoluciones manuales.'),
        LegacyToCanonicalMapping('facturas_electronicas', 'SII.DTE', 'requiere_transformacion', 'Separar capacidad y estado por gate.'),
        LegacyToCanonicalMapping('asientos_contables', 'AsientoContable', 'requiere_transformacion', 'Requiere evento contable previo y política de reverso.'),
        LegacyToCanonicalMapping('movimientos_asientos', 'MovimientoAsiento', 'migrable_directo', 'Pendiente mapear plan de cuentas final.'),
        LegacyToCanonicalMapping('contabilidad_persona_natural', 'Reporting/Patrimonio', 'requiere_decision_manual', 'Definir si entra al boundary v1 o fase posterior.'),
    ]

    decisions = [
        MigrationDecision('infraestructura', 'nueva_aislada', 'El greenfield no reutiliza la infraestructura viva del root.'),
        MigrationDecision('secrets', 'read_only_manifest', 'Se inventarian claves sin escribir valores en repo.'),
        MigrationDecision('schema', 'canonical_first', 'El modelo final sigue PRD_CANONICO, no Supabase legacy.'),
    ]

    queue = [
        ManualResolutionQueue(
            aggregate='contabilidad_persona_natural',
            reason='No está explicitada como entidad canónica mínima en el greenfield actual.',
            resolution_owner='producto+contabilidad',
        ).__dict__,
        ManualResolutionQueue(
            aggregate='facturas_electronicas',
            reason='Debe dividirse por capacidad y gate SII antes de migrar.',
            resolution_owner='arquitectura+sii',
        ).__dict__,
    ]

    return {
        'mappings': [mapping.__dict__ for mapping in mappings],
        'decisions': [decision.__dict__ for decision in decisions],
        'manual_resolution_queue': queue,
    }


def write_json(file_name, payload):
    (OUTPUT_DIR / file_name).write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding='utf-8')


def main():
    ensure_output_dir()
    write_json('secrets_inventory.json', parse_env_keys())
    write_json('sensitive_assets_inventory.json', collect_sensitive_assets())
    write_json('schema_inventory.json', collect_table_inventory())
    write_json('integration_inventory.json', collect_integrations())
    write_json('legacy_to_canonical_mapping.json', collect_mapping_matrix())


if __name__ == '__main__':
    main()

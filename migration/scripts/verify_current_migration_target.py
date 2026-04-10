import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = PROJECT_ROOT / 'backend'

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leasemanager_api.settings')

import django

django.setup()

from migration.importers import validate_current_migration_state  # noqa: E402
from patrimonio.models import ComunidadPatrimonial, Empresa, ParticipacionPatrimonial, Propiedad, Socio  # noqa: E402
from operacion.models import CuentaRecaudadora, MandatoOperacion  # noqa: E402
from contratos.models import Arrendatario, Contrato, PeriodoContractual  # noqa: E402
from audit.models import ManualResolution  # noqa: E402


def collect_snapshot():
    return {
        'socios': Socio.objects.count(),
        'empresas': Empresa.objects.count(),
        'comunidades': ComunidadPatrimonial.objects.count(),
        'participaciones_comunidad': ParticipacionPatrimonial.objects.filter(comunidad_owner__isnull=False).count(),
        'participaciones_empresa': ParticipacionPatrimonial.objects.filter(empresa_owner__isnull=False).count(),
        'propiedades': Propiedad.objects.count(),
        'cuentas_recaudadoras': CuentaRecaudadora.objects.count(),
        'mandatos': MandatoOperacion.objects.count(),
        'arrendatarios': Arrendatario.objects.count(),
        'contratos': Contrato.objects.count(),
        'periodos': PeriodoContractual.objects.count(),
        'manual_resolutions_abiertas': ManualResolution.objects.filter(
            status__in=[ManualResolution.Status.OPEN, ManualResolution.Status.IN_REVIEW]
        ).count(),
        'manual_resolutions_resueltas': ManualResolution.objects.filter(status=ManualResolution.Status.RESOLVED).count(),
    }


def collect_semantic_checks():
    edificio_q = list(
        MandatoOperacion.objects.filter(
            propiedad__direccion__in=['Edificio Q Dpto 1014', 'Edificio Q Bod. Nº 17, Est. Nº 33']
        )
        .select_related('entidad_facturadora', 'propiedad')
        .order_by('propiedad__direccion')
        .values_list('propiedad__direccion', 'entidad_facturadora__razon_social')
    )
    communities = list(
        ComunidadPatrimonial.objects.filter(
            nombre__in=['Av. Pablo Neruda 02491, Local 4', 'Edificio Q Dpto 1014', 'Edificio Q Bod. Nº 17, Est. Nº 33']
        ).order_by('nombre')
    )
    return {
        'edificio_q_facturadora': [
            {'propiedad': direccion, 'entidad_facturadora': facturadora}
            for direccion, facturadora in edificio_q
        ],
        'community_samples': [
            {'nombre': comunidad.nombre, 'participaciones_activas': comunidad.participaciones_activas().count()}
            for comunidad in communities
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description='Verifica que el target actual de migración coincide con el estado esperado del backlog actual.'
    )
    parser.add_argument('--output', default='')
    args = parser.parse_args()

    snapshot = collect_snapshot()
    validation = validate_current_migration_state(snapshot)
    result = {
        'database_url': os.environ.get('DATABASE_URL', ''),
        'snapshot': snapshot,
        'validation': validation,
        **collect_semantic_checks(),
    }
    rendered = json.dumps(result, indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).write_text(rendered, encoding='utf-8')
    print(rendered)
    if not validation['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()


import sys
from pathlib import Path

from django.test import TestCase

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from migration.importers import (  # noqa: E402
    collect_migration_state_snapshot,
    import_bundle,
    resolve_current_community_manual_resolutions,
    run_current_migration_flow,
)
from migration.transformers import transform_legacy_bundle  # noqa: E402
from audit.models import ManualResolution  # noqa: E402
from audit.services import resolve_migration_property_owner_manual_resolution  # noqa: E402
from contratos.models import Arrendatario, AvisoTermino, Contrato, ContratoPropiedad, PeriodoContractual  # noqa: E402
from operacion.models import CuentaRecaudadora, MandatoOperacion  # noqa: E402
from patrimonio.models import (  # noqa: E402
    ComunidadPatrimonial,
    Empresa,
    ModoRepresentacionComunidad,
    ParticipacionPatrimonial,
    Propiedad,
    RepresentacionComunidad,
    Socio,
)


class MigrationPipelineTests(TestCase):
    def test_transform_legacy_bundle_separates_deterministic_and_unresolved_items(self):
        legacy_rows = {
            'empresas': [
                {
                    'id': 'emp-1',
                    'rut': '76311245-4',
                    'nombre': 'Inmo Puig',
                    'razon_social': 'Inmobiliaria Puig SpA',
                    'direccion': 'Av Uno 123',
                    'comuna': 'Santiago',
                    'ciudad': 'Santiago',
                    'giro': 'Arriendos',
                    'activa': True,
                    'standard_contable': 'IFRS',
                }
            ],
            'socios': [
                {
                    'id': 'soc-1',
                    'rut': '17366287-4',
                    'nombre': 'Joaquin',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Vittini',
                    'nombre_completo': 'Joaquin Puig Vittini',
                    'email': 'jp@example.com',
                    'telefono': '+5691',
                    'direccion': 'Dir 1',
                    'domicilio': 'Dom 1',
                }
            ],
            'comunidades': [{'id': 'com-1', 'nombre': 'Comunidad Q', 'descripcion': 'Desc'}],
            'participaciones': [
                {
                    'id': 'par-1',
                    'socio_id': 'soc-1',
                    'empresa_id': 'emp-1',
                    'propiedad_id': None,
                    'comunidad_id': None,
                    'porcentaje': 100,
                    'porcentaje_participacion': 100,
                    'activa': True,
                    'fecha_inicio': '2026-01-01',
                    'fecha_fin': None,
                },
                {
                    'id': 'par-2',
                    'socio_id': 'soc-1',
                    'empresa_id': None,
                    'propiedad_id': 'prop-1',
                    'comunidad_id': None,
                    'porcentaje': 100,
                    'porcentaje_participacion': 100,
                    'activa': True,
                    'fecha_inicio': '2026-01-01',
                    'fecha_fin': None,
                },
            ],
            'propiedades': [
                {
                    'id': 'prop-1',
                    'codigo': 'P1',
                    'codigo_propiedad': '001',
                    'tipo': 'local',
                    'tipo_propiedad': None,
                    'direccion': 'Av Uno',
                    'numero': '123',
                    'depto': '',
                    'comuna': 'Santiago',
                    'ciudad': 'Santiago',
                    'rol': '123-1',
                    'rol_tributario': None,
                    'empresa_id': 'emp-1',
                    'socio_id': None,
                    'comunidad_id': None,
                    'es_comunidad': False,
                    'estado': 'arrendada',
                }
            ],
            'cuentas_bancarias': [
                {
                    'id': 'cta-1',
                    'banco': 'Banco de Chile',
                    'nombre_banco': None,
                    'numero_cuenta': '8240144702',
                    'tipo_cuenta': 'corriente',
                    'empresa_id': 'emp-1',
                    'moneda': 'CLP',
                    'activa': True,
                }
            ],
            'arrendatarios': [
                {
                    'id': 'arr-1',
                    'rut': '11111111-1',
                    'nombre': 'Tenant',
                    'apellido_paterno': 'Uno',
                    'apellido_materno': '',
                    'razon_social': None,
                    'tipo': 'persona_natural',
                    'email': 'tenant@example.com',
                    'telefono': '+5692',
                    'direccion': 'Dir T',
                    'nombre_completo': 'Tenant Uno',
                    'comuna': 'Santiago',
                    'ciudad': 'Santiago',
                    'estado_registro': 'activo',
                }
            ],
            'contratos': [
                {
                    'id': 'ctr-1',
                    'propiedad_id': 'prop-1',
                    'arrendatario_id': 'arr-1',
                    'fecha_inicio': '2026-01-01',
                    'fecha_termino': '2026-12-31',
                    'valor_arriendo': 100000,
                    'moneda': 'CLP',
                    'dia_pago': 5,
                    'dias_alerta_admin': 90,
                    'dias_aviso_termino': 60,
                    'garantia_requerida': True,
                    'requiere_garantia': True,
                    'estado': 'activo',
                }
            ],
            'periodos_contractuales': [
                {
                    'id': 'per-1',
                    'contrato_id': 'ctr-1',
                    'fecha_inicio': '2026-01-01',
                    'fecha_termino': '2026-12-31',
                    'valor_arriendo': 100000,
                    'moneda': 'CLP',
                    'activo': True,
                    'numero_periodo': 1,
                }
            ],
        }

        bundle = transform_legacy_bundle(legacy_rows)

        self.assertEqual(bundle['metadata']['counts']['socios'], 1)
        self.assertEqual(bundle['metadata']['counts']['property_participation_rows_skipped'], 1)
        self.assertEqual(len(bundle['patrimonio']['empresas']), 1)
        self.assertEqual(len(bundle['contratos']['contratos_candidates']), 1)
        self.assertIn('participaciones_propiedad', bundle['unresolved'])

    def test_transform_legacy_bundle_resequences_duplicate_period_numbers(self):
        legacy_rows = {
            'empresas': [],
            'socios': [],
            'comunidades': [],
            'participaciones': [],
            'propiedades': [],
            'cuentas_bancarias': [],
            'arrendatarios': [],
            'contratos': [
                {
                    'id': 'ctr-1',
                    'propiedad_id': 'prop-1',
                    'arrendatario_id': 'arr-1',
                    'fecha_inicio': '2026-01-01',
                    'fecha_termino': '2026-12-31',
                    'valor_arriendo': 100000,
                    'moneda': 'CLP',
                    'dia_pago': 5,
                    'dias_alerta_admin': 90,
                    'dias_aviso_termino': 60,
                    'garantia_requerida': True,
                    'requiere_garantia': True,
                    'estado': 'activo',
                }
            ],
            'periodos_contractuales': [
                {
                    'id': 'per-2',
                    'contrato_id': 'ctr-1',
                    'fecha_inicio': '2027-01-01',
                    'fecha_termino': '2027-12-31',
                    'valor_arriendo': 120000,
                    'moneda': 'CLP',
                    'activo': True,
                    'numero_periodo': 1,
                },
                {
                    'id': 'per-1',
                    'contrato_id': 'ctr-1',
                    'fecha_inicio': '2026-01-01',
                    'fecha_termino': '2026-12-31',
                    'valor_arriendo': 100000,
                    'moneda': 'CLP',
                    'activo': True,
                    'numero_periodo': 1,
                },
            ],
        }

        bundle = transform_legacy_bundle(legacy_rows)

        periods = bundle['contratos']['periodos_candidates']
        self.assertEqual([period['numero_periodo'] for period in periods], [1, 2])
        self.assertEqual([period['legacy_numero_periodo'] for period in periods], [1, 1])
        self.assertTrue(any('re-sequenced chronologically' in warning for warning in bundle['warnings']))

    def test_transform_legacy_bundle_derives_socio_owner_and_documented_personal_account(self):
        legacy_rows = {
            'empresas': [],
            'socios': [
                {
                    'id': 'soc-1',
                    'rut': '17.366.287-4',
                    'nombre': 'Joaquin',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Vittini',
                    'nombre_completo': 'Joaquin Puig Vittini',
                    'email': 'jp@example.com',
                    'telefono': '+5691',
                    'direccion': 'Dir 1',
                    'domicilio': 'Dom 1',
                }
            ],
            'comunidades': [],
            'participaciones': [
                {
                    'id': 'par-1',
                    'socio_id': 'soc-1',
                    'empresa_id': None,
                    'propiedad_id': 'prop-1',
                    'comunidad_id': None,
                    'porcentaje': 100,
                    'porcentaje_participacion': 100,
                    'activa': True,
                    'fecha_inicio': '2026-01-01',
                    'fecha_fin': None,
                }
            ],
            'propiedades': [
                {
                    'id': 'prop-1',
                    'codigo': '15',
                    'codigo_propiedad': None,
                    'tipo': 'estacionamiento',
                    'tipo_propiedad': None,
                    'direccion': 'Av. Los Pablos 1950, Estacionamiento E49',
                    'numero': '',
                    'depto': '',
                    'comuna': 'Santiago',
                    'ciudad': 'Santiago',
                    'rol': '123-1',
                    'rol_tributario': None,
                    'empresa_id': None,
                    'socio_id': None,
                    'comunidad_id': None,
                    'es_comunidad': False,
                    'estado': 'arrendada',
                }
            ],
            'cuentas_bancarias': [
                {
                    'id': 'cta-1',
                    'banco': 'Banco de Chile',
                    'nombre_banco': None,
                    'numero_cuenta': '8240131105',
                    'tipo_cuenta': 'corriente',
                    'empresa_id': None,
                    'moneda': 'CLP',
                    'activa': True,
                }
            ],
            'arrendatarios': [],
            'contratos': [],
            'periodos_contractuales': [],
        }

        bundle = transform_legacy_bundle(legacy_rows)

        self.assertEqual(bundle['patrimonio']['propiedades'][0]['owner_kind'], 'socio')
        self.assertEqual(bundle['patrimonio']['propiedades'][0]['owner_legacy_id'], 'soc-1')
        self.assertEqual(bundle['operacion']['cuentas_recaudadoras'][0]['owner_kind'], 'socio')
        self.assertEqual(bundle['operacion']['cuentas_recaudadoras'][0]['owner_legacy_id'], 'soc-1')

    def test_transform_legacy_bundle_enriches_manual_owner_resolution_candidates(self):
        legacy_rows = {
            'empresas': [],
            'socios': [
                {
                    'id': 'soc-1',
                    'rut': '11.111.111-1',
                    'nombre': 'Socio Uno',
                    'apellido_paterno': 'Uno',
                    'apellido_materno': '',
                    'nombre_completo': 'Socio Uno',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
                {
                    'id': 'soc-2',
                    'rut': '22.222.222-2',
                    'nombre': 'Socio Dos',
                    'apellido_paterno': 'Dos',
                    'apellido_materno': '',
                    'nombre_completo': 'Socio Dos',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
            ],
            'comunidades': [],
            'participaciones': [
                {
                    'id': 'par-1',
                    'socio_id': 'soc-1',
                    'empresa_id': None,
                    'propiedad_id': 'prop-1',
                    'comunidad_id': None,
                    'porcentaje': 50,
                    'porcentaje_participacion': 50,
                    'activa': True,
                    'fecha_inicio': '2026-01-01',
                    'fecha_fin': None,
                },
                {
                    'id': 'par-2',
                    'socio_id': 'soc-2',
                    'empresa_id': None,
                    'propiedad_id': 'prop-1',
                    'comunidad_id': None,
                    'porcentaje': 50,
                    'porcentaje_participacion': 50,
                    'activa': True,
                    'fecha_inicio': '2026-01-01',
                    'fecha_fin': None,
                },
            ],
            'propiedades': [
                {
                    'id': 'prop-1',
                    'codigo': '46',
                    'codigo_propiedad': None,
                    'tipo': 'departamento',
                    'tipo_propiedad': None,
                    'direccion': 'Av. Santa Maria 9500 Dpto 1014',
                    'numero': '',
                    'depto': '',
                    'comuna': 'Santiago',
                    'ciudad': 'Santiago',
                    'rol': '123-1',
                    'rol_tributario': None,
                    'empresa_id': None,
                    'socio_id': None,
                    'comunidad_id': None,
                    'es_comunidad': False,
                    'estado': 'arrendada',
                }
            ],
            'cuentas_bancarias': [],
            'arrendatarios': [],
            'contratos': [],
            'periodos_contractuales': [],
        }

        bundle = transform_legacy_bundle(legacy_rows)

        unresolved = bundle['unresolved']['propiedades_sin_owner'][0]
        self.assertEqual(unresolved['candidate_owner_model'], 'comunidad')
        self.assertEqual(unresolved['participaciones_count'], 2)
        self.assertEqual(len(unresolved['socios']), 2)
        self.assertEqual(len(unresolved['participantes']), 2)
        self.assertIsNone(unresolved['representacion_sugerida'])

    def test_transform_legacy_bundle_applies_confirmed_override_for_edificio_q_1014(self):
        legacy_rows = {
            'empresas': [
                {
                    'id': 'emp-1',
                    'rut': '76.311.245-4',
                    'nombre': 'Inmobiliaria Puig SpA',
                    'razon_social': 'Inmobiliaria Puig SpA',
                    'direccion': '',
                    'comuna': '',
                    'ciudad': '',
                    'giro': '',
                    'activa': True,
                    'standard_contable': 'IFRS',
                }
            ],
            'socios': [
                {
                    'id': 'soc-cecilia',
                    'rut': '7.768.066-7',
                    'nombre': 'Cecilia',
                    'apellido_paterno': 'Vittini',
                    'apellido_materno': 'De Ruyt',
                    'nombre_completo': 'Cecilia Jacqueline Vittini De Ruyt',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
                {
                    'id': 'soc-trinidad',
                    'rut': '20.785.966-4',
                    'nombre': 'Trinidad',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Jequier',
                    'nombre_completo': 'Trinidad Puig Jequier',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
                {
                    'id': 'soc-catalina',
                    'rut': '21.180.524-2',
                    'nombre': 'Catalina',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Jequier',
                    'nombre_completo': 'Catalina Puig Jequier',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
                {
                    'id': 'soc-cristobal',
                    'rut': '16.531.864-1',
                    'nombre': 'Cristóbal',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Vittini',
                    'nombre_completo': 'Cristóbal José Puig Vittini',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
                {
                    'id': 'soc-geraldine',
                    'rut': '15.244.057-K',
                    'nombre': 'Geraldine',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Vittini',
                    'nombre_completo': 'Geraldine Stefanie Puig Vittini',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
                {
                    'id': 'soc-joaquin',
                    'rut': '17.366.287-4',
                    'nombre': 'Joaquín',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Vittini',
                    'nombre_completo': 'Joaquín Esteban Puig Vittini',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
            ],
            'comunidades': [],
            'participaciones': [
                {
                    'id': 'par-1',
                    'socio_id': 'soc-cecilia',
                    'empresa_id': None,
                    'propiedad_id': 'prop-46',
                    'comunidad_id': None,
                    'porcentaje': 16.67,
                    'porcentaje_participacion': 16.67,
                    'activa': True,
                    'fecha_inicio': None,
                    'fecha_fin': None,
                },
                {
                    'id': 'par-2',
                    'socio_id': 'soc-trinidad',
                    'empresa_id': None,
                    'propiedad_id': 'prop-46',
                    'comunidad_id': None,
                    'porcentaje': 16.67,
                    'porcentaje_participacion': 16.67,
                    'activa': True,
                    'fecha_inicio': None,
                    'fecha_fin': None,
                },
                {
                    'id': 'par-3',
                    'socio_id': 'soc-catalina',
                    'empresa_id': None,
                    'propiedad_id': 'prop-46',
                    'comunidad_id': None,
                    'porcentaje': 16.67,
                    'porcentaje_participacion': 16.67,
                    'activa': True,
                    'fecha_inicio': None,
                    'fecha_fin': None,
                },
                {
                    'id': 'par-4',
                    'socio_id': 'soc-cristobal',
                    'empresa_id': None,
                    'propiedad_id': 'prop-46',
                    'comunidad_id': None,
                    'porcentaje': 16.66,
                    'porcentaje_participacion': 16.66,
                    'activa': True,
                    'fecha_inicio': None,
                    'fecha_fin': None,
                },
                {
                    'id': 'par-5',
                    'socio_id': 'soc-geraldine',
                    'empresa_id': None,
                    'propiedad_id': 'prop-46',
                    'comunidad_id': None,
                    'porcentaje': 16.67,
                    'porcentaje_participacion': 16.67,
                    'activa': True,
                    'fecha_inicio': None,
                    'fecha_fin': None,
                },
            ],
            'propiedades': [
                {
                    'id': 'prop-46',
                    'codigo': 46,
                    'codigo_propiedad': None,
                    'tipo': 'departamento',
                    'tipo_propiedad': None,
                    'direccion': 'Edificio Q Dpto 1014',
                    'numero': '',
                    'depto': '',
                    'comuna': 'Temuco',
                    'ciudad': 'Temuco',
                    'rol': '1338-268',
                    'rol_tributario': None,
                    'empresa_id': None,
                    'socio_id': None,
                    'comunidad_id': None,
                    'es_comunidad': False,
                    'estado': 'arrendada',
                }
            ],
            'cuentas_bancarias': [],
            'arrendatarios': [],
            'contratos': [],
            'periodos_contractuales': [],
        }

        bundle = transform_legacy_bundle(legacy_rows)
        unresolved = bundle['unresolved']['propiedades_sin_owner'][0]
        self.assertEqual(unresolved['candidate_owner_model'], 'comunidad')
        self.assertEqual(unresolved['total_pct'], 100.0)
        self.assertEqual(len(unresolved['participantes']), 6)
        participant_types = sorted({item['participante_tipo'] for item in unresolved['participantes']})
        self.assertEqual(participant_types, ['empresa', 'socio'])
        self.assertEqual(unresolved['representacion_sugerida']['modo_representacion'], 'designado')

    def test_transform_legacy_bundle_applies_confirmed_override_for_edificio_q_bod_17_est_33(self):
        legacy_rows = {
            'empresas': [
                {
                    'id': 'emp-1',
                    'rut': '76.311.245-4',
                    'nombre': 'Inmobiliaria Puig SpA',
                    'razon_social': 'Inmobiliaria Puig SpA',
                    'direccion': '',
                    'comuna': '',
                    'ciudad': '',
                    'giro': '',
                    'activa': True,
                    'standard_contable': 'IFRS',
                }
            ],
            'socios': [
                {
                    'id': 'soc-cecilia',
                    'rut': '7.768.066-7',
                    'nombre': 'Cecilia',
                    'apellido_paterno': 'Vittini',
                    'apellido_materno': 'De Ruyt',
                    'nombre_completo': 'Cecilia Jacqueline Vittini De Ruyt',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
                {
                    'id': 'soc-trinidad',
                    'rut': '20.785.966-4',
                    'nombre': 'Trinidad',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Jequier',
                    'nombre_completo': 'Trinidad Puig Jequier',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
                {
                    'id': 'soc-catalina',
                    'rut': '21.180.524-2',
                    'nombre': 'Catalina',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Jequier',
                    'nombre_completo': 'Catalina Puig Jequier',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
                {
                    'id': 'soc-cristobal',
                    'rut': '16.531.864-1',
                    'nombre': 'Cristóbal',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Vittini',
                    'nombre_completo': 'Cristóbal José Puig Vittini',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
                {
                    'id': 'soc-geraldine',
                    'rut': '15.244.057-K',
                    'nombre': 'Geraldine',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Vittini',
                    'nombre_completo': 'Geraldine Stefanie Puig Vittini',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
                {
                    'id': 'soc-joaquin',
                    'rut': '17.366.287-4',
                    'nombre': 'Joaquín',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Vittini',
                    'nombre_completo': 'Joaquín Esteban Puig Vittini',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                },
            ],
            'comunidades': [],
            'participaciones': [
                {
                    'id': 'par-1',
                    'socio_id': 'soc-cecilia',
                    'empresa_id': None,
                    'propiedad_id': 'prop-40',
                    'comunidad_id': None,
                    'porcentaje': 16.67,
                    'porcentaje_participacion': 16.67,
                    'activa': True,
                    'fecha_inicio': None,
                    'fecha_fin': None,
                },
                {
                    'id': 'par-2',
                    'socio_id': 'soc-trinidad',
                    'empresa_id': None,
                    'propiedad_id': 'prop-40',
                    'comunidad_id': None,
                    'porcentaje': 16.67,
                    'porcentaje_participacion': 16.67,
                    'activa': True,
                    'fecha_inicio': None,
                    'fecha_fin': None,
                },
                {
                    'id': 'par-3',
                    'socio_id': 'soc-catalina',
                    'empresa_id': None,
                    'propiedad_id': 'prop-40',
                    'comunidad_id': None,
                    'porcentaje': 16.67,
                    'porcentaje_participacion': 16.67,
                    'activa': True,
                    'fecha_inicio': None,
                    'fecha_fin': None,
                },
                {
                    'id': 'par-4',
                    'socio_id': 'soc-cristobal',
                    'empresa_id': None,
                    'propiedad_id': 'prop-40',
                    'comunidad_id': None,
                    'porcentaje': 16.66,
                    'porcentaje_participacion': 16.66,
                    'activa': True,
                    'fecha_inicio': None,
                    'fecha_fin': None,
                },
                {
                    'id': 'par-5',
                    'socio_id': 'soc-geraldine',
                    'empresa_id': None,
                    'propiedad_id': 'prop-40',
                    'comunidad_id': None,
                    'porcentaje': 16.67,
                    'porcentaje_participacion': 16.67,
                    'activa': True,
                    'fecha_inicio': None,
                    'fecha_fin': None,
                },
            ],
            'propiedades': [
                {
                    'id': 'prop-40',
                    'codigo': 40,
                    'codigo_propiedad': None,
                    'tipo': 'otro',
                    'tipo_propiedad': None,
                    'direccion': 'Edificio Q Bod. Nº 17, Est. Nº 33',
                    'numero': '',
                    'depto': '',
                    'comuna': 'Temuco',
                    'ciudad': 'Temuco',
                    'rol': '1338-33',
                    'rol_tributario': None,
                    'empresa_id': None,
                    'socio_id': None,
                    'comunidad_id': None,
                    'es_comunidad': False,
                    'estado': 'acoplada',
                }
            ],
            'cuentas_bancarias': [],
            'arrendatarios': [],
            'contratos': [],
            'periodos_contractuales': [],
        }

        bundle = transform_legacy_bundle(legacy_rows)
        unresolved = bundle['unresolved']['propiedades_sin_owner'][0]
        self.assertEqual(unresolved['candidate_owner_model'], 'comunidad')
        self.assertEqual(unresolved['total_pct'], 100.0)
        self.assertEqual(len(unresolved['participantes']), 6)
        participant_types = sorted({item['participante_tipo'] for item in unresolved['participantes']})
        self.assertEqual(participant_types, ['empresa', 'socio'])
        self.assertEqual(unresolved['representacion_sugerida']['modo_representacion'], 'designado')

    def test_transform_legacy_bundle_applies_confirmed_default_day_payment_for_known_legacy_contracts(self):
        legacy_rows = {
            'empresas': [],
            'socios': [],
            'comunidades': [],
            'participaciones': [],
            'propiedades': [],
            'cuentas_bancarias': [],
            'arrendatarios': [],
            'contratos': [
                {
                    'id': '08fe72fc-0890-460d-974f-d934931b7e19',
                    'propiedad_id': 'prop-1',
                    'arrendatario_id': 'arr-1',
                    'fecha_inicio': '2025-11-23',
                    'fecha_termino': '2026-01-23',
                    'valor_arriendo': 2,
                    'moneda': 'UF',
                    'dia_pago': None,
                    'dias_alerta_admin': 0,
                    'dias_aviso_termino': 120,
                    'garantia_requerida': True,
                    'requiere_garantia': True,
                    'estado': 'activo',
                }
            ],
            'periodos_contractuales': [],
        }

        bundle = transform_legacy_bundle(legacy_rows)
        self.assertEqual(bundle['contratos']['contratos_candidates'][0]['dia_pago_mensual'], 5)

    def test_transform_legacy_bundle_reassigns_paulina_contract_from_96_to_97(self):
        legacy_rows = {
            'empresas': [],
            'socios': [
                {
                    'id': 'soc-joaquin',
                    'rut': '17.366.287-4',
                    'nombre': 'Joaquin',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Vittini',
                    'nombre_completo': 'Joaquin Puig Vittini',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                }
            ],
            'comunidades': [],
            'participaciones': [],
            'propiedades': [
                {
                    'id': '91eb267c-154c-40df-89d8-0ea18bacd765',
                    'codigo': 19,
                    'codigo_propiedad': None,
                    'tipo': 'otro',
                    'tipo_propiedad': 'persona_natural',
                    'direccion': 'Santa Maria 9500 Estacionamiento 96',
                    'numero': None,
                    'depto': None,
                    'comuna': 'Vitacura',
                    'ciudad': 'Santiago',
                    'rol': '70015',
                    'rol_tributario': None,
                    'empresa_id': None,
                    'socio_id': None,
                    'comunidad_id': None,
                    'es_comunidad': False,
                    'estado': 'arrendada',
                },
                {
                    'id': '54c7de96-c6bb-4446-971f-90c062edffae',
                    'codigo': 20,
                    'codigo_propiedad': None,
                    'tipo': 'otro',
                    'tipo_propiedad': 'persona_natural',
                    'direccion': 'Av Santa Maria 9500',
                    'numero': 'Estacionamiento 97',
                    'depto': None,
                    'comuna': 'Vitacura',
                    'ciudad': 'Santiago',
                    'rol': '70014',
                    'rol_tributario': None,
                    'empresa_id': None,
                    'socio_id': None,
                    'comunidad_id': None,
                    'es_comunidad': False,
                    'estado': 'disponible',
                    'observaciones': 'Propiedad 100% de Joaquín Puig Vittini como persona natural. Mes a mes, sin factura.',
                }
            ],
            'cuentas_bancarias': [],
            'arrendatarios': [
                {
                    'id': '0f7aa310-231a-40a9-b397-99a7f53a4f03',
                    'rut': None,
                    'nombre': None,
                    'apellido_paterno': None,
                    'apellido_materno': None,
                    'razon_social': None,
                    'tipo': 'persona',
                    'email': 'pfuenza95@gmail.com',
                    'telefono': '+56962110932',
                    'direccion': None,
                    'nombre_completo': 'Paulina Fuenzalida',
                    'comuna': 'Vitacura',
                    'ciudad': 'Santiago',
                    'estado_registro': 'activo',
                }
            ],
            'contratos': [
                {
                    'id': 'b1634538-d8a8-406a-a1f3-bcb3ff391a2a',
                    'propiedad_id': '91eb267c-154c-40df-89d8-0ea18bacd765',
                    'arrendatario_id': '0f7aa310-231a-40a9-b397-99a7f53a4f03',
                    'fecha_inicio': '2025-11-23',
                    'fecha_termino': '2026-01-23',
                    'valor_arriendo': 70015,
                    'moneda': 'CLP',
                    'dia_pago': None,
                    'dias_alerta_admin': 0,
                    'dias_aviso_termino': 120,
                    'garantia_requerida': True,
                    'requiere_garantia': True,
                    'estado': 'activo',
                }
            ],
            'periodos_contractuales': [],
        }

        bundle = transform_legacy_bundle(legacy_rows)
        self.assertEqual(bundle['patrimonio']['propiedades'][0]['owner_kind'], 'socio')
        self.assertEqual(bundle['patrimonio']['propiedades'][0]['direccion'], 'Av Santa Maria 9500, Estacionamiento 97')
        self.assertEqual(bundle['contratos']['arrendatarios'][0]['rut'], '19.076.873-2')
        self.assertEqual(bundle['contratos']['contratos_candidates'][0]['propiedad_legacy_id'], '54c7de96-c6bb-4446-971f-90c062edffae')
        self.assertEqual(bundle['contratos']['contratos_candidates'][0]['dia_pago_mensual'], 5)

    def test_transform_legacy_bundle_excludes_estacionamiento_96_from_current_migration(self):
        legacy_rows = {
            'empresas': [],
            'socios': [
                {
                    'id': 'soc-1',
                    'rut': '17.366.287-4',
                    'nombre': 'Joaquin',
                    'apellido_paterno': 'Puig',
                    'apellido_materno': 'Vittini',
                    'nombre_completo': 'Joaquin Puig Vittini',
                    'email': '',
                    'telefono': '',
                    'direccion': '',
                    'domicilio': '',
                }
            ],
            'comunidades': [],
            'participaciones': [],
            'propiedades': [
                {
                    'id': 'prop-96',
                    'codigo': 19,
                    'codigo_propiedad': None,
                    'tipo': 'otro',
                    'tipo_propiedad': 'persona_natural',
                    'direccion': 'Santa Maria 9500 Estacionamiento 96',
                    'numero': None,
                    'depto': None,
                    'comuna': 'Vitacura',
                    'ciudad': 'Santiago',
                    'rol': '70015',
                    'rol_tributario': None,
                    'empresa_id': None,
                    'socio_id': None,
                    'comunidad_id': None,
                    'es_comunidad': False,
                    'estado': 'arrendada',
                }
            ],
            'cuentas_bancarias': [],
            'arrendatarios': [
                {
                    'id': 'arr-1',
                    'rut': None,
                    'nombre': None,
                    'apellido_paterno': None,
                    'apellido_materno': None,
                    'razon_social': None,
                    'tipo': 'persona',
                    'email': 'pfuenza95@gmail.com',
                    'telefono': '+56962110932',
                    'direccion': None,
                    'nombre_completo': 'Paulina Fuenzalida',
                    'comuna': 'Vitacura',
                    'ciudad': 'Santiago',
                    'estado_registro': 'activo',
                }
            ],
            'contratos': [
                {
                    'id': 'b1634538-d8a8-406a-a1f3-bcb3ff391a2a',
                    'propiedad_id': 'prop-96',
                    'arrendatario_id': 'arr-1',
                    'fecha_inicio': '2025-11-23',
                    'fecha_termino': '2026-01-23',
                    'valor_arriendo': 70015,
                    'moneda': 'CLP',
                    'dia_pago': None,
                    'dias_alerta_admin': 0,
                    'dias_aviso_termino': 120,
                    'garantia_requerida': True,
                    'requiere_garantia': True,
                    'estado': 'activo',
                }
            ],
            'periodos_contractuales': [],
        }

        bundle = transform_legacy_bundle(legacy_rows)
        self.assertEqual(bundle['patrimonio']['propiedades'], [])
        self.assertEqual(bundle['contratos']['contratos_candidates'][0]['propiedad_legacy_id'], '54c7de96-c6bb-4446-971f-90c062edffae')

    def test_transform_legacy_bundle_excludes_confirmed_former_inactive_tenants(self):
        legacy_rows = {
            'empresas': [],
            'socios': [],
            'comunidades': [],
            'participaciones': [],
            'propiedades': [],
            'cuentas_bancarias': [],
            'arrendatarios': [
                {
                    'id': '780bba00-db91-4b63-bfc0-35706db6e6a5',
                    'rut': None,
                    'nombre': None,
                    'apellido_paterno': None,
                    'apellido_materno': None,
                    'razon_social': None,
                    'tipo': 'persona',
                    'email': 'joseibanez246@gmail.com',
                    'telefono': '+56976188469',
                    'direccion': None,
                    'nombre_completo': 'José Ibáñez',
                    'comuna': 'Temuco',
                    'ciudad': 'Temuco',
                    'estado_registro': 'inactivo',
                },
                {
                    'id': '714b5efc-68de-4457-b950-e57d4c4ee14c',
                    'rut': None,
                    'nombre': None,
                    'apellido_paterno': None,
                    'apellido_materno': None,
                    'razon_social': None,
                    'tipo': 'persona',
                    'email': None,
                    'telefono': None,
                    'direccion': None,
                    'nombre_completo': 'Claudio Galdames',
                    'comuna': 'Temuco',
                    'ciudad': 'Temuco',
                    'estado_registro': 'inactivo',
                }
            ],
            'contratos': [],
            'periodos_contractuales': [],
        }

        bundle = transform_legacy_bundle(legacy_rows)
        self.assertEqual(bundle['contratos']['arrendatarios'], [])

    def test_import_bundle_loads_deterministic_entities_idempotently(self):
        bundle = {
            'patrimonio': {
                'socios': [
                    {
                        'legacy_id': 'soc-1',
                        'rut': '17.366.287-4',
                        'nombre': 'Joaquin Puig Vittini',
                        'email': 'jp@example.com',
                        'telefono': '+5691',
                        'domicilio': 'Dom 1',
                        'activo': True,
                    }
                ],
                'empresas': [
                    {
                        'legacy_id': 'emp-1',
                        'rut': '76.311.245-4',
                        'razon_social': 'Inmobiliaria Puig SpA',
                        'domicilio': 'Av Uno 123, Santiago',
                        'giro': 'Arriendos',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    }
                ],
                'comunidades': [
                    {
                        'legacy_id': 'com-1',
                        'nombre': 'Comunidad Q',
                        'descripcion': 'Desc',
                        'estado': 'activa',
                        'representante_legacy_id': 'soc-1',
                    }
                ],
                'participaciones': [
                    {
                        'legacy_id': 'par-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-1',
                        'socio_legacy_id': 'soc-1',
                        'porcentaje': '100.00',
                        'vigente_desde': '2026-01-01',
                        'vigente_hasta': None,
                        'activo': True,
                    }
                ],
                'propiedades': [
                    {
                        'legacy_id': 'prop-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-1',
                        'rol_avaluo': '123-1',
                        'direccion': 'Av Uno 123',
                        'comuna': 'Santiago',
                        'region': '',
                        'tipo_inmueble': 'local',
                        'codigo_propiedad': '001',
                        'estado': 'activa',
                        'legacy_estado': 'arrendada',
                    }
                ],
            },
            'operacion': {
                'cuentas_recaudadoras': [
                    {
                        'legacy_id': 'cta-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-1',
                        'institucion': 'Banco de Chile',
                        'numero_cuenta': '8240144702',
                        'tipo_cuenta': 'corriente',
                        'titular_nombre': 'Inmobiliaria Puig SpA',
                        'titular_rut': '76311245-4',
                        'moneda_operativa': 'CLP',
                        'estado_operativo': 'activa',
                    }
                ]
            },
            'contratos': {
                'arrendatarios': [
                    {
                        'legacy_id': 'arr-1',
                        'tipo_arrendatario': 'persona_natural',
                        'nombre_razon_social': 'Tenant Uno',
                        'rut': '11.111.111-1',
                        'email': 'tenant@example.com',
                        'telefono': '+5692',
                        'domicilio_notificaciones': 'Dir T, Santiago',
                        'estado_contacto': 'activo',
                        'whatsapp_bloqueado': False,
                    }
                ],
                'contratos_candidates': [{'legacy_id': 'ctr-1'}],
                'periodos_candidates': [{'legacy_id': 'per-1'}],
            },
            'unresolved': {'contracts': ['needs mandate mapping']},
        }

        report = import_bundle(bundle)
        self.assertEqual(Socio.objects.count(), 1)
        self.assertEqual(Empresa.objects.count(), 1)
        self.assertEqual(ComunidadPatrimonial.objects.count(), 1)
        self.assertEqual(ParticipacionPatrimonial.objects.count(), 1)
        self.assertEqual(Propiedad.objects.count(), 1)
        self.assertEqual(CuentaRecaudadora.objects.count(), 1)
        self.assertEqual(Arrendatario.objects.count(), 1)
        self.assertIn('contratos_candidates', report.skipped)

        report_again = import_bundle(bundle)
        self.assertEqual(Socio.objects.count(), 1)
        self.assertEqual(Empresa.objects.count(), 1)
        self.assertGreaterEqual(report_again.updated.get('socios', 0), 1)

    def test_import_bundle_skips_contract_without_unique_active_mandate(self):
        bundle = {
            'patrimonio': {'socios': [], 'empresas': [], 'comunidades': [], 'participaciones': [], 'propiedades': []},
            'operacion': {'cuentas_recaudadoras': []},
            'contratos': {
                'arrendatarios': [],
                'contratos_candidates': [
                    {
                        'legacy_id': 'ctr-1',
                        'arrendatario_legacy_id': 'arr-1',
                        'propiedad_legacy_id': 'prop-1',
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin_vigente': '2026-12-31',
                        'fecha_entrega': '2026-01-01',
                        'dia_pago_mensual': 5,
                        'plazo_notificacion_termino_dias': 60,
                        'dias_prealerta_admin': 90,
                        'estado_legacy': 'activo',
                        'aviso_termino_registrado': False,
                        'fecha_aviso_termino': None,
                        'notas_aviso_termino': '',
                    }
                ],
                'periodos_candidates': [],
            },
            'unresolved': {},
        }
        report = import_bundle(bundle)
        self.assertIn('contratos_candidates', report.skipped)

    def test_import_bundle_skips_contract_with_missing_dia_pago(self):
        bundle = {
            'patrimonio': {'socios': [], 'empresas': [], 'comunidades': [], 'participaciones': [], 'propiedades': []},
            'operacion': {'cuentas_recaudadoras': []},
            'contratos': {
                'arrendatarios': [],
                'contratos_candidates': [
                    {
                        'legacy_id': 'ctr-1',
                        'arrendatario_legacy_id': 'arr-1',
                        'propiedad_legacy_id': 'prop-1',
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin_vigente': '2026-12-31',
                        'fecha_entrega': '2026-01-01',
                        'dia_pago_mensual': None,
                        'plazo_notificacion_termino_dias': 60,
                        'dias_prealerta_admin': 90,
                    }
                ],
                'periodos_candidates': [],
            },
            'unresolved': {},
        }

        report = import_bundle(bundle)

        self.assertIn('contratos_candidates', report.skipped)
        self.assertIn('dia_pago_mensual', report.skipped['contratos_candidates'][0]['reason'])

    def test_import_bundle_defaults_participacion_without_vigente_desde_to_symbolic_inheritance_date(self):
        bundle = {
            'patrimonio': {
                'socios': [
                    {
                        'legacy_id': 'soc-1',
                        'rut': '17366287-4',
                        'nombre': 'Socio Uno',
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    }
                ],
                'empresas': [
                    {
                        'legacy_id': 'emp-1',
                        'rut': '76311245-4',
                        'razon_social': 'Inmobiliaria Puig SpA',
                        'domicilio': '',
                        'giro': '',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    }
                ],
                'comunidades': [],
                'participaciones': [
                    {
                        'legacy_id': 'par-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-1',
                        'socio_legacy_id': 'soc-1',
                        'porcentaje': '100.00',
                        'vigente_desde': None,
                        'vigente_hasta': None,
                        'activo': True,
                    }
                ],
                'propiedades': [],
            },
            'operacion': {'cuentas_recaudadoras': []},
            'contratos': {'arrendatarios': [], 'contratos_candidates': [], 'periodos_candidates': []},
            'unresolved': {},
        }

        report = import_bundle(bundle)

        self.assertEqual(ParticipacionPatrimonial.objects.count(), 1)
        participacion = ParticipacionPatrimonial.objects.get()
        self.assertEqual(str(participacion.vigente_desde), '2017-03-16')
        self.assertNotIn('participaciones', report.skipped)

    def test_import_bundle_skips_arrendatario_without_rut(self):
        bundle = {
            'patrimonio': {'socios': [], 'empresas': [], 'comunidades': [], 'participaciones': [], 'propiedades': []},
            'operacion': {'cuentas_recaudadoras': []},
            'contratos': {
                'arrendatarios': [
                    {
                        'legacy_id': 'arr-1',
                        'tipo_arrendatario': 'persona_natural',
                        'nombre_razon_social': 'Tenant Sin Rut',
                        'rut': '',
                        'email': 'tenant@example.com',
                        'telefono': '',
                        'domicilio_notificaciones': '',
                        'estado_contacto': 'activo',
                        'whatsapp_bloqueado': False,
                    }
                ],
                'contratos_candidates': [],
                'periodos_candidates': [],
            },
            'unresolved': {},
        }

        report = import_bundle(bundle)

        self.assertEqual(Arrendatario.objects.count(), 0)
        self.assertIn('arrendatarios', report.skipped)
        self.assertEqual(report.skipped['arrendatarios'][0]['legacy_id'], 'arr-1')

    def test_import_bundle_imports_contract_and_period_when_mandate_is_unique(self):
        socio = Socio.objects.create(nombre='Socio Uno', rut='17366287-4')
        empresa = Empresa.objects.create(razon_social='Inmobiliaria Puig SpA', rut='76311245-4', estado='activa')
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio,
            empresa_owner=empresa,
            porcentaje='100.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        propiedad = Propiedad.objects.create(
            codigo_propiedad='001',
            rol_avaluo='123-1',
            direccion='Av Uno 123',
            comuna='Santiago',
            region='',
            tipo_inmueble='local',
            estado='activa',
            empresa_owner=empresa,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco de Chile',
            numero_cuenta='8240144702',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo='activa',
        )
        mandate = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='interna',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            vigencia_desde='2026-01-01',
            estado='activa',
        )
        tenant = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Tenant Uno',
            rut='11111111-1',
            email='tenant@example.com',
        )

        bundle = {
            'patrimonio': {
                'socios': [
                    {
                        'legacy_id': 'soc-1',
                        'rut': '17366287-4',
                        'nombre': 'Socio Uno',
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    }
                ],
                'empresas': [
                    {
                        'legacy_id': 'emp-1',
                        'rut': '76311245-4',
                        'razon_social': 'Inmobiliaria Puig SpA',
                        'domicilio': '',
                        'giro': '',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    }
                ],
                'comunidades': [],
                'participaciones': [
                    {
                        'legacy_id': 'par-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-1',
                        'socio_legacy_id': 'soc-1',
                        'porcentaje': '100.00',
                        'vigente_desde': '2026-01-01',
                        'vigente_hasta': None,
                        'activo': True,
                    }
                ],
                'propiedades': [
                    {
                        'legacy_id': 'prop-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-1',
                        'rol_avaluo': '123-1',
                        'direccion': 'Av Uno 123',
                        'comuna': 'Santiago',
                        'region': '',
                        'tipo_inmueble': 'local',
                        'codigo_propiedad': '001',
                        'estado': 'activa',
                        'legacy_estado': 'arrendada',
                    }
                ],
            },
            'operacion': {
                'cuentas_recaudadoras': [
                    {
                        'legacy_id': 'cta-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-1',
                        'institucion': 'Banco de Chile',
                        'numero_cuenta': '8240144702',
                        'tipo_cuenta': 'corriente',
                        'titular_nombre': 'Inmobiliaria Puig SpA',
                        'titular_rut': '76311245-4',
                        'moneda_operativa': 'CLP',
                        'estado_operativo': 'activa',
                    }
                ]
            },
            'contratos': {
                'arrendatarios': [
                    {
                        'legacy_id': 'arr-1',
                        'tipo_arrendatario': 'persona_natural',
                        'nombre_razon_social': 'Tenant Uno',
                        'rut': '11111111-1',
                        'email': 'tenant@example.com',
                        'telefono': '',
                        'domicilio_notificaciones': '',
                        'estado_contacto': 'activo',
                        'whatsapp_bloqueado': False,
                    }
                ],
                'contratos_candidates': [
                    {
                        'legacy_id': 'ctr-1',
                        'arrendatario_legacy_id': 'arr-1',
                        'propiedad_legacy_id': 'prop-1',
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin_vigente': '2026-12-31',
                        'fecha_entrega': '2026-01-01',
                        'dia_pago_mensual': 5,
                        'plazo_notificacion_termino_dias': 60,
                        'dias_prealerta_admin': 90,
                        'estado_legacy': 'activo',
                        'aviso_termino_registrado': True,
                        'fecha_aviso_termino': '2026-11-01',
                        'notas_aviso_termino': 'No renovar',
                    }
                ],
                'periodos_candidates': [
                    {
                        'legacy_id': 'per-1',
                        'legacy_contrato_id': 'ctr-1',
                        'numero_periodo': 1,
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin': '2026-12-31',
                        'monto_base': '100000.00',
                        'moneda_base': 'CLP',
                    }
                ],
            },
            'unresolved': {},
        }

        report = import_bundle(bundle)
        self.assertEqual(report.created.get('contratos', 0), 1)
        contrato = Contrato.objects.get(codigo_contrato='LEGACY-ctr-1')
        self.assertEqual(contrato.mandato_operacion, mandate)
        self.assertEqual(ContratoPropiedad.objects.filter(contrato=contrato).count(), 1)
        self.assertEqual(PeriodoContractual.objects.filter(contrato=contrato).count(), 1)
        self.assertEqual(AvisoTermino.objects.filter(contrato=contrato, estado='registrado').count(), 1)

        report_again = import_bundle(bundle)
        self.assertEqual(report_again.updated.get('contrato_propiedades', 0), 1)

    def test_import_bundle_derives_active_mandate_for_company_owned_property(self):
        bundle = {
            'patrimonio': {
                'socios': [
                    {
                        'legacy_id': 'soc-1',
                        'rut': '17366287-4',
                        'nombre': 'Socio Uno',
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    }
                ],
                'empresas': [
                    {
                        'legacy_id': 'emp-1',
                        'rut': '76311245-4',
                        'razon_social': 'Inmobiliaria Puig SpA',
                        'domicilio': '',
                        'giro': '',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    }
                ],
                'comunidades': [],
                'participaciones': [
                    {
                        'legacy_id': 'par-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-1',
                        'socio_legacy_id': 'soc-1',
                        'porcentaje': '100.00',
                        'vigente_desde': '2026-01-01',
                        'vigente_hasta': None,
                        'activo': True,
                    }
                ],
                'propiedades': [
                    {
                        'legacy_id': 'prop-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-1',
                        'rol_avaluo': '123-1',
                        'direccion': 'Av Uno 123',
                        'comuna': 'Santiago',
                        'region': '',
                        'tipo_inmueble': 'local',
                        'codigo_propiedad': '001',
                        'estado': 'activa',
                        'legacy_estado': 'arrendada',
                    }
                ],
            },
            'operacion': {
                'cuentas_recaudadoras': [
                    {
                        'legacy_id': 'cta-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-1',
                        'institucion': 'Banco de Chile',
                        'numero_cuenta': '8240144702',
                        'tipo_cuenta': 'corriente',
                        'titular_nombre': 'Inmobiliaria Puig SpA',
                        'titular_rut': '76311245-4',
                        'moneda_operativa': 'CLP',
                        'estado_operativo': 'activa',
                    }
                ]
            },
            'contratos': {'arrendatarios': [], 'contratos_candidates': [], 'periodos_candidates': []},
            'unresolved': {},
        }

        report = import_bundle(bundle)
        self.assertEqual(report.created.get('mandatos_operacion', 0), 1)
        mandate = MandatoOperacion.objects.get()
        self.assertEqual(mandate.tipo_relacion_operativa, 'legacy_import_auto')
        self.assertEqual(mandate.estado, 'activa')

    def test_import_bundle_derives_active_mandate_for_socio_owned_property(self):
        bundle = {
            'patrimonio': {
                'socios': [
                    {
                        'legacy_id': 'soc-1',
                        'rut': '17.366.287-4',
                        'nombre': 'Joaquin Puig Vittini',
                        'email': 'jp@example.com',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    }
                ],
                'empresas': [],
                'comunidades': [],
                'participaciones': [],
                'propiedades': [
                    {
                        'legacy_id': 'prop-1',
                        'owner_kind': 'socio',
                        'owner_legacy_id': 'soc-1',
                        'rol_avaluo': '123-1',
                        'direccion': 'Av. Los Pablos 1950, Estacionamiento E49',
                        'comuna': 'Santiago',
                        'region': '',
                        'tipo_inmueble': 'estacionamiento',
                        'codigo_propiedad': '15',
                        'estado': 'activa',
                        'legacy_estado': 'arrendada',
                    }
                ],
            },
            'operacion': {
                'cuentas_recaudadoras': [
                    {
                        'legacy_id': 'cta-1',
                        'owner_kind': 'socio',
                        'owner_legacy_id': 'soc-1',
                        'institucion': 'Banco de Chile',
                        'numero_cuenta': '8240131105',
                        'tipo_cuenta': 'corriente',
                        'titular_nombre': 'Joaquin Puig Vittini',
                        'titular_rut': '17.366.287-4',
                        'moneda_operativa': 'CLP',
                        'estado_operativo': 'activa',
                    }
                ]
            },
            'contratos': {'arrendatarios': [], 'contratos_candidates': [], 'periodos_candidates': []},
            'unresolved': {},
        }

        report = import_bundle(bundle)

        self.assertEqual(report.created.get('mandatos_operacion', 0), 1)
        mandate = MandatoOperacion.objects.get()
        self.assertEqual(mandate.propietario_tipo, 'socio')
        self.assertEqual(mandate.administrador_operativo_tipo, 'socio')
        self.assertFalse(mandate.autoriza_facturacion)

    def test_import_bundle_derives_active_mandate_for_standard_community_property(self):
        bundle = {
            'patrimonio': {
                'socios': [
                    {
                        'legacy_id': 'soc-joaquin',
                        'rut': '17.366.287-4',
                        'nombre': 'Joaquin Puig Vittini',
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    },
                    {
                        'legacy_id': 'soc-1',
                        'rut': '7.768.066-7',
                        'nombre': 'Cecilia Jacqueline Vittini De Ruyt',
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    },
                ],
                'empresas': [
                    {
                        'legacy_id': 'emp-santamaria',
                        'rut': '76.124.381-0',
                        'razon_social': 'Sociedad Inmobiliaria Santa María Ltda',
                        'domicilio': '',
                        'giro': '',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    }
                ],
                'comunidades': [
                    {
                        'legacy_id': 'com-1',
                        'nombre': 'Basilio Urrutia 633',
                        'descripcion': '',
                        'estado': 'activa',
                        'representante_legacy_id': 'soc-joaquin',
                        'representacion_sugerida': {
                            'modo_representacion': 'designado',
                            'socio_legacy_id': 'soc-joaquin',
                        },
                    }
                ],
                'participaciones': [
                    {
                        'legacy_id': 'par-1',
                        'owner_kind': 'comunidad',
                        'owner_legacy_id': 'com-1',
                        'participante_kind': 'socio',
                        'participante_legacy_id': 'soc-1',
                        'porcentaje': '100.00',
                        'vigente_desde': '2017-03-16',
                        'vigente_hasta': None,
                        'activo': True,
                    }
                ],
                'propiedades': [
                    {
                        'legacy_id': 'prop-1',
                        'owner_kind': 'comunidad',
                        'owner_legacy_id': 'com-1',
                        'rol_avaluo': '597-005',
                        'direccion': 'Basilio Urrutia 633',
                        'comuna': 'Temuco',
                        'region': 'La Araucania',
                        'tipo_inmueble': 'otro',
                        'codigo_propiedad': '5',
                        'estado': 'activa',
                        'legacy_estado': 'arrendada',
                    }
                ],
            },
            'operacion': {
                'cuentas_recaudadoras': [
                    {
                        'legacy_id': 'cta-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-santamaria',
                        'institucion': 'Banco de Chile',
                        'numero_cuenta': '8240452907',
                        'tipo_cuenta': 'corriente',
                        'titular_nombre': 'Sociedad Inmobiliaria Santa María Ltda',
                        'titular_rut': '76.124.381-0',
                        'moneda_operativa': 'CLP',
                        'estado_operativo': 'activa',
                    }
                ]
            },
            'contratos': {'arrendatarios': [], 'contratos_candidates': [], 'periodos_candidates': []},
            'unresolved': {},
        }

        report = import_bundle(bundle)
        self.assertEqual(report.created.get('mandatos_operacion', 0), 1)
        mandate = MandatoOperacion.objects.get()
        self.assertEqual(mandate.propietario_tipo, 'comunidad')
        self.assertEqual(mandate.administrador_operativo_tipo, 'socio')
        self.assertEqual(mandate.recaudador_tipo, 'empresa')
        self.assertEqual(mandate.cuenta_recaudadora.numero_cuenta, '8240452907')
        self.assertIsNone(mandate.entidad_facturadora_id)

    def test_import_bundle_derives_active_mandate_for_mixed_community_property(self):
        bundle = {
            'patrimonio': {
                'socios': [
                    {
                        'legacy_id': 'soc-joaquin',
                        'rut': '17.366.287-4',
                        'nombre': 'Joaquin Puig Vittini',
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    },
                    {
                        'legacy_id': 'soc-1',
                        'rut': '7.768.066-7',
                        'nombre': 'Cecilia Jacqueline Vittini De Ruyt',
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    },
                ],
                'empresas': [
                    {
                        'legacy_id': 'emp-santamaria',
                        'rut': '76.124.381-0',
                        'razon_social': 'Sociedad Inmobiliaria Santa María Ltda',
                        'domicilio': '',
                        'giro': '',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    },
                    {
                        'legacy_id': 'emp-inmopuig',
                        'rut': '76.311.245-4',
                        'razon_social': 'Inmobiliaria Puig SpA',
                        'domicilio': '',
                        'giro': '',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    }
                ],
                'comunidades': [
                    {
                        'legacy_id': 'com-1',
                        'nombre': 'Edificio Q Dpto 1014',
                        'descripcion': '',
                        'estado': 'activa',
                        'representante_legacy_id': 'soc-joaquin',
                        'representacion_sugerida': {
                            'modo_representacion': 'designado',
                            'socio_legacy_id': 'soc-joaquin',
                        },
                    }
                ],
                'participaciones': [
                    {
                        'legacy_id': 'par-1',
                        'owner_kind': 'comunidad',
                        'owner_legacy_id': 'com-1',
                        'participante_kind': 'socio',
                        'participante_legacy_id': 'soc-1',
                        'porcentaje': '83.34',
                        'vigente_desde': '2017-03-16',
                        'vigente_hasta': None,
                        'activo': True,
                    },
                    {
                        'legacy_id': 'par-2',
                        'owner_kind': 'comunidad',
                        'owner_legacy_id': 'com-1',
                        'participante_kind': 'empresa',
                        'participante_legacy_id': 'emp-inmopuig',
                        'porcentaje': '16.66',
                        'vigente_desde': '2017-03-16',
                        'vigente_hasta': None,
                        'activo': True,
                    }
                ],
                'propiedades': [
                    {
                        'legacy_id': 'prop-1',
                        'owner_kind': 'comunidad',
                        'owner_legacy_id': 'com-1',
                        'rol_avaluo': '1338-268',
                        'direccion': 'Edificio Q Dpto 1014',
                        'comuna': 'Temuco',
                        'region': 'La Araucania',
                        'tipo_inmueble': 'otro',
                        'codigo_propiedad': '46',
                        'estado': 'activa',
                        'legacy_estado': 'arrendada',
                    }
                ],
            },
            'operacion': {
                'cuentas_recaudadoras': [
                    {
                        'legacy_id': 'cta-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-santamaria',
                        'institucion': 'Banco de Chile',
                        'numero_cuenta': '8240452907',
                        'tipo_cuenta': 'corriente',
                        'titular_nombre': 'Sociedad Inmobiliaria Santa María Ltda',
                        'titular_rut': '76.124.381-0',
                        'moneda_operativa': 'CLP',
                        'estado_operativo': 'activa',
                    }
                ]
            },
            'contratos': {'arrendatarios': [], 'contratos_candidates': [], 'periodos_candidates': []},
            'unresolved': {},
        }

        report = import_bundle(bundle)
        self.assertEqual(report.created.get('mandatos_operacion', 0), 1)
        mandate = MandatoOperacion.objects.get()
        self.assertEqual(mandate.propietario_tipo, 'comunidad')
        self.assertEqual(mandate.administrador_operativo_tipo, 'socio')
        self.assertEqual(mandate.recaudador_tipo, 'empresa')
        self.assertEqual(mandate.entidad_facturadora.razon_social, 'Inmobiliaria Puig SpA')

    def test_import_bundle_creates_manual_resolution_for_unresolved_property_owner(self):
        bundle = {
            'patrimonio': {'socios': [], 'empresas': [], 'comunidades': [], 'participaciones': [], 'propiedades': []},
            'operacion': {'cuentas_recaudadoras': []},
            'contratos': {'arrendatarios': [], 'contratos_candidates': [], 'periodos_candidates': []},
            'unresolved': {
                'propiedades_sin_owner': [
                    {
                        'legacy_id': 'prop-1',
                        'reason': 'No owner found in legacy row.',
                        'codigo': 46,
                        'direccion': 'Av. Santa Maria 9500 Dpto 1014',
                        'candidate_owner_model': 'comunidad',
                        'participaciones_count': 2,
                        'total_pct': 100.0,
                        'socios': [
                            {'socio_legacy_id': 'soc-1', 'socio_nombre': 'Socio Uno', 'porcentaje': '50'},
                            {'socio_legacy_id': 'soc-2', 'socio_nombre': 'Socio Dos', 'porcentaje': '50'},
                        ],
                    }
                ]
            },
        }

        report = import_bundle(bundle)
        self.assertEqual(report.created.get('manual_resolutions', 0), 1)
        resolution = ManualResolution.objects.get()
        self.assertEqual(resolution.category, 'migration.propiedad.owner_manual_required')
        self.assertEqual(resolution.scope_reference, 'prop-1')

        report_again = import_bundle(bundle)
        self.assertEqual(ManualResolution.objects.count(), 1)
        self.assertGreaterEqual(report_again.updated.get('manual_resolutions', 0), 1)

    def test_import_bundle_uses_resolved_manual_resolution_property_for_contract_import(self):
        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1')
        socio_2 = Socio.objects.create(nombre='Socio Dos', rut='22222222-2')
        comunidad = ComunidadPatrimonial.objects.create(
            nombre='Comunidad Av Santa Maria 9500 Dpto 1014',
            estado='activa',
        )
        RepresentacionComunidad.objects.create(
            comunidad=comunidad,
            modo_representacion=ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
            socio_representante=socio_1,
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_1,
            comunidad_owner=comunidad,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_2,
            comunidad_owner=comunidad,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        propiedad = Propiedad.objects.create(
            codigo_propiedad='46',
            rol_avaluo='123-1',
            direccion='Av. Santa Maria 9500 Dpto 1014',
            comuna='Santiago',
            region='',
            tipo_inmueble='departamento',
            estado='activa',
            comunidad_owner=comunidad,
        )
        empresa_admin = Empresa.objects.create(razon_social='San Cristobal Ltda', rut='76390560-8', estado='activa')
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa_admin,
            institucion='Banco de Chile',
            numero_cuenta='1440147402',
            tipo_cuenta='corriente',
            titular_nombre=empresa_admin.razon_social,
            titular_rut=empresa_admin.rut,
            moneda_operativa='CLP',
            estado_operativo='activa',
        )
        MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_comunidad_owner=comunidad,
            administrador_empresa_owner=empresa_admin,
            recaudador_empresa_owner=empresa_admin,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_comunicacion=True,
            estado='activa',
            vigencia_desde='2026-01-01',
        )
        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-1',
            summary='Owner manual',
            status='resolved',
            metadata={
                'resolved_canonical_comunidad_id': comunidad.pk,
                'resolved_canonical_property_id': propiedad.pk,
            },
        )
        self.assertIsNotNone(resolution.pk)
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social='Tenant Uno',
            rut='33333333-3',
            email='tenant@example.com',
        )

        bundle = {
            'patrimonio': {'socios': [], 'empresas': [], 'comunidades': [], 'participaciones': [], 'propiedades': []},
            'operacion': {'cuentas_recaudadoras': []},
            'contratos': {
                'arrendatarios': [
                    {
                        'legacy_id': 'arr-1',
                        'tipo_arrendatario': 'persona_natural',
                        'nombre_razon_social': 'Tenant Uno',
                        'rut': '33.333.333-3',
                        'email': 'tenant@example.com',
                        'telefono': '',
                        'domicilio_notificaciones': '',
                        'estado_contacto': 'activo',
                        'whatsapp_bloqueado': False,
                    }
                ],
                'contratos_candidates': [
                    {
                        'legacy_id': 'ctr-1',
                        'arrendatario_legacy_id': 'arr-1',
                        'propiedad_legacy_id': 'prop-legacy-1',
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin_vigente': '2026-12-31',
                        'fecha_entrega': '2026-01-01',
                        'dia_pago_mensual': 5,
                        'plazo_notificacion_termino_dias': 60,
                        'dias_prealerta_admin': 90,
                        'estado_legacy': 'activo',
                        'aviso_termino_registrado': False,
                        'fecha_aviso_termino': None,
                        'notas_aviso_termino': '',
                    }
                ],
                'periodos_candidates': [
                    {
                        'legacy_id': 'per-1',
                        'legacy_contrato_id': 'ctr-1',
                        'numero_periodo': 1,
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin': '2026-12-31',
                        'monto_base': '100000.00',
                        'moneda_base': 'CLP',
                    }
                ],
            },
            'unresolved': {},
        }

        report = import_bundle(bundle)
        self.assertEqual(report.created.get('contratos', 0), 1)
        self.assertEqual(report.created.get('periodos_contractuales', 0), 1)

    def test_import_bundle_supports_company_participant_in_community_bundle(self):
        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        empresa = Empresa.objects.create(razon_social='Inmobiliaria Puig SpA', rut='76311245-4', estado='activa')
        socio_empresa_1 = Socio.objects.create(nombre='Socio Empresa Uno', rut='44444444-4', activo=True)
        socio_empresa_2 = Socio.objects.create(nombre='Socio Empresa Dos', rut='55555555-5', activo=True)
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_empresa_1,
            empresa_owner=empresa,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_empresa_2,
            empresa_owner=empresa,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )

        bundle = {
            'patrimonio': {
                'socios': [
                    {
                        'legacy_id': 'soc-1',
                        'rut': socio_1.rut,
                        'nombre': socio_1.nombre,
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    }
                ],
                'empresas': [
                    {
                        'legacy_id': 'emp-1',
                        'rut': empresa.rut,
                        'razon_social': empresa.razon_social,
                        'domicilio': '',
                        'giro': '',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    }
                ],
                'comunidades': [
                    {
                        'legacy_id': 'com-1',
                        'nombre': 'Comunidad Mixta',
                        'descripcion': '',
                        'estado': 'activa',
                        'representante_legacy_id': 'soc-1',
                        'representacion_sugerida': {
                            'modo_representacion': 'participante_patrimonial',
                            'socio_legacy_id': 'soc-1',
                        },
                    }
                ],
                'participaciones': [
                    {
                        'legacy_id': 'par-1',
                        'owner_kind': 'comunidad',
                        'owner_legacy_id': 'com-1',
                        'participante_kind': 'socio',
                        'participante_legacy_id': 'soc-1',
                        'socio_legacy_id': 'soc-1',
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'vigente_hasta': None,
                        'activo': True,
                    },
                    {
                        'legacy_id': 'par-2',
                        'owner_kind': 'comunidad',
                        'owner_legacy_id': 'com-1',
                        'participante_kind': 'empresa',
                        'participante_legacy_id': 'emp-1',
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'vigente_hasta': None,
                        'activo': True,
                    },
                ],
                'propiedades': [],
            },
            'operacion': {'cuentas_recaudadoras': []},
            'contratos': {'arrendatarios': [], 'contratos_candidates': [], 'periodos_candidates': []},
            'unresolved': {},
        }

        report = import_bundle(bundle)
        self.assertEqual(report.created.get('comunidades', 0), 1)
        comunidad = ComunidadPatrimonial.objects.get(nombre='Comunidad Mixta')
        participant_types = {item.participante_tipo for item in comunidad.participaciones.all()}
        self.assertEqual(participant_types, {'socio', 'empresa'})

    def test_resolve_current_community_manual_resolutions_supports_rerun_import_for_mixed_community(self):
        bundle = {
            'patrimonio': {
                'socios': [
                    {
                        'legacy_id': 'soc-joaquin',
                        'rut': '17.366.287-4',
                        'nombre': 'Joaquin Puig Vittini',
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    },
                    {
                        'legacy_id': 'soc-cecilia',
                        'rut': '7.768.066-7',
                        'nombre': 'Cecilia Jacqueline Vittini De Ruyt',
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    },
                ],
                'empresas': [
                    {
                        'legacy_id': 'emp-santa-maria',
                        'rut': '76.124.381-0',
                        'razon_social': 'Santa Maria Ltda',
                        'domicilio': '',
                        'giro': '',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    },
                    {
                        'legacy_id': 'emp-inmo-puig',
                        'rut': '76.311.245-4',
                        'razon_social': 'Inmobiliaria Puig SpA',
                        'domicilio': '',
                        'giro': '',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    },
                ],
                'comunidades': [],
                'participaciones': [],
                'propiedades': [],
            },
            'operacion': {
                'cuentas_recaudadoras': [
                    {
                        'legacy_id': 'acct-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-santa-maria',
                        'institucion': 'Banco de Chile',
                        'numero_cuenta': '8240452907',
                        'tipo_cuenta': 'corriente',
                        'titular_nombre': 'Santa Maria Ltda',
                        'titular_rut': '76.124.381-0',
                        'moneda_operativa': 'CLP',
                        'estado_operativo': 'activa',
                    }
                ]
            },
            'contratos': {
                'arrendatarios': [
                    {
                        'legacy_id': 'arr-1',
                        'tipo_arrendatario': 'persona_natural',
                        'nombre_razon_social': 'Tenant Uno',
                        'rut': '33.333.333-3',
                        'email': 'tenant@example.com',
                        'telefono': '',
                        'domicilio_notificaciones': '',
                        'estado_contacto': 'activo',
                        'whatsapp_bloqueado': False,
                    }
                ],
                'contratos_candidates': [
                    {
                        'legacy_id': 'ctr-1',
                        'arrendatario_legacy_id': 'arr-1',
                        'propiedad_legacy_id': 'prop-edificio-q',
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin_vigente': '2026-12-31',
                        'fecha_entrega': '2026-01-01',
                        'dia_pago_mensual': 5,
                        'plazo_notificacion_termino_dias': 60,
                        'dias_prealerta_admin': 90,
                        'estado_legacy': 'activo',
                        'aviso_termino_registrado': False,
                        'fecha_aviso_termino': None,
                        'notas_aviso_termino': '',
                    }
                ],
                'periodos_candidates': [
                    {
                        'legacy_id': 'per-1',
                        'legacy_contrato_id': 'ctr-1',
                        'numero_periodo': 1,
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin': '2026-12-31',
                        'monto_base': '100000.00',
                        'moneda_base': 'CLP',
                    }
                ],
            },
            'unresolved': {
                'propiedades_sin_owner': [
                    {
                        'legacy_id': 'prop-edificio-q',
                        'reason': 'No owner found in legacy row.',
                        'codigo': 46,
                        'codigo_propiedad': None,
                        'direccion': 'Edificio Q Dpto 1014',
                        'estado': 'arrendada',
                        'canonical_estado': 'activa',
                        'rol_avaluo': '1338-268',
                        'comuna': 'Temuco',
                        'region': 'La Araucania',
                        'tipo_inmueble': 'otro',
                        'candidate_owner_model': 'comunidad',
                        'participantes': [
                            {
                                'participante_tipo': 'socio',
                                'participante_rut': '7.768.066-7',
                                'porcentaje': '50.00',
                                'activo': True,
                                'vigente_desde': '2017-03-16',
                                'vigente_hasta': None,
                            },
                            {
                                'participante_tipo': 'empresa',
                                'participante_rut': '76.311.245-4',
                                'porcentaje': '50.00',
                                'activo': True,
                                'vigente_desde': '2017-03-16',
                                'vigente_hasta': None,
                            },
                        ],
                    }
                ]
            },
        }

        first_report = import_bundle(bundle)
        self.assertEqual(first_report.created.get('manual_resolutions', 0), 1)
        resolution_result = resolve_current_community_manual_resolutions()
        self.assertEqual(resolution_result['resolved'], 1)
        self.assertEqual(resolution_result['skipped'], [])

        second_report = import_bundle(bundle)
        self.assertEqual(second_report.created.get('contratos', 0), 1)
        self.assertEqual(second_report.created.get('periodos_contractuales', 0), 1)

        comunidad = ComunidadPatrimonial.objects.get(nombre='Edificio Q Dpto 1014')
        self.assertEqual(comunidad.participaciones_activas().count(), 2)
        mandate = MandatoOperacion.objects.get(propiedad__direccion='Edificio Q Dpto 1014')
        self.assertEqual(mandate.entidad_facturadora.razon_social, 'Inmobiliaria Puig SpA')

    def test_run_current_migration_flow_executes_validated_sequence(self):
        bundle = {
            'patrimonio': {
                'socios': [
                    {
                        'legacy_id': 'soc-joaquin',
                        'rut': '17.366.287-4',
                        'nombre': 'Joaquin Puig Vittini',
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    },
                    {
                        'legacy_id': 'soc-cecilia',
                        'rut': '7.768.066-7',
                        'nombre': 'Cecilia Jacqueline Vittini De Ruyt',
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    },
                ],
                'empresas': [
                    {
                        'legacy_id': 'emp-santa-maria',
                        'rut': '76.124.381-0',
                        'razon_social': 'Santa Maria Ltda',
                        'domicilio': '',
                        'giro': '',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    },
                    {
                        'legacy_id': 'emp-inmo-puig',
                        'rut': '76.311.245-4',
                        'razon_social': 'Inmobiliaria Puig SpA',
                        'domicilio': '',
                        'giro': '',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    },
                ],
                'comunidades': [],
                'participaciones': [],
                'propiedades': [],
            },
            'operacion': {
                'cuentas_recaudadoras': [
                    {
                        'legacy_id': 'acct-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-santa-maria',
                        'institucion': 'Banco de Chile',
                        'numero_cuenta': '8240452907',
                        'tipo_cuenta': 'corriente',
                        'titular_nombre': 'Santa Maria Ltda',
                        'titular_rut': '76.124.381-0',
                        'moneda_operativa': 'CLP',
                        'estado_operativo': 'activa',
                    }
                ]
            },
            'contratos': {
                'arrendatarios': [
                    {
                        'legacy_id': 'arr-1',
                        'tipo_arrendatario': 'persona_natural',
                        'nombre_razon_social': 'Tenant Uno',
                        'rut': '33.333.333-3',
                        'email': 'tenant@example.com',
                        'telefono': '',
                        'domicilio_notificaciones': '',
                        'estado_contacto': 'activo',
                        'whatsapp_bloqueado': False,
                    }
                ],
                'contratos_candidates': [
                    {
                        'legacy_id': 'ctr-1',
                        'arrendatario_legacy_id': 'arr-1',
                        'propiedad_legacy_id': 'prop-edificio-q',
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin_vigente': '2026-12-31',
                        'fecha_entrega': '2026-01-01',
                        'dia_pago_mensual': 5,
                        'plazo_notificacion_termino_dias': 60,
                        'dias_prealerta_admin': 90,
                        'estado_legacy': 'activo',
                        'aviso_termino_registrado': False,
                        'fecha_aviso_termino': None,
                        'notas_aviso_termino': '',
                    }
                ],
                'periodos_candidates': [
                    {
                        'legacy_id': 'per-1',
                        'legacy_contrato_id': 'ctr-1',
                        'numero_periodo': 1,
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin': '2026-12-31',
                        'monto_base': '100000.00',
                        'moneda_base': 'CLP',
                    }
                ],
            },
            'unresolved': {
                'propiedades_sin_owner': [
                    {
                        'legacy_id': 'prop-edificio-q',
                        'reason': 'No owner found in legacy row.',
                        'codigo': 46,
                        'codigo_propiedad': None,
                        'direccion': 'Edificio Q Dpto 1014',
                        'estado': 'arrendada',
                        'canonical_estado': 'activa',
                        'rol_avaluo': '1338-268',
                        'comuna': 'Temuco',
                        'region': 'La Araucania',
                        'tipo_inmueble': 'otro',
                        'candidate_owner_model': 'comunidad',
                        'participantes': [
                            {
                                'participante_tipo': 'socio',
                                'participante_rut': '7.768.066-7',
                                'porcentaje': '50.00',
                                'activo': True,
                                'vigente_desde': '2017-03-16',
                                'vigente_hasta': None,
                            },
                            {
                                'participante_tipo': 'empresa',
                                'participante_rut': '76.311.245-4',
                                'porcentaje': '50.00',
                                'activo': True,
                                'vigente_desde': '2017-03-16',
                                'vigente_hasta': None,
                            },
                        ],
                    }
                ]
            },
        }

        result = run_current_migration_flow(bundle)

        self.assertEqual(result['community_resolution']['resolved'], 1)
        self.assertEqual(result['community_resolution']['skipped'], [])
        self.assertEqual(result['final_state'], collect_migration_state_snapshot())
        self.assertEqual(result['final_state']['manual_resolutions_abiertas'], 0)
        self.assertEqual(result['final_state']['manual_resolutions_resueltas'], 1)
        self.assertEqual(result['final_state']['contratos'], 1)
        self.assertEqual(result['final_state']['periodos'], 1)
        self.assertEqual(result['final_state']['mandatos'], 1)

    def test_import_bundle_rerun_preserves_resolved_community_participations_and_facturadora(self):
        bundle = {
            'patrimonio': {
                'socios': [
                    {
                        'legacy_id': 'soc-joaquin',
                        'rut': '17.366.287-4',
                        'nombre': 'Joaquin Puig Vittini',
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    },
                    {
                        'legacy_id': 'soc-cecilia',
                        'rut': '7.768.066-7',
                        'nombre': 'Cecilia Jacqueline Vittini De Ruyt',
                        'email': '',
                        'telefono': '',
                        'domicilio': '',
                        'activo': True,
                    },
                ],
                'empresas': [
                    {
                        'legacy_id': 'emp-santa-maria',
                        'rut': '76.124.381-0',
                        'razon_social': 'Santa Maria Ltda',
                        'domicilio': '',
                        'giro': '',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    },
                    {
                        'legacy_id': 'emp-inmo-puig',
                        'rut': '76.311.245-4',
                        'razon_social': 'Inmobiliaria Puig SpA',
                        'domicilio': '',
                        'giro': '',
                        'codigo_actividad_sii': '',
                        'estado': 'activa',
                    },
                ],
                'comunidades': [],
                'participaciones': [],
                'propiedades': [],
            },
            'operacion': {
                'cuentas_recaudadoras': [
                    {
                        'legacy_id': 'acct-1',
                        'owner_kind': 'empresa',
                        'owner_legacy_id': 'emp-santa-maria',
                        'institucion': 'Banco de Chile',
                        'numero_cuenta': '8240452907',
                        'tipo_cuenta': 'corriente',
                        'titular_nombre': 'Santa Maria Ltda',
                        'titular_rut': '76.124.381-0',
                        'moneda_operativa': 'CLP',
                        'estado_operativo': 'activa',
                    }
                ]
            },
            'contratos': {
                'arrendatarios': [
                    {
                        'legacy_id': 'arr-1',
                        'tipo_arrendatario': 'persona_natural',
                        'nombre_razon_social': 'Tenant Uno',
                        'rut': '33.333.333-3',
                        'email': 'tenant@example.com',
                        'telefono': '',
                        'domicilio_notificaciones': '',
                        'estado_contacto': 'activo',
                        'whatsapp_bloqueado': False,
                    }
                ],
                'contratos_candidates': [
                    {
                        'legacy_id': 'ctr-1',
                        'arrendatario_legacy_id': 'arr-1',
                        'propiedad_legacy_id': 'prop-edificio-q',
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin_vigente': '2026-12-31',
                        'fecha_entrega': '2026-01-01',
                        'dia_pago_mensual': 5,
                        'plazo_notificacion_termino_dias': 60,
                        'dias_prealerta_admin': 90,
                        'estado_legacy': 'activo',
                        'aviso_termino_registrado': False,
                        'fecha_aviso_termino': None,
                        'notas_aviso_termino': '',
                    }
                ],
                'periodos_candidates': [
                    {
                        'legacy_id': 'per-1',
                        'legacy_contrato_id': 'ctr-1',
                        'numero_periodo': 1,
                        'fecha_inicio': '2026-01-01',
                        'fecha_fin': '2026-12-31',
                        'monto_base': '100000.00',
                        'moneda_base': 'CLP',
                    }
                ],
            },
            'unresolved': {
                'propiedades_sin_owner': [
                    {
                        'legacy_id': 'prop-edificio-q',
                        'reason': 'No owner found in legacy row.',
                        'codigo': 46,
                        'codigo_propiedad': None,
                        'direccion': 'Edificio Q Dpto 1014',
                        'estado': 'arrendada',
                        'canonical_estado': 'activa',
                        'rol_avaluo': '1338-268',
                        'comuna': 'Temuco',
                        'region': 'La Araucania',
                        'tipo_inmueble': 'otro',
                        'candidate_owner_model': 'comunidad',
                        'participantes': [
                            {
                                'participante_tipo': 'socio',
                                'participante_rut': '7.768.066-7',
                                'porcentaje': '50.00',
                                'activo': True,
                                'vigente_desde': '2017-03-16',
                                'vigente_hasta': None,
                            },
                            {
                                'participante_tipo': 'empresa',
                                'participante_rut': '76.311.245-4',
                                'porcentaje': '50.00',
                                'activo': True,
                                'vigente_desde': '2017-03-16',
                                'vigente_hasta': None,
                            },
                        ],
                        'representacion_sugerida': {
                            'modo_representacion': 'designado',
                            'socio_rut': '17.366.287-4',
                        },
                    }
                ]
            },
        }

        first_report = import_bundle(bundle)
        self.assertEqual(first_report.created.get('manual_resolutions', 0), 1)
        resolution = ManualResolution.objects.get(category='migration.propiedad.owner_manual_required')
        joaquin = Socio.objects.get(rut='17366287-4')
        resolve_migration_property_owner_manual_resolution(
            resolution=resolution,
            nombre_comunidad='Edificio Q Dpto 1014',
            representante_socio_id=joaquin.pk,
            representante_modo=ModoRepresentacionComunidad.DESIGNATED,
            region='La Araucania',
        )

        second_report = import_bundle(bundle)
        self.assertEqual(second_report.created.get('contratos', 0), 1)
        self.assertEqual(second_report.created.get('periodos_contractuales', 0), 1)

        comunidad = ComunidadPatrimonial.objects.get(nombre='Edificio Q Dpto 1014')
        self.assertEqual(comunidad.participaciones_activas().count(), 2)
        mandate = MandatoOperacion.objects.get(propiedad__direccion='Edificio Q Dpto 1014')
        self.assertEqual(mandate.entidad_facturadora.razon_social, 'Inmobiliaria Puig SpA')

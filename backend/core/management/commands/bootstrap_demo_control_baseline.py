from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from contabilidad.models import (
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EstadoRegistro,
    MatrizReglasContables,
    NaturalezaCuenta,
    RegimenTributarioEmpresa,
    ReglaContable,
)
from patrimonio.models import Empresa
from sii.models import AmbienteSII, CapacidadSII, CapacidadTributariaSII, EstadoGateSII


DEFAULT_PLAN_VERSION = "v1-default"
DEFAULT_REGIME_CODE = "EmpresaContabilidadCompletaV1"

DEFAULT_ACCOUNTS = (
    ("1101", "Bancos", NaturalezaCuenta.DEBIT, 1, True),
    ("1102", "CuentasPorCobrarArriendos", NaturalezaCuenta.DEBIT, 1, True),
    ("1103", "CuentasPorCobrarCobranzaResidual", NaturalezaCuenta.DEBIT, 1, True),
    ("2101", "GarantiasRecibidas", NaturalezaCuenta.CREDIT, 1, True),
    ("2102", "PPM_por_Pagar", NaturalezaCuenta.CREDIT, 1, True),
    ("4101", "IngresosPorArriendo", NaturalezaCuenta.CREDIT, 1, True),
    ("4102", "RecuperacionGastosComunes", NaturalezaCuenta.CREDIT, 1, False),
    ("4103", "OtrosIngresosOperacionales", NaturalezaCuenta.CREDIT, 1, False),
    ("5101", "ComisionesBancarias", NaturalezaCuenta.DEBIT, 1, True),
)

DEFAULT_RULES = (
    ("PagoConciliadoArriendo", "1101", "1102"),
    ("GarantiaRecibida", "1101", "2101"),
    ("GarantiaDevuelta", "2101", "1101"),
    ("GarantiaAplicadaADeuda", "2101", "1103"),
    ("ComisionBancaria", "5101", "1101"),
)

DEFAULT_SII_CAPABILITIES = (
    CapacidadSII.DTE_EMISION,
    CapacidadSII.F29_PREPARACION,
    CapacidadSII.DDJJ_PREPARACION,
    CapacidadSII.F22_PREPARACION,
)


class Command(BaseCommand):
    help = (
        "Crea un baseline canonico minimo de control no productivo para una empresa: "
        "configuracion fiscal, cuentas, reglas, matrices y capacidades SII condicionadas."
    )

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=int, required=True, help="Empresa objetivo.")
        parser.add_argument(
            "--exercise-start",
            default="2026-01-01",
            help="Inicio de ejercicio en formato YYYY-MM-DD. Default: 2026-01-01",
        )
        parser.add_argument(
            "--plan-version",
            default=DEFAULT_PLAN_VERSION,
            help=f"Version del plan de cuentas. Default: {DEFAULT_PLAN_VERSION}",
        )

    def handle(self, *args, **options):
        company_id = options["company_id"]
        try:
            exercise_start = date.fromisoformat(options["exercise_start"])
        except ValueError as error:
            raise CommandError("exercise-start debe venir en formato YYYY-MM-DD.") from error

        plan_version = options["plan_version"].strip()
        if not plan_version:
            raise CommandError("plan-version no puede venir vacio.")

        try:
            empresa = Empresa.objects.get(pk=company_id)
        except Empresa.DoesNotExist as error:
            raise CommandError(f"La empresa {company_id} no existe.") from error

        regimen = RegimenTributarioEmpresa.objects.filter(codigo_regimen=DEFAULT_REGIME_CODE).first()
        if regimen is None:
            raise CommandError(
                f"No existe el regimen tributario canonico {DEFAULT_REGIME_CODE}. Ejecuta migraciones completas primero."
            )

        config, config_created = ConfiguracionFiscalEmpresa.objects.update_or_create(
            empresa=empresa,
            defaults={
                "regimen_tributario": regimen,
                "afecta_iva_arriendo": False,
                "tasa_iva": Decimal("0.00"),
                "tasa_ppm_vigente": None,
                "aplica_ppm": True,
                "ddjj_habilitadas": [],
                "inicio_ejercicio": exercise_start,
                "moneda_funcional": "CLP",
                "estado": EstadoRegistro.ACTIVE,
            },
        )

        created_accounts = 0
        accounts_by_code = {}
        for codigo, nombre, naturaleza, nivel, control in DEFAULT_ACCOUNTS:
            account, created = CuentaContable.objects.update_or_create(
                empresa=empresa,
                plan_cuentas_version=plan_version,
                codigo=codigo,
                defaults={
                    "nombre": nombre,
                    "naturaleza": naturaleza,
                    "nivel": nivel,
                    "padre": None,
                    "estado": EstadoRegistro.ACTIVE,
                    "es_control_obligatoria": control,
                },
            )
            if created:
                created_accounts += 1
            accounts_by_code[codigo] = account

        created_rules = 0
        created_matrices = 0
        for event_type, debe_code, haber_code in DEFAULT_RULES:
            rule, rule_created = ReglaContable.objects.update_or_create(
                empresa=empresa,
                evento_tipo=event_type,
                plan_cuentas_version=plan_version,
                vigencia_desde=exercise_start,
                defaults={
                    "criterio_cargo": f"default:{debe_code}",
                    "criterio_abono": f"default:{haber_code}",
                    "vigencia_hasta": None,
                    "estado": EstadoRegistro.ACTIVE,
                },
            )
            if rule_created:
                created_rules += 1

            _, matrix_created = MatrizReglasContables.objects.update_or_create(
                regla_contable=rule,
                cuenta_debe=accounts_by_code[debe_code],
                cuenta_haber=accounts_by_code[haber_code],
                defaults={
                    "condicion_impuesto": "",
                    "estado": EstadoRegistro.ACTIVE,
                },
            )
            if matrix_created:
                created_matrices += 1

        created_capabilities = 0
        for capability_key in DEFAULT_SII_CAPABILITIES:
            _, created = CapacidadTributariaSII.objects.update_or_create(
                empresa=empresa,
                capacidad_key=capability_key,
                defaults={
                    "certificado_ref": "",
                    "ambiente": AmbienteSII.CERTIFICATION,
                    "estado_gate": EstadoGateSII.CONDITIONED,
                    "ultimo_resultado": {"bootstrap": "canonical_nonprod_minimum"},
                },
            )
            if created:
                created_capabilities += 1

        self.stdout.write(self.style.SUCCESS("Baseline de control no productivo aplicado correctamente."))
        self.stdout.write(
            f"- empresa: {empresa.id} | config creada={config_created} | plan={plan_version} | inicio_ejercicio={config.inicio_ejercicio}"
        )
        self.stdout.write(
            f"- cuentas creadas={created_accounts} | reglas creadas={created_rules} | matrices creadas={created_matrices} | capacidades creadas={created_capabilities}"
        )

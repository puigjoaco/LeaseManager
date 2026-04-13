from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from contabilidad.models import ConfiguracionFiscalEmpresa, EstadoCierreMensual, ObligacionTributariaMensual
from contabilidad.services import approve_monthly_close, prepare_monthly_close
from patrimonio.models import Empresa
from sii.models import CapacidadSII
from sii.services import generate_annual_preparation


DEFAULT_PPM_RATE = "10.00"
DEFAULT_DDJJ_CODES = ("1887",)


class Command(BaseCommand):
    help = (
        "Construye un baseline anual demo reproducible: completa cierres aprobados del año comercial, "
        "asegura DDJJ habilitadas y genera ProcesoRentaAnual + DDJJ + F22."
    )

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=int, required=True, help="Empresa objetivo.")
        parser.add_argument("--anio-tributario", type=int, required=True, help="Año tributario a preparar.")
        parser.add_argument(
            "--ppm-rate",
            default=DEFAULT_PPM_RATE,
            help=f"Tasa PPM demo para las obligaciones mensuales. Default: {DEFAULT_PPM_RATE}",
        )
        parser.add_argument(
            "--ddjj",
            action="append",
            dest="ddjj_codes",
            help="Código DDJJ habilitada. Se puede repetir. Default: 1887",
        )
        parser.add_argument(
            "--cert-prefix",
            default="demo-cert",
            help="Prefijo para certificado_ref demo. Default: demo-cert",
        )

    def handle(self, *args, **options):
        empresa = self._get_company(options["company_id"])
        anio_tributario = options["anio_tributario"]
        fiscal_year = anio_tributario - 1
        ppm_rate = self._parse_decimal(options["ppm_rate"], field_name="ppm-rate")
        ddjj_codes = tuple(code.strip() for code in (options.get("ddjj_codes") or list(DEFAULT_DDJJ_CODES)) if code.strip())
        cert_prefix = options["cert_prefix"].strip() or "demo-cert"

        config = self._get_config(empresa)
        self._ensure_config_baseline(config=config, ppm_rate=ppm_rate, ddjj_codes=ddjj_codes)
        updated_capabilities = self._ensure_annual_cert_refs(empresa=empresa, cert_prefix=cert_prefix)

        prepared_months = 0
        approved_months = 0
        for month in range(1, 13):
            close = empresa.cierres_mensuales_contables.filter(anio=fiscal_year, mes=month).first()
            if close is None or close.estado in {EstadoCierreMensual.DRAFT, EstadoCierreMensual.REOPENED}:
                close = prepare_monthly_close(empresa, fiscal_year, month)
                prepared_months += 1
            if close.estado == EstadoCierreMensual.PREPARED:
                close = approve_monthly_close(close)
                approved_months += 1
            self._ensure_prepared_ppm_obligation(empresa=empresa, anio=fiscal_year, mes=month, ppm_rate=ppm_rate)

        process, ddjj, f22 = generate_annual_preparation(empresa, anio_tributario)

        self.stdout.write(self.style.SUCCESS("Bootstrap demo tributario anual aplicado correctamente."))
        self.stdout.write(
            f"- empresa={empresa.id} | anio_tributario={anio_tributario} | fiscal_year={fiscal_year}"
        )
        self.stdout.write(
            f"- cierres_preparados_en_esta_corrida={prepared_months} | cierres_aprobados_en_esta_corrida={approved_months}"
        )
        self.stdout.write(f"- capacidades_sii_actualizadas={updated_capabilities} | ddjj_habilitadas={list(ddjj_codes)}")
        self.stdout.write(
            f"- proceso={process.id} estado={process.estado} | ddjj={ddjj.id} estado={ddjj.estado_preparacion} | f22={f22.id} estado={f22.estado_preparacion}"
        )

    def _get_company(self, company_id: int) -> Empresa:
        try:
            return Empresa.objects.get(pk=company_id)
        except Empresa.DoesNotExist as error:
            raise CommandError(f"La empresa {company_id} no existe.") from error

    def _get_config(self, empresa: Empresa) -> ConfiguracionFiscalEmpresa:
        try:
            return ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        except ConfiguracionFiscalEmpresa.DoesNotExist as error:
            raise CommandError(
                f"La empresa {empresa.id} no tiene ConfiguracionFiscalEmpresa. Ejecuta bootstrap_demo_control_baseline primero."
            ) from error

    def _parse_decimal(self, raw_value: str, *, field_name: str) -> Decimal:
        try:
            return Decimal(raw_value)
        except InvalidOperation as error:
            raise CommandError(f"Valor invalido para {field_name}: {raw_value}") from error

    def _ensure_config_baseline(self, *, config: ConfiguracionFiscalEmpresa, ppm_rate: Decimal, ddjj_codes: tuple[str, ...]) -> None:
        dirty = False
        if config.tasa_ppm_vigente != ppm_rate:
            config.tasa_ppm_vigente = ppm_rate
            dirty = True
        if tuple(config.ddjj_habilitadas) != ddjj_codes:
            config.ddjj_habilitadas = list(ddjj_codes)
            dirty = True
        if dirty:
            config.save(update_fields=["tasa_ppm_vigente", "ddjj_habilitadas", "updated_at"])

    def _ensure_annual_cert_refs(self, *, empresa: Empresa, cert_prefix: str) -> int:
        updated = 0
        for capability in empresa.capacidades_sii.filter(
            capacidad_key__in=[CapacidadSII.DDJJ_PREPARACION, CapacidadSII.F22_PREPARACION]
        ):
            if capability.certificado_ref:
                continue
            capability.certificado_ref = f"{cert_prefix}-{capability.capacidad_key.lower()}-{empresa.pk}"
            capability.save(update_fields=["certificado_ref", "updated_at"])
            updated += 1
        return updated

    def _ensure_prepared_ppm_obligation(self, *, empresa: Empresa, anio: int, mes: int, ppm_rate: Decimal) -> None:
        obligation, _ = ObligacionTributariaMensual.objects.get_or_create(
            empresa=empresa,
            anio=anio,
            mes=mes,
            obligacion_tipo="PPM",
            defaults={
                "base_imponible": Decimal("0.00"),
                "monto_calculado": Decimal("0.00"),
                "estado_preparacion": "preparado",
                "detalle_calculo": {"tasa_ppm_vigente": str(ppm_rate), "seed_source": "bootstrap_demo_tax_annual_flow"},
            },
        )
        if obligation.estado_preparacion != "preparado":
            obligation.estado_preparacion = "preparado"
            obligation.save(update_fields=["estado_preparacion", "updated_at"])

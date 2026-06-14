from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib

from django.core.management.base import BaseCommand, CommandError

from contabilidad.models import (
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    EstadoCierreMensual,
    EstadoLiquidacionMensual,
    LiquidacionMensual,
    ObligacionTributariaMensual,
    TipoOwnerLiquidacion,
)
from contabilidad.services import approve_monthly_close, prepare_monthly_close
from patrimonio.models import Empresa
from sii.models import (
    CapacidadSII,
    DestinoMapeoTributarioAnual,
    EstadoReglaTributariaAnual,
    TaxCodeMapping,
    TaxYearRuleSet,
)
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
        self._ensure_tax_year_ruleset(config=config, anio_tributario=anio_tributario, ddjj_codes=ddjj_codes)
        updated_capabilities = self._ensure_annual_cert_refs(empresa=empresa, cert_prefix=cert_prefix)

        prepared_months = 0
        approved_months = 0
        for month in range(1, 13):
            close = empresa.cierres_mensuales_contables.filter(anio=fiscal_year, mes=month).first()
            if close is None or close.estado in {EstadoCierreMensual.DRAFT, EstadoCierreMensual.REOPENED}:
                close = prepare_monthly_close(empresa, fiscal_year, month)
                prepared_months += 1
            if close.estado == EstadoCierreMensual.PREPARED:
                self._ensure_company_liquidation(close)
                close = approve_monthly_close(close)
                approved_months += 1
            self._ensure_prepared_ppm_obligation(empresa=empresa, anio=fiscal_year, mes=month, ppm_rate=ppm_rate)

        process, ddjj, f22 = generate_annual_preparation(empresa, anio_tributario)

        self._write_summary(
            anio_tributario=anio_tributario,
            fiscal_year=fiscal_year,
            prepared_months=prepared_months,
            approved_months=approved_months,
            updated_capabilities=updated_capabilities,
            ddjj_codes=ddjj_codes,
            process=process,
            ddjj=ddjj,
            f22=f22,
        )

    def _get_company(self, company_id: int) -> Empresa:
        try:
            return Empresa.objects.get(pk=company_id)
        except Empresa.DoesNotExist as error:
            raise CommandError("La empresa indicada no existe.") from error

    def _get_config(self, empresa: Empresa) -> ConfiguracionFiscalEmpresa:
        try:
            return ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        except ConfiguracionFiscalEmpresa.DoesNotExist as error:
            raise CommandError(
                "La empresa indicada no tiene ConfiguracionFiscalEmpresa. Ejecuta bootstrap_demo_control_baseline primero."
            ) from error

    def _parse_decimal(self, raw_value: str, *, field_name: str) -> Decimal:
        try:
            return Decimal(raw_value)
        except InvalidOperation as error:
            raise CommandError(f"Valor invalido para {field_name}. Usa un valor decimal.") from error

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

    def _ensure_tax_year_ruleset(
        self,
        *,
        config: ConfiguracionFiscalEmpresa,
        anio_tributario: int,
        ddjj_codes: tuple[str, ...],
    ) -> TaxYearRuleSet:
        hash_normativo = hashlib.sha256(
            f"demo-tax-year-ruleset-{anio_tributario}-{config.regimen_tributario_id}".encode("utf-8")
        ).hexdigest()
        rule_set = TaxYearRuleSet.objects.filter(
            anio_tributario=anio_tributario,
            regimen_tributario=config.regimen_tributario,
            estado=EstadoReglaTributariaAnual.APPROVED,
        ).first()
        created = False
        if rule_set is None:
            rule_set, created = TaxYearRuleSet.objects.get_or_create(
                anio_tributario=anio_tributario,
                regimen_tributario=config.regimen_tributario,
                version=f"AT{anio_tributario}-demo-v1",
                defaults={
                    "estado": EstadoReglaTributariaAnual.APPROVED,
                    "fuente_ref": f"demo-tax-rule-source-at{anio_tributario}",
                    "hash_normativo": hash_normativo,
                    "responsable_aprobacion_ref": f"demo-tax-rule-reviewer-at{anio_tributario}",
                    "metadata": {"source": "bootstrap_demo_tax_annual_flow", "official": False},
                },
            )
        if not created and rule_set.estado != EstadoReglaTributariaAnual.APPROVED:
            rule_set.estado = EstadoReglaTributariaAnual.APPROVED
            rule_set.fuente_ref = f"demo-tax-rule-source-at{anio_tributario}"
            rule_set.hash_normativo = hash_normativo
            rule_set.responsable_aprobacion_ref = f"demo-tax-rule-reviewer-at{anio_tributario}"
            rule_set.metadata = {"source": "bootstrap_demo_tax_annual_flow", "official": False}
            rule_set.full_clean()
            rule_set.save(
                update_fields=[
                    "estado",
                    "fuente_ref",
                    "hash_normativo",
                    "responsable_aprobacion_ref",
                    "metadata",
                    "updated_at",
                ]
            )

        required_destinations = (
            DestinoMapeoTributarioAnual.RLI,
            DestinoMapeoTributarioAnual.CPT,
            DestinoMapeoTributarioAnual.RAI,
            DestinoMapeoTributarioAnual.SAC,
            DestinoMapeoTributarioAnual.F22,
            DestinoMapeoTributarioAnual.DDJJ,
        )
        for destino in required_destinations:
            TaxCodeMapping.objects.get_or_create(
                rule_set=rule_set,
                destino=destino,
                codigo_interno=f"demo.{destino.lower()}.controlled",
                codigo_destino=f"{destino}-DEMO",
                defaults={
                    "formula_ref": f"demo-formula-{destino.lower()}-at{anio_tributario}",
                    "evidencia_ref": f"demo-evidence-{destino.lower()}-at{anio_tributario}",
                    "metadata": {
                        "source": "bootstrap_demo_tax_annual_flow",
                        "ddjj_codes": list(ddjj_codes) if destino == DestinoMapeoTributarioAnual.DDJJ else [],
                    },
                },
            )
        return rule_set

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

    def _ensure_company_liquidation(self, close: CierreMensualContable) -> LiquidacionMensual:
        liquidation, _ = LiquidacionMensual.objects.get_or_create(
            owner_tipo=TipoOwnerLiquidacion.COMPANY,
            empresa=close.empresa,
            cierre_contable=close,
            anio=close.anio,
            mes=close.mes,
            defaults={
                "estado": EstadoLiquidacionMensual.PREPARED,
                "comision_administracion_aplica": False,
                "saldo_final_clp": Decimal("0.00"),
                "evidencia_base_ref": f"demo-tax-annual-liquidation-base-{close.pk}",
                "responsable_ref": f"demo-tax-annual-liquidation-owner-{close.pk}",
            },
        )
        dirty_fields = []
        if liquidation.estado == EstadoLiquidacionMensual.DRAFT:
            liquidation.estado = EstadoLiquidacionMensual.PREPARED
            dirty_fields.append("estado")
        if not liquidation.evidencia_base_ref:
            liquidation.evidencia_base_ref = f"demo-tax-annual-liquidation-base-{close.pk}"
            dirty_fields.append("evidencia_base_ref")
        if not liquidation.responsable_ref:
            liquidation.responsable_ref = f"demo-tax-annual-liquidation-owner-{close.pk}"
            dirty_fields.append("responsable_ref")
        liquidation.full_clean()
        if dirty_fields:
            liquidation.save(update_fields=[*dirty_fields, "updated_at"])
        return liquidation

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

    def _write_summary(
        self,
        *,
        anio_tributario: int,
        fiscal_year: int,
        prepared_months: int,
        approved_months: int,
        updated_capabilities: int,
        ddjj_codes: tuple[str, ...],
        process,
        ddjj,
        f22,
    ) -> None:
        self.stdout.write(self.style.SUCCESS("Bootstrap demo tributario anual aplicado correctamente."))
        self.stdout.write(
            f"- empresa_validada=true | anio_tributario={anio_tributario} | fiscal_year={fiscal_year}"
        )
        self.stdout.write(
            f"- cierres_preparados_en_esta_corrida={prepared_months} | cierres_aprobados_en_esta_corrida={approved_months}"
        )
        self.stdout.write(
            f"- capacidades_sii_actualizadas={updated_capabilities} | ddjj_habilitadas_total={len(ddjj_codes)}"
        )
        self.stdout.write(
            f"- proceso_generado=true | proceso_estado={process.estado} | ddjj_generada=true | ddjj_estado={ddjj.estado_preparacion} | f22_generado=true | f22_estado={f22.estado_preparacion}"
        )

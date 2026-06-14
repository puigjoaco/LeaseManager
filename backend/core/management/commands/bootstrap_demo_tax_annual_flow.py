from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from contabilidad.models import (
    BalanceComprobacion,
    CierreMensualContable,
    ConfiguracionFiscalEmpresa,
    CuentaContable,
    EstadoCierreMensual,
    EstadoLiquidacionMensual,
    LiquidacionMensual,
    NaturalezaCuenta,
    ObligacionTributariaMensual,
    TipoOwnerLiquidacion,
)
from contabilidad.services import approve_monthly_close, prepare_monthly_close
from patrimonio.models import Empresa
from sii.models import (
    AnnualTaxDDJJFormLayout,
    AnnualTaxF22ExportLayout,
    CapacidadSII,
    DestinoMapeoTributarioAnual,
    AnnualTaxOfficialSource,
    EstadoAnnualTaxDDJJLayout,
    EstadoAnnualTaxF22ExportLayout,
    EstadoAnnualTaxOfficialSource,
    EstadoReglaTributariaAnual,
    MedioAnnualTaxDDJJ,
    MedioAnnualTaxF22Export,
    TaxCodeMapping,
    TaxYearRuleSet,
    TipoAnnualTaxOfficialSource,
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
        self._ensure_ddjj_layouts(config=config, anio_tributario=anio_tributario, ddjj_codes=ddjj_codes)
        self._ensure_f22_export_layout(config=config, anio_tributario=anio_tributario)
        self._ensure_real_estate_contribution_source(config=config, anio_tributario=anio_tributario)
        self._ensure_f22_export_format_source(config=config, anio_tributario=anio_tributario)
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

        self._ensure_annual_trial_balance_source(empresa=empresa, fiscal_year=fiscal_year)
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
        rule_source = self._ensure_official_source(
            config=config,
            anio_tributario=anio_tributario,
            key="ruleset",
        )
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
                    "official_source": rule_source,
                    "metadata": {"source": "bootstrap_demo_tax_annual_flow", "official": False},
                },
            )
        if not created and rule_set.estado != EstadoReglaTributariaAnual.APPROVED:
            rule_set.estado = EstadoReglaTributariaAnual.APPROVED
            rule_set.fuente_ref = f"demo-tax-rule-source-at{anio_tributario}"
            rule_set.hash_normativo = hash_normativo
            rule_set.responsable_aprobacion_ref = f"demo-tax-rule-reviewer-at{anio_tributario}"
            rule_set.official_source = rule_source
            rule_set.metadata = {"source": "bootstrap_demo_tax_annual_flow", "official": False}
            rule_set.full_clean()
            rule_set.save(
                update_fields=[
                    "estado",
                    "fuente_ref",
                    "hash_normativo",
                    "responsable_aprobacion_ref",
                    "official_source",
                    "metadata",
                    "updated_at",
                ]
            )
        elif not rule_set.official_source_id:
            rule_set.official_source = rule_source
            rule_set.full_clean()
            rule_set.save(update_fields=["official_source", "updated_at"])

        required_destinations = (
            DestinoMapeoTributarioAnual.RLI,
            DestinoMapeoTributarioAnual.CPT,
            DestinoMapeoTributarioAnual.RAI,
            DestinoMapeoTributarioAnual.SAC,
            DestinoMapeoTributarioAnual.F22,
            DestinoMapeoTributarioAnual.DDJJ,
        )
        for destino in required_destinations:
            source_metadata = {
                DestinoMapeoTributarioAnual.RLI: {
                    "source_metric": "annual_trial_balance.resultado_ganancia_clp",
                    "trial_balance_classifier": "RLI-LEASE-REVENUE",
                },
                DestinoMapeoTributarioAnual.CPT: {
                    "source_metric": "annual_trial_balance.inventario_activo_clp",
                    "trial_balance_classifier": "CPT-CASH-ASSET",
                },
            }.get(destino, {})
            mapping_source = self._ensure_official_source(
                config=config,
                anio_tributario=anio_tributario,
                key=f"mapping-{destino.lower()}",
                applies_to=destino,
            )
            mapping, _ = TaxCodeMapping.objects.get_or_create(
                rule_set=rule_set,
                destino=destino,
                codigo_interno=f"demo.{destino.lower()}.controlled",
                codigo_destino=f"{destino}-DEMO",
                defaults={
                    "formula_ref": f"demo-formula-{destino.lower()}-at{anio_tributario}",
                    "evidencia_ref": f"demo-evidence-{destino.lower()}-at{anio_tributario}",
                    "official_source": mapping_source,
                    "metadata": {
                        "source": "bootstrap_demo_tax_annual_flow",
                        **source_metadata,
                        "ddjj_codes": list(ddjj_codes) if destino == DestinoMapeoTributarioAnual.DDJJ else [],
                    },
                },
            )
            expected_metadata = {
                "source": "bootstrap_demo_tax_annual_flow",
                **source_metadata,
                "ddjj_codes": list(ddjj_codes) if destino == DestinoMapeoTributarioAnual.DDJJ else [],
            }
            dirty_fields = []
            if mapping.metadata != expected_metadata:
                mapping.metadata = expected_metadata
                dirty_fields.append("metadata")
            if not mapping.official_source_id:
                mapping.official_source = mapping_source
                dirty_fields.append("official_source")
            if dirty_fields:
                mapping.full_clean()
                mapping.save(update_fields=[*dirty_fields, "updated_at"])
        rule_set.full_clean()
        return rule_set

    def _ensure_official_source(
        self,
        *,
        config: ConfiguracionFiscalEmpresa,
        anio_tributario: int,
        key: str,
        applies_to: str = "",
        metadata_extra: dict | None = None,
    ) -> AnnualTaxOfficialSource:
        source_key = f"demo-{key}-at{anio_tributario}"
        source_hash = hashlib.sha256(
            f"bootstrap-demo-official-source-{source_key}-{config.regimen_tributario_id}".encode("utf-8")
        ).hexdigest()
        metadata = {"source": "bootstrap_demo_tax_annual_flow", "official": False}
        metadata.update(metadata_extra or {})
        defaults = {
            "source_type": TipoAnnualTaxOfficialSource.EXPERT_REVIEW,
            "title": f"Revision experta demo {key} AT{anio_tributario}",
            "source_ref": f"demo-official-source-{key}-at{anio_tributario}",
            "source_hash": source_hash,
            "retrieved_on": timezone.localdate(),
            "responsible_ref": f"demo-tax-source-reviewer-at{anio_tributario}",
            "estado": EstadoAnnualTaxOfficialSource.APPROVED,
            "applies_to": applies_to,
            "regime_code": config.regimen_tributario.codigo_regimen,
            "scope_note": "Fuente experta demo controlada para preparacion anual local.",
            "metadata": metadata,
        }
        source, created = AnnualTaxOfficialSource.objects.get_or_create(
            anio_tributario=anio_tributario,
            source_key=source_key,
            defaults=defaults,
        )
        if not created:
            dirty_fields = []
            for field_name, value in defaults.items():
                if getattr(source, field_name) != value:
                    setattr(source, field_name, value)
                    dirty_fields.append(field_name)
            if dirty_fields:
                source.full_clean()
                source.save(update_fields=[*dirty_fields, "updated_at"])
        return source

    def _ensure_real_estate_contribution_source(
        self,
        *,
        config: ConfiguracionFiscalEmpresa,
        anio_tributario: int,
    ) -> AnnualTaxOfficialSource:
        values_by_property_id = {
            str(propiedad.id): {
                "contribuciones_clp": "0.00",
                "codigo_f22": "F22-BIENES-RAICES-DEMO",
                "evidencia_ref": f"demo-real-estate-contributions-{propiedad.codigo_propiedad}",
            }
            for propiedad in Empresa.objects.get(pk=config.empresa_id).propiedades.order_by("codigo_propiedad", "id")
            if propiedad.estado == "activa"
        }
        return self._ensure_official_source(
            config=config,
            anio_tributario=anio_tributario,
            key="real-estate-contributions",
            applies_to=DestinoMapeoTributarioAnual.F22,
            metadata_extra={
                "real_estate_contributions": True,
                "values_by_property_id": values_by_property_id,
            },
        )

    def _ensure_f22_export_format_source(
        self,
        *,
        config: ConfiguracionFiscalEmpresa,
        anio_tributario: int,
    ) -> AnnualTaxOfficialSource:
        return self._ensure_official_source(
            config=config,
            anio_tributario=anio_tributario,
            key="f22-export-format",
            applies_to=DestinoMapeoTributarioAnual.F22,
            metadata_extra={
                "f22_export_format": True,
                "f22_certification": False,
                "official_format": False,
                "sii_submission": False,
            },
        )

    def _ensure_ddjj_layouts(
        self,
        *,
        config: ConfiguracionFiscalEmpresa,
        anio_tributario: int,
        ddjj_codes: tuple[str, ...],
    ) -> list[AnnualTaxDDJJFormLayout]:
        layouts = []
        for form_code in ddjj_codes:
            media_source = self._ensure_official_source(
                config=config,
                anio_tributario=anio_tributario,
                key=f"ddjj-media-{form_code}",
                applies_to=DestinoMapeoTributarioAnual.DDJJ,
            )
            form_source = self._ensure_official_source(
                config=config,
                anio_tributario=anio_tributario,
                key=f"ddjj-form-{form_code}",
                applies_to=DestinoMapeoTributarioAnual.DDJJ,
            )
            layout, _ = AnnualTaxDDJJFormLayout.objects.get_or_create(
                anio_tributario=anio_tributario,
                form_code=form_code,
                defaults={
                    "title": f"DDJJ {form_code} demo controlada",
                    "periodicidad": "Anual",
                    "allows_electronic_form": True,
                    "allows_file_importer": True,
                    "allows_file_upload": False,
                    "allows_commercial_software": True,
                    "allows_assistant": False,
                    "medio_preferente": MedioAnnualTaxDDJJ.FILE_IMPORTER,
                    "due_date_label": f"AT{anio_tributario}-plazo-ddjj-{form_code}",
                    "certificate_code": f"cert-ddjj-{form_code}",
                    "certificate_due_label": f"AT{anio_tributario}-plazo-certificado-{form_code}",
                    "resolution_ref": f"demo-resolution-ddjj-{form_code}-at{anio_tributario}",
                    "declaration_status": "preparacion_local_revisable",
                    "layout_ref": f"demo-layout-ddjj-{form_code}-at{anio_tributario}",
                    "instructions_ref": f"demo-instructions-ddjj-{form_code}-at{anio_tributario}",
                    "responsible_ref": f"demo-ddjj-layout-reviewer-at{anio_tributario}",
                    "official_media_source": media_source,
                    "official_form_source": form_source,
                    "warnings": [],
                    "source_payload": {
                        "source": "bootstrap_demo_tax_annual_flow",
                        "form_code": form_code,
                        "anio_tributario": anio_tributario,
                        "official_format": False,
                        "sii_submission": False,
                        "final_tax_calculation": False,
                    },
                    "estado": EstadoAnnualTaxDDJJLayout.PREPARED,
                },
            )
            layout.title = f"DDJJ {form_code} demo controlada"
            layout.periodicidad = "Anual"
            layout.allows_electronic_form = True
            layout.allows_file_importer = True
            layout.allows_file_upload = False
            layout.allows_commercial_software = True
            layout.allows_assistant = False
            layout.medio_preferente = MedioAnnualTaxDDJJ.FILE_IMPORTER
            layout.due_date_label = f"AT{anio_tributario}-plazo-ddjj-{form_code}"
            layout.certificate_code = f"cert-ddjj-{form_code}"
            layout.certificate_due_label = f"AT{anio_tributario}-plazo-certificado-{form_code}"
            layout.resolution_ref = f"demo-resolution-ddjj-{form_code}-at{anio_tributario}"
            layout.declaration_status = "preparacion_local_revisable"
            layout.layout_ref = f"demo-layout-ddjj-{form_code}-at{anio_tributario}"
            layout.instructions_ref = f"demo-instructions-ddjj-{form_code}-at{anio_tributario}"
            layout.responsible_ref = f"demo-ddjj-layout-reviewer-at{anio_tributario}"
            layout.official_media_source = media_source
            layout.official_form_source = form_source
            layout.official_software_source = None
            layout.warnings = []
            layout.source_payload = {
                "source": "bootstrap_demo_tax_annual_flow",
                "form_code": form_code,
                "anio_tributario": anio_tributario,
                "official_format": False,
                "sii_submission": False,
                "final_tax_calculation": False,
            }
            layout.estado = EstadoAnnualTaxDDJJLayout.PREPARED
            layout.hash_layout = layout.compute_hash_layout()
            layout.full_clean()
            layout.save()
            layouts.append(layout)
        return layouts

    def _ensure_f22_export_layout(
        self,
        *,
        config: ConfiguracionFiscalEmpresa,
        anio_tributario: int,
    ) -> AnnualTaxF22ExportLayout:
        certification_source = self._ensure_official_source(
            config=config,
            anio_tributario=anio_tributario,
            key="f22-export-format",
            applies_to=DestinoMapeoTributarioAnual.F22,
            metadata_extra={"f22_export_format": True, "f22_certification": True},
        )
        instructions_source = self._ensure_official_source(
            config=config,
            anio_tributario=anio_tributario,
            key="f22-instructions",
            applies_to=DestinoMapeoTributarioAnual.F22,
            metadata_extra={"f22_instructions": True},
        )
        layout, _ = AnnualTaxF22ExportLayout.objects.get_or_create(
            anio_tributario=anio_tributario,
            form_code="F22",
            defaults={
                "title": f"F22 AT{anio_tributario} preview local demo controlado",
                "allows_local_preview": True,
                "allows_certified_file": False,
                "allows_supervised_portal": False,
                "medio_preferente": MedioAnnualTaxF22Export.LOCAL_PREVIEW,
                "certification_ref": f"demo-certification-f22-at{anio_tributario}",
                "format_ref": f"demo-f22-layout-at{anio_tributario}",
                "instructions_ref": f"demo-f22-instructions-at{anio_tributario}",
                "responsible_ref": f"demo-f22-layout-reviewer-at{anio_tributario}",
                "official_certification_source": certification_source,
                "official_instructions_source": instructions_source,
                "warnings": [],
                "source_payload": {
                    "source": "bootstrap_demo_tax_annual_flow",
                    "form_code": "F22",
                    "anio_tributario": anio_tributario,
                    "official_format": False,
                    "sii_submission": False,
                    "final_tax_calculation": False,
                },
                "estado": EstadoAnnualTaxF22ExportLayout.PREPARED,
            },
        )
        layout.title = f"F22 AT{anio_tributario} preview local demo controlado"
        layout.allows_local_preview = True
        layout.allows_certified_file = False
        layout.allows_supervised_portal = False
        layout.medio_preferente = MedioAnnualTaxF22Export.LOCAL_PREVIEW
        layout.certification_ref = f"demo-certification-f22-at{anio_tributario}"
        layout.format_ref = f"demo-f22-layout-at{anio_tributario}"
        layout.instructions_ref = f"demo-f22-instructions-at{anio_tributario}"
        layout.responsible_ref = f"demo-f22-layout-reviewer-at{anio_tributario}"
        layout.official_certification_source = certification_source
        layout.official_instructions_source = instructions_source
        layout.warnings = []
        layout.source_payload = {
            "source": "bootstrap_demo_tax_annual_flow",
            "form_code": "F22",
            "anio_tributario": anio_tributario,
            "official_format": False,
            "sii_submission": False,
            "final_tax_calculation": False,
        }
        layout.estado = EstadoAnnualTaxF22ExportLayout.PREPARED
        layout.hash_layout = layout.compute_hash_layout()
        layout.full_clean()
        layout.save()
        return layout

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

    def _ensure_annual_trial_balance_source(self, *, empresa: Empresa, fiscal_year: int) -> BalanceComprobacion:
        revenue_account, _ = CuentaContable.objects.get_or_create(
            empresa=empresa,
            plan_cuentas_version="demo-stage6-controlled",
            codigo="4100",
            defaults={
                "nombre": "Ingresos por arriendo",
                "naturaleza": NaturalezaCuenta.CREDIT,
                "nivel": 1,
                "estado": "activa",
            },
        )
        asset_account, _ = CuentaContable.objects.get_or_create(
            empresa=empresa,
            plan_cuentas_version="demo-stage6-controlled",
            codigo="1100",
            defaults={
                "nombre": "Banco recaudador",
                "naturaleza": NaturalezaCuenta.DEBIT,
                "nivel": 1,
                "estado": "activa",
            },
        )
        balance_summary = {
            "source": "bootstrap_demo_tax_annual_flow",
            "lineas_balance_8_columnas": [
                {
                    "codigo_cuenta": revenue_account.codigo,
                    "clasificador_dj1847": "RLI-LEASE-REVENUE",
                    "sumas_haber_clp": "1200000.00",
                    "saldo_acreedor_clp": "1200000.00",
                    "resultado_ganancia_clp": "1200000.00",
                    "formula_ref": f"demo-dj1847-rli-revenue-at{fiscal_year + 1}",
                    "evidencia_ref": f"demo-balance-revenue-at{fiscal_year + 1}",
                },
                {
                    "codigo_cuenta": asset_account.codigo,
                    "clasificador_dj1847": "CPT-CASH-ASSET",
                    "sumas_debe_clp": "1200000.00",
                    "saldo_deudor_clp": "1200000.00",
                    "inventario_activo_clp": "1200000.00",
                    "formula_ref": f"demo-dj1847-cpt-cash-at{fiscal_year + 1}",
                    "evidencia_ref": f"demo-balance-cash-at{fiscal_year + 1}",
                },
            ],
        }
        balance, _ = BalanceComprobacion.objects.update_or_create(
            empresa=empresa,
            periodo=f"{fiscal_year}-12",
            defaults={
                "estado_snapshot": EstadoCierreMensual.APPROVED,
                "storage_ref": f"demo-balance-comprobacion-{empresa.pk}-{fiscal_year}",
                "resumen": balance_summary,
            },
        )
        balance.full_clean()
        return balance

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

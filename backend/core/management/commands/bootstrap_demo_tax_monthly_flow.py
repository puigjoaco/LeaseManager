from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cobranza.models import PagoMensual
from conciliacion.models import ConexionBancaria, EstadoConexionBancaria, MovimientoBancarioImportado, TipoMovimientoBancario
from conciliacion.services import reconcile_exact_movement
from contabilidad.models import ConfiguracionFiscalEmpresa
from contabilidad.services import approve_monthly_close, prepare_monthly_close
from patrimonio.models import Empresa
from sii.models import CapacidadSII, DTEEmitido
from sii.services import generate_dte_draft, generate_f29_draft


DEFAULT_PPM_RATE = "10.00"


class Command(BaseCommand):
    help = (
        "Construye un flujo demo mensual tributario reproducible: concilia un pago facturable, "
        "genera DTE borrador y recalcula F29 del mismo periodo."
    )

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=int, required=True, help="Empresa objetivo.")
        parser.add_argument("--anio", type=int, required=True, help="Año del periodo.")
        parser.add_argument("--mes", type=int, required=True, help="Mes del periodo.")
        parser.add_argument("--payment-id", type=int, help="Pago mensual específico a usar.")
        parser.add_argument(
            "--ppm-rate",
            default=DEFAULT_PPM_RATE,
            help=f"Tasa PPM demo a fijar si falta. Default: {DEFAULT_PPM_RATE}",
        )
        parser.add_argument(
            "--provider-key",
            default="banco_de_chile",
            help="Provider key para la conexión bancaria demo. Default: banco_de_chile",
        )
        parser.add_argument(
            "--cert-prefix",
            default="demo-cert",
            help="Prefijo para certificado_ref demo. Default: demo-cert",
        )

    def handle(self, *args, **options):
        empresa = self._get_company(options["company_id"])
        anio = options["anio"]
        mes = options["mes"]
        payment = self._resolve_payment(
            empresa=empresa,
            anio=anio,
            mes=mes,
            payment_id=options.get("payment_id"),
        )
        ppm_rate = self._parse_decimal(options["ppm_rate"], field_name="ppm-rate")
        provider_key = options["provider_key"].strip() or "banco_de_chile"
        cert_prefix = options["cert_prefix"].strip() or "demo-cert"

        self._ensure_ppm_rate(empresa, ppm_rate)
        updated_capabilities = self._ensure_cert_refs(empresa=empresa, cert_prefix=cert_prefix)

        payment_was_paid = payment.estado_pago in {"pagado", "pagado_via_repactacion", "pagado_por_acuerdo_termino"}
        movement = None
        match_result = None
        if not payment_was_paid:
            connection = self._ensure_connection(payment=payment, provider_key=provider_key)
            movement, match_result = self._reconcile_payment(payment=payment, connection=connection)
            payment.refresh_from_db()

        close = prepare_monthly_close(empresa, anio, mes)
        if close.estado == "preparado":
            close = approve_monthly_close(close)

        f29, f29_created = generate_f29_draft(empresa, anio, mes)
        dte, dte_created = generate_dte_draft(payment)

        self.stdout.write(self.style.SUCCESS("Bootstrap demo tributario mensual aplicado correctamente."))
        self.stdout.write(
            f"- empresa={empresa.id} | periodo={anio:04d}-{mes:02d} | payment={payment.id} | payment_estado={payment.estado_pago}"
        )
        self.stdout.write(
            f"- capacidades_sii_actualizadas={updated_capabilities} | dte={dte.id} created={dte_created} | f29={f29.id} created={f29_created}"
        )
        self.stdout.write(f"- cierre={close.id} | estado_cierre={close.estado}")
        if movement is not None:
            self.stdout.write(
                f"- movimiento={movement.id} | estado_conciliacion={movement.estado_conciliacion} | match={match_result}"
            )

    def _get_company(self, company_id: int) -> Empresa:
        try:
            return Empresa.objects.get(pk=company_id)
        except Empresa.DoesNotExist as error:
            raise CommandError(f"La empresa {company_id} no existe.") from error

    def _resolve_payment(self, *, empresa: Empresa, anio: int, mes: int, payment_id: int | None) -> PagoMensual:
        queryset = (
            PagoMensual.objects.filter(
                contrato__mandato_operacion__propietario_empresa_owner=empresa,
                anio=anio,
                mes=mes,
                distribuciones_cobro__requiere_dte=True,
            )
            .select_related("contrato__mandato_operacion__cuenta_recaudadora")
            .distinct()
            .order_by("id")
        )
        if payment_id is not None:
            queryset = queryset.filter(pk=payment_id)
        payment = queryset.first()
        if payment is None:
            raise CommandError(
                f"No existe un pago facturable para empresa {empresa.id} en {anio:04d}-{mes:02d}."
            )
        return payment

    def _parse_decimal(self, raw_value: str, *, field_name: str) -> Decimal:
        try:
            return Decimal(raw_value)
        except InvalidOperation as error:
            raise CommandError(f"Valor invalido para {field_name}: {raw_value}") from error

    def _ensure_ppm_rate(self, empresa: Empresa, ppm_rate: Decimal) -> None:
        try:
            config = ConfiguracionFiscalEmpresa.objects.get(empresa=empresa)
        except ConfiguracionFiscalEmpresa.DoesNotExist as error:
            raise CommandError(
                f"La empresa {empresa.id} no tiene ConfiguracionFiscalEmpresa. Ejecuta bootstrap_demo_control_baseline primero."
            ) from error

        if config.tasa_ppm_vigente == ppm_rate:
            return
        config.tasa_ppm_vigente = ppm_rate
        config.save(update_fields=["tasa_ppm_vigente", "updated_at"])

    def _ensure_cert_refs(self, *, empresa: Empresa, cert_prefix: str) -> int:
        updated = 0
        for capability in empresa.capacidades_sii.filter(
            capacidad_key__in=[
                CapacidadSII.DTE_EMISION,
                CapacidadSII.F29_PREPARACION,
            ]
        ):
            if capability.certificado_ref:
                continue
            capability.certificado_ref = f"{cert_prefix}-{capability.capacidad_key.lower()}-{empresa.pk}"
            capability.save(update_fields=["certificado_ref", "updated_at"])
            updated += 1
        return updated

    def _ensure_connection(self, *, payment: PagoMensual, provider_key: str) -> ConexionBancaria:
        cuenta = payment.contrato.mandato_operacion.cuenta_recaudadora
        connection, _ = ConexionBancaria.objects.get_or_create(
            cuenta_recaudadora=cuenta,
            provider_key=provider_key,
            defaults={
                "credencial_ref": f"demo-{provider_key}-{cuenta.pk}",
                "scope": "movimientos",
                "estado_conexion": EstadoConexionBancaria.ACTIVE,
                "primaria_movimientos": True,
            },
        )
        dirty = False
        if connection.estado_conexion != EstadoConexionBancaria.ACTIVE:
            connection.estado_conexion = EstadoConexionBancaria.ACTIVE
            dirty = True
        if not connection.primaria_movimientos:
            connection.primaria_movimientos = True
            dirty = True
        if not connection.credencial_ref:
            connection.credencial_ref = f"demo-{provider_key}-{cuenta.pk}"
            dirty = True
        if dirty:
            connection.save()
        return connection

    def _reconcile_payment(self, *, payment: PagoMensual, connection: ConexionBancaria):
        with transaction.atomic():
            movement, created = MovimientoBancarioImportado.objects.get_or_create(
                conexion_bancaria=connection,
                fecha_movimiento=payment.fecha_vencimiento,
                tipo_movimiento=TipoMovimientoBancario.CREDIT,
                monto=payment.monto_calculado_clp,
                descripcion_origen=f"Bootstrap demo tributario pago {payment.id}",
                defaults={
                    "transaction_id_banco": f"demo-tax-{payment.id}",
                },
            )
            if not created:
                movement.descripcion_origen = f"Bootstrap demo tributario pago {payment.id}"
                movement.transaction_id_banco = movement.transaction_id_banco or f"demo-tax-{payment.id}"
                movement.save(update_fields=["descripcion_origen", "transaction_id_banco", "updated_at"])
            result = reconcile_exact_movement(movement)
        return movement, result["status"]

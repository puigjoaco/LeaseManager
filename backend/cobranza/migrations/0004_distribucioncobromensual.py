from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal, ROUND_DOWN
import django.core.validators
from datetime import date


def _split_amount_by_percentages(total_amount, percentages):
    if not percentages:
        return []
    allocated = []
    running_total = Decimal('0.00')
    for index, percentage in enumerate(percentages):
        if index == len(percentages) - 1:
            amount = total_amount - running_total
        else:
            amount = (total_amount * percentage / Decimal('100.00')).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
            running_total += amount
        allocated.append(amount)
    return allocated


def _operational_month_start(payment):
    return date(int(payment.anio), int(payment.mes), 1)


def _resolved_facturable_amount(payment):
    stored_amount = Decimal(payment.monto_facturable_clp or Decimal('0.00'))
    if stored_amount > Decimal('0.00'):
        return stored_amount
    return Decimal(payment.monto_calculado_clp)


def backfill_distributions_for_existing_payments(apps, schema_editor):
    PagoMensual = apps.get_model('cobranza', 'PagoMensual')
    DistribucionCobroMensual = apps.get_model('cobranza', 'DistribucionCobroMensual')
    ParticipacionPatrimonial = apps.get_model('patrimonio', 'ParticipacionPatrimonial')

    for payment in PagoMensual.objects.select_related(
        'contrato__mandato_operacion__propietario_empresa_owner',
        'contrato__mandato_operacion__propietario_comunidad_owner',
        'contrato__mandato_operacion__propietario_socio_owner',
        'contrato__mandato_operacion__entidad_facturadora',
    ).all():
        if DistribucionCobroMensual.objects.filter(pago_mensual_id=payment.id).exists():
            continue

        mandate = payment.contrato.mandato_operacion
        distribution_rows = []
        if mandate.propietario_empresa_owner_id:
            distribution_rows.append(
                {
                    'beneficiario_empresa_owner_id': mandate.propietario_empresa_owner_id,
                    'beneficiario_socio_owner_id': None,
                    'porcentaje_snapshot': Decimal('100.00'),
                }
            )
        elif mandate.propietario_socio_owner_id:
            distribution_rows.append(
                {
                    'beneficiario_empresa_owner_id': None,
                    'beneficiario_socio_owner_id': mandate.propietario_socio_owner_id,
                    'porcentaje_snapshot': Decimal('100.00'),
                }
            )
        elif mandate.propietario_comunidad_owner_id:
            effective_date = _operational_month_start(payment)
            participaciones = list(
                ParticipacionPatrimonial.objects.filter(
                    comunidad_owner_id=mandate.propietario_comunidad_owner_id,
                    activo=True,
                    vigente_desde__lte=effective_date,
                ).filter(
                    models.Q(vigente_hasta__isnull=True) | models.Q(vigente_hasta__gte=effective_date)
                ).order_by('id')
            )
            for participacion in participaciones:
                distribution_rows.append(
                    {
                        'beneficiario_empresa_owner_id': participacion.participante_empresa_id,
                        'beneficiario_socio_owner_id': participacion.participante_socio_id,
                        'porcentaje_snapshot': participacion.porcentaje,
                    }
                )

        facturable_amount = _resolved_facturable_amount(payment)
        devengados = _split_amount_by_percentages(facturable_amount, [row['porcentaje_snapshot'] for row in distribution_rows])
        conciliados = _split_amount_by_percentages(Decimal(payment.monto_pagado_clp), [row['porcentaje_snapshot'] for row in distribution_rows])

        for index, row in enumerate(distribution_rows):
            requiere_dte = bool(
                row['beneficiario_empresa_owner_id']
                and mandate.entidad_facturadora_id
                and row['beneficiario_empresa_owner_id'] == mandate.entidad_facturadora_id
            )
            DistribucionCobroMensual.objects.create(
                pago_mensual_id=payment.id,
                beneficiario_socio_owner_id=row['beneficiario_socio_owner_id'],
                beneficiario_empresa_owner_id=row['beneficiario_empresa_owner_id'],
                porcentaje_snapshot=row['porcentaje_snapshot'],
                monto_devengado_clp=devengados[index],
                monto_conciliado_clp=conciliados[index],
                monto_facturable_clp=devengados[index] if requiere_dte else Decimal('0.00'),
                requiere_dte=requiere_dte,
                origen_atribucion='backfill_migracion',
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('patrimonio', '0002_participaciones_mixtas_y_representacion_comunidad'),
        ('cobranza', '0003_pagomensual_monto_facturable_clp'),
    ]

    operations = [
        migrations.CreateModel(
            name='DistribucionCobroMensual',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                (
                    'porcentaje_snapshot',
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal('0.01')),
                            django.core.validators.MaxValueValidator(Decimal('100.00')),
                        ],
                    ),
                ),
                ('monto_devengado_clp', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('monto_conciliado_clp', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('monto_facturable_clp', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14)),
                ('requiere_dte', models.BooleanField(default=False)),
                ('origen_atribucion', models.CharField(default='snapshot_pago', max_length=64)),
                ('beneficiario_empresa_owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='distribuciones_cobro_mensual', to='patrimonio.empresa')),
                ('beneficiario_socio_owner', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='distribuciones_cobro_mensual', to='patrimonio.socio')),
                ('pago_mensual', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='distribuciones_cobro', to='cobranza.pagomensual')),
            ],
            options={
                'ordering': ['pago_mensual_id', 'id'],
            },
        ),
        migrations.AddConstraint(
            model_name='distribucioncobromensual',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(beneficiario_socio_owner__isnull=False, beneficiario_empresa_owner__isnull=True)
                    | models.Q(beneficiario_socio_owner__isnull=True, beneficiario_empresa_owner__isnull=False)
                ),
                name='distribucion_cobro_exactly_one_beneficiary',
            ),
        ),
        migrations.RunPython(backfill_distributions_for_existing_payments, noop_reverse),
    ]

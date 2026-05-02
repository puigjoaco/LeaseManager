from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


def _resolved_distribution_amount(dte):
    payment = dte.pago_mensual
    stored_amount = Decimal(payment.monto_facturable_clp or Decimal('0.00'))
    if stored_amount > Decimal('0.00'):
        return stored_amount
    dte_amount = Decimal(dte.monto_neto_clp or Decimal('0.00'))
    if dte_amount > Decimal('0.00'):
        return dte_amount
    return Decimal(payment.monto_calculado_clp)


def _ensure_distribution_for_dte(dte, DistribucionCobroMensual):
    payment = dte.pago_mensual
    amount = _resolved_distribution_amount(dte)
    defaults = {
        'beneficiario_empresa_owner_id': dte.empresa_id,
        'beneficiario_socio_owner_id': None,
        'porcentaje_snapshot': Decimal('100.00'),
        'monto_devengado_clp': amount,
        'monto_conciliado_clp': Decimal(payment.monto_pagado_clp),
        'monto_facturable_clp': amount,
        'requiere_dte': True,
        'origen_atribucion': 'backfill_dte_orfano',
    }

    distribution = (
        DistribucionCobroMensual.objects.filter(
            pago_mensual_id=dte.pago_mensual_id,
            beneficiario_empresa_owner_id=dte.empresa_id,
            requiere_dte=True,
        )
        .order_by('id')
        .first()
    )
    if distribution:
        return distribution

    fallback_distribution = (
        DistribucionCobroMensual.objects.filter(
            pago_mensual_id=dte.pago_mensual_id,
            beneficiario_empresa_owner_id=dte.empresa_id,
        )
        .order_by('id')
        .first()
    )
    if fallback_distribution:
        for field, value in defaults.items():
            setattr(fallback_distribution, field, value)
        fallback_distribution.save(update_fields=[*defaults.keys(), 'updated_at'])
        return fallback_distribution

    return DistribucionCobroMensual.objects.create(
        pago_mensual_id=dte.pago_mensual_id,
        **defaults,
    )


def backfill_dte_distribution(apps, schema_editor):
    DTEEmitido = apps.get_model('sii', 'DTEEmitido')
    DistribucionCobroMensual = apps.get_model('cobranza', 'DistribucionCobroMensual')

    for dte in DTEEmitido.objects.select_related('pago_mensual').all():
        distribution = _ensure_distribution_for_dte(dte, DistribucionCobroMensual)
        dte.distribucion_cobro_mensual_id = distribution.id
        dte.save(update_fields=['distribucion_cobro_mensual'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('cobranza', '0004_distribucioncobromensual'),
        ('sii', '0003_procesorentaanual_f22preparacionanual_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='dteemitido',
            name='distribucion_cobro_mensual',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='dte_emitido',
                to='cobranza.distribucioncobromensual',
            ),
        ),
        migrations.RunPython(backfill_dte_distribution, noop_reverse),
        migrations.AlterField(
            model_name='dteemitido',
            name='distribucion_cobro_mensual',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='dte_emitido',
                to='cobranza.distribucioncobromensual',
            ),
        ),
    ]

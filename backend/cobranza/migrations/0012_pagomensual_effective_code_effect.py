from decimal import Decimal

from django.db import migrations, models


def backfill_effective_code_effect(apps, schema_editor):
    PagoMensual = apps.get_model('cobranza', 'PagoMensual')
    for payment in PagoMensual.objects.all().iterator():
        calculated = Decimal(payment.monto_calculado_clp or Decimal('0.00'))
        billable = Decimal(payment.monto_facturable_clp or Decimal('0.00'))
        payment.monto_efecto_codigo_efectivo_clp = calculated - billable
        payment.save(update_fields=['monto_efecto_codigo_efectivo_clp'])


class Migration(migrations.Migration):

    dependencies = [
        ('cobranza', '0011_valorufdiario_manual_provenance'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagomensual',
            name='monto_efecto_codigo_efectivo_clp',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=14),
        ),
        migrations.RunPython(backfill_effective_code_effect, migrations.RunPython.noop),
    ]

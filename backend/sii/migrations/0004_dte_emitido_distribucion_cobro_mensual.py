from django.db import migrations, models
import django.db.models.deletion


def backfill_dte_distribution(apps, schema_editor):
    DTEEmitido = apps.get_model('sii', 'DTEEmitido')
    DistribucionCobroMensual = apps.get_model('cobranza', 'DistribucionCobroMensual')

    for dte in DTEEmitido.objects.select_related('pago_mensual').all():
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

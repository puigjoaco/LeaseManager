from django.db import migrations, models


def backfill_recaudador_from_account_owner(apps, schema_editor):
    MandatoOperacion = apps.get_model('operacion', 'MandatoOperacion')

    for mandato in MandatoOperacion.objects.select_related('cuenta_recaudadora').all():
        cuenta = mandato.cuenta_recaudadora
        mandato.recaudador_empresa_owner_id = cuenta.empresa_owner_id
        mandato.recaudador_socio_owner_id = cuenta.socio_owner_id
        mandato.save(update_fields=['recaudador_empresa_owner', 'recaudador_socio_owner'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('operacion', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='mandatooperacion',
            name='recaudador_empresa_owner',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name='mandatos_como_recaudadora',
                to='patrimonio.empresa',
            ),
        ),
        migrations.AddField(
            model_name='mandatooperacion',
            name='recaudador_socio_owner',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.PROTECT,
                related_name='mandatos_como_recaudador',
                to='patrimonio.socio',
            ),
        ),
        migrations.RunPython(backfill_recaudador_from_account_owner, noop_reverse),
        migrations.AddConstraint(
            model_name='mandatooperacion',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(recaudador_empresa_owner__isnull=False, recaudador_socio_owner__isnull=True)
                    | models.Q(recaudador_empresa_owner__isnull=True, recaudador_socio_owner__isnull=False)
                ),
                name='mandato_exactly_one_recaudador',
            ),
        ),
    ]

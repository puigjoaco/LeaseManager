from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations, models


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


def _derived_total_from_dte(dte, distribution_rows):
    if dte is None:
        return None
    dte_amount = Decimal(dte.monto_neto_clp or Decimal('0.00'))
    if dte_amount <= Decimal('0.00'):
        return None

    for row in distribution_rows:
        if row['beneficiario_empresa_owner_id'] != dte.empresa_id:
            continue
        percentage = Decimal(row['porcentaje_snapshot'])
        if percentage <= Decimal('0.00'):
            return None
        return (dte_amount * Decimal('100.00') / percentage).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP,
        )

    return dte_amount


def _resolved_facturable_amount(payment, dte=None, distribution_rows=None):
    stored_amount = Decimal(payment.monto_facturable_clp or Decimal('0.00'))
    if stored_amount > Decimal('0.00'):
        return stored_amount
    dte_derived_amount = _derived_total_from_dte(dte, distribution_rows or [])
    if dte_derived_amount is not None:
        return dte_derived_amount
    return Decimal(payment.monto_calculado_clp)


def _sync_payment_facturable_amount(payment, facturable_amount):
    stored_amount = Decimal(payment.monto_facturable_clp or Decimal('0.00'))
    if stored_amount > Decimal('0.00') or facturable_amount <= Decimal('0.00'):
        return
    payment.monto_facturable_clp = facturable_amount
    payment.save(update_fields=['monto_facturable_clp'])


def _distribution_key_from_ids(*, beneficiario_empresa_owner_id=None, beneficiario_socio_owner_id=None):
    if beneficiario_empresa_owner_id:
        return ('empresa', beneficiario_empresa_owner_id)
    if beneficiario_socio_owner_id:
        return ('socio', beneficiario_socio_owner_id)
    return ('none', None)


def _distribution_key(instance):
    return _distribution_key_from_ids(
        beneficiario_empresa_owner_id=instance.beneficiario_empresa_owner_id,
        beneficiario_socio_owner_id=instance.beneficiario_socio_owner_id,
    )


def _get_attached_dte(distribution):
    try:
        return distribution.dte_emitido
    except ObjectDoesNotExist:
        return None


def _select_distribution_for_dte(dte, distributions):
    if dte is None:
        return None
    return next(
        (item for item in distributions if item.beneficiario_empresa_owner_id == dte.empresa_id),
        None,
    )


def _mandate_owner_type(mandate):
    if getattr(mandate, 'propietario_empresa_owner_id', None):
        return 'empresa'
    if getattr(mandate, 'propietario_comunidad_owner_id', None):
        return 'comunidad'
    if getattr(mandate, 'propietario_socio_owner_id', None):
        return 'socio'
    return 'desconocido'


def _record_distribution_conflict(payment, attached_payment_dte, ManualResolution):
    mandate = payment.contrato.mandato_operacion
    ManualResolution.objects.get_or_create(
        category='migration.cobranza.distribucion_facturable_conflict',
        scope_type='pago_mensual',
        scope_reference=str(payment.id),
        defaults={
            'summary': (
                'El DTE legado no coincide con la atribucion patrimonial historica del pago '
                'y requiere revision manual antes de normalizar la distribucion facturable.'
            ),
            'metadata': {
                'pago_mensual_id': payment.id,
                'contrato_id': payment.contrato_id,
                'dte_id': attached_payment_dte.id,
                'dte_empresa_id': attached_payment_dte.empresa_id,
                'mandato_entidad_facturadora_id': mandate.entidad_facturadora_id,
                'owner_type': _mandate_owner_type(mandate),
            },
        },
    )


def _build_desired_rows(payment, ParticipacionPatrimonial):
    mandate = payment.contrato.mandato_operacion
    try:
        dte = payment.dte_emitido
    except ObjectDoesNotExist:
        dte = None

    effective_date = _operational_month_start(payment)
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

    if not distribution_rows:
        return [], True, Decimal('0.00')

    dte_company_in_snapshot = (
        not dte
        or any(row['beneficiario_empresa_owner_id'] == dte.empresa_id for row in distribution_rows)
    )

    facturable_amount = _resolved_facturable_amount(payment, dte=dte, distribution_rows=distribution_rows)
    devengados = _split_amount_by_percentages(
        facturable_amount,
        [row['porcentaje_snapshot'] for row in distribution_rows],
    )
    conciliados = _split_amount_by_percentages(
        Decimal(payment.monto_pagado_clp),
        [row['porcentaje_snapshot'] for row in distribution_rows],
    )

    requires_dte_company_id = dte.empresa_id if dte else mandate.entidad_facturadora_id
    desired_rows = []
    for index, row in enumerate(distribution_rows):
        beneficiario_empresa_owner_id = row['beneficiario_empresa_owner_id']
        requires_dte = bool(
            beneficiario_empresa_owner_id
            and requires_dte_company_id
            and beneficiario_empresa_owner_id == requires_dte_company_id
        )
        desired_rows.append(
            {
                'beneficiario_empresa_owner_id': beneficiario_empresa_owner_id,
                'beneficiario_socio_owner_id': row['beneficiario_socio_owner_id'],
                'porcentaje_snapshot': row['porcentaje_snapshot'],
                'monto_devengado_clp': devengados[index],
                'monto_conciliado_clp': conciliados[index],
                'monto_facturable_clp': devengados[index] if requires_dte else Decimal('0.00'),
                'requiere_dte': requires_dte,
                'origen_atribucion': 'repair_migracion_historica',
            }
        )

    return desired_rows, dte_company_in_snapshot, facturable_amount


def repair_legacy_distributions(apps, schema_editor):
    PagoMensual = apps.get_model('cobranza', 'PagoMensual')
    DistribucionCobroMensual = apps.get_model('cobranza', 'DistribucionCobroMensual')
    ParticipacionPatrimonial = apps.get_model('patrimonio', 'ParticipacionPatrimonial')
    ManualResolution = apps.get_model('audit', 'ManualResolution')

    payments = PagoMensual.objects.select_related(
        'contrato__mandato_operacion',
        'dte_emitido',
    ).all()

    for payment in payments:
        try:
            attached_payment_dte = payment.dte_emitido
        except ObjectDoesNotExist:
            attached_payment_dte = None
        existing_distributions = list(
            DistribucionCobroMensual.objects.filter(pago_mensual_id=payment.id).order_by('id')
        )
        should_repair = (
            not existing_distributions
            or any(
                item.origen_atribucion in {'backfill_migracion', 'backfill_dte_orfano'}
                for item in existing_distributions
            )
        )
        if not should_repair:
            continue

        desired_rows, can_preserve_dte_link, facturable_amount = _build_desired_rows(payment, ParticipacionPatrimonial)
        if not desired_rows:
            continue
        _sync_payment_facturable_amount(payment, facturable_amount)
        if attached_payment_dte is not None and not can_preserve_dte_link:
            # This legacy DTE contradicts the historical participant snapshot.
            # Keep the existing rows untouched rather than collapsing the whole payment
            # into a fictitious 100% company allocation.
            _record_distribution_conflict(payment, attached_payment_dte, ManualResolution)
            continue

        existing_by_key = defaultdict(list)
        for distribution in existing_distributions:
            existing_by_key[_distribution_key(distribution)].append(distribution)

        matched_distribution_ids = set()
        kept_distributions = []

        for desired in desired_rows:
            key = _distribution_key_from_ids(
                beneficiario_empresa_owner_id=desired['beneficiario_empresa_owner_id'],
                beneficiario_socio_owner_id=desired['beneficiario_socio_owner_id'],
            )
            candidates = [
                distribution
                for distribution in existing_by_key.get(key, [])
                if distribution.id not in matched_distribution_ids
            ]
            distribution = next(
                (item for item in candidates if _get_attached_dte(item) is not None),
                candidates[0] if candidates else None,
            )

            if distribution is None:
                distribution = DistribucionCobroMensual.objects.create(
                    pago_mensual_id=payment.id,
                    **desired,
                )
            else:
                for field, value in desired.items():
                    setattr(distribution, field, value)
                distribution.save(update_fields=[*desired.keys(), 'updated_at'])

            kept_distributions.append(distribution)
            matched_distribution_ids.add(distribution.id)

        payment_dte_target = _select_distribution_for_dte(attached_payment_dte, kept_distributions)
        if (
            attached_payment_dte is not None
            and payment_dte_target is not None
            and attached_payment_dte.distribucion_cobro_mensual_id != payment_dte_target.id
        ):
            attached_payment_dte.distribucion_cobro_mensual_id = payment_dte_target.id
            attached_payment_dte.save(update_fields=['distribucion_cobro_mensual'])

        for distribution in existing_distributions:
            if distribution.id in matched_distribution_ids:
                continue

            attached_dte = _get_attached_dte(distribution)
            attached_dte_target = _select_distribution_for_dte(attached_dte, kept_distributions)
            if attached_dte is not None and attached_dte_target is not None:
                attached_dte.distribucion_cobro_mensual_id = attached_dte_target.id
                attached_dte.save(update_fields=['distribucion_cobro_mensual'])

            if attached_dte is None or attached_dte_target is not None:
                distribution.delete()


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('audit', '0001_initial'),
        ('cobranza', '0004_distribucioncobromensual'),
        ('sii', '0004_dte_emitido_distribucion_cobro_mensual'),
    ]

    operations = [
        migrations.RunPython(repair_legacy_distributions, noop_reverse),
        migrations.AddConstraint(
            model_name='distribucioncobromensual',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(monto_devengado_clp__gte=Decimal('0.00'))
                    & models.Q(monto_conciliado_clp__gte=Decimal('0.00'))
                    & models.Q(monto_facturable_clp__gte=Decimal('0.00'))
                ),
                name='distribucion_cobro_non_negative_amounts',
            ),
        ),
        migrations.AddConstraint(
            model_name='distribucioncobromensual',
            constraint=models.CheckConstraint(
                check=models.Q(monto_facturable_clp__lte=models.F('monto_devengado_clp')),
                name='distribucion_cobro_facturable_lte_devengado',
            ),
        ),
        migrations.AddConstraint(
            model_name='distribucioncobromensual',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(requiere_dte=False, monto_facturable_clp=Decimal('0.00'))
                    | models.Q(requiere_dte=True, monto_facturable_clp__gt=Decimal('0.00'))
                ),
                name='distribucion_cobro_facturable_matches_dte_flag',
            ),
        ),
        migrations.AddConstraint(
            model_name='distribucioncobromensual',
            constraint=models.CheckConstraint(
                check=(
                    models.Q(requiere_dte=False)
                    | models.Q(beneficiario_empresa_owner__isnull=False, beneficiario_socio_owner__isnull=True)
                ),
                name='distribucion_cobro_dte_requires_company_beneficiary',
            ),
        ),
        migrations.AddConstraint(
            model_name='distribucioncobromensual',
            constraint=models.UniqueConstraint(
                fields=('pago_mensual', 'beneficiario_empresa_owner'),
                condition=models.Q(beneficiario_empresa_owner__isnull=False),
                name='uniq_distribucion_pago_empresa_beneficiaria',
            ),
        ),
        migrations.AddConstraint(
            model_name='distribucioncobromensual',
            constraint=models.UniqueConstraint(
                fields=('pago_mensual', 'beneficiario_socio_owner'),
                condition=models.Q(beneficiario_socio_owner__isnull=False),
                name='uniq_distribucion_pago_socio_beneficiario',
            ),
        ),
    ]

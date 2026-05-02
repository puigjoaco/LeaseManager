from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cobranza.models import PagoMensual
from conciliacion.models import ConexionBancaria, MovimientoBancarioImportado
from contratos.models import Arrendatario, Contrato, ContratoPropiedad, PeriodoContractual
from core.models import Role, Scope, UserScopeAssignment
from operacion.models import CuentaRecaudadora, EstadoCuentaRecaudadora, EstadoMandatoOperacion, MandatoOperacion
from patrimonio.models import ComunidadPatrimonial, Empresa, ModoRepresentacionComunidad, Propiedad, Socio, TipoInmueble

from .models import AuditEvent, ManualResolution


class AuditAPITests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='audit', password='secret123')
        self.client.force_authenticate(self.user)

    def test_auth_is_required_for_manual_resolution_endpoints(self):
        client = self.client_class()
        response = client.get(reverse('manual-resolution-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manual_resolution_list_supports_filters(self):
        first = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-1',
            summary='Primera',
            status='open',
        )
        ManualResolution.objects.create(
            category='migration.arrendatario.invalid_rut',
            scope_type='legacy_arrendatario',
            scope_reference='arr-1',
            summary='Segunda',
            status='resolved',
        )

        response = self.client.get(
            f"{reverse('manual-resolution-list')}?status=open&category={first.category}&scope_type=legacy_propiedad"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['scope_reference'], 'prop-1')

    def test_unknown_income_resolution_cannot_be_marked_resolved_via_generic_patch(self):
        resolution = ManualResolution.objects.create(
            category='conciliacion.ingreso_desconocido',
            scope_type='movimiento_bancario',
            scope_reference='123',
            summary='Ingreso desconocido',
            status='open',
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {'status': 'resolved', 'rationale': 'Cerrar directo'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_charge_resolution_cannot_be_marked_resolved_via_generic_patch(self):
        resolution = ManualResolution.objects.create(
            category='conciliacion.movimiento_cargo',
            scope_type='movimiento_bancario',
            scope_reference='124',
            summary='Cargo bancario',
            status='open',
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {'status': 'resolved', 'rationale': 'Cerrar directo'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_migration_owner_resolution_cannot_be_marked_resolved_via_generic_patch(self):
        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='legacy-123',
            summary='Owner manual pendiente',
            status='open',
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {'status': 'resolved', 'rationale': 'Cerrar directo'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_distribution_conflict_resolution_cannot_be_marked_resolved_via_generic_patch(self):
        resolution = ManualResolution.objects.create(
            category='migration.cobranza.distribucion_facturable_conflict',
            scope_type='pago_mensual',
            scope_reference='123',
            summary='Conflicto DTE distribucion',
            status='open',
        )

        response = self.client.patch(
            reverse('manual-resolution-detail', args=[resolution.pk]),
            {'status': 'resolved', 'rationale': 'Cerrar directo'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_resolve_property_owner_manual_resolution_creates_comunidad_and_propiedad(self):
        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        socio_2 = Socio.objects.create(nombre='Socio Dos', rut='22222222-2', activo=True)
        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-1',
            summary='Owner manual',
            metadata={
                'codigo': 46,
                'codigo_propiedad': None,
                'direccion': 'Av. Santa Maria 9500 Dpto 1014',
                'canonical_estado': 'activa',
                'rol_avaluo': '123-1',
                'comuna': 'Santiago',
                'region': '',
                'tipo_inmueble': 'departamento',
                'candidate_owner_model': 'comunidad',
                'socios': [
                    {
                        'socio_legacy_id': 'soc-1',
                        'socio_nombre': socio_1.nombre,
                        'socio_rut': socio_1.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                        'vigente_hasta': None,
                    },
                    {
                        'socio_legacy_id': 'soc-2',
                        'socio_nombre': socio_2.nombre,
                        'socio_rut': socio_2.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                        'vigente_hasta': None,
                    },
                ],
            },
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-property-owner', args=[resolution.pk]),
            {
                'nombre_comunidad': 'Comunidad Av Santa Maria 9500 Dpto 1014',
                'representante_socio_id': socio_1.pk,
                'representante_modo': ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
                'region': 'RM',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resolution.refresh_from_db()
        self.assertEqual(resolution.status, 'resolved')
        self.assertEqual(ComunidadPatrimonial.objects.count(), 1)
        self.assertEqual(Propiedad.objects.count(), 1)
        self.assertEqual(Propiedad.objects.get().comunidad_owner_id, ComunidadPatrimonial.objects.get().pk)
        self.assertEqual(ComunidadPatrimonial.objects.get().representacion_vigente().modo_representacion, ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT)

    def test_resolve_property_owner_manual_resolution_allows_designated_representative(self):
        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        socio_2 = Socio.objects.create(nombre='Socio Dos', rut='22222222-2', activo=True)
        socio_designado = Socio.objects.create(nombre='Joaquin', rut='33333333-3', activo=True)
        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-2',
            summary='Owner manual',
            metadata={
                'codigo': 47,
                'direccion': 'Av. Comunidad Designada 123',
                'canonical_estado': 'activa',
                'rol_avaluo': '123-2',
                'comuna': 'Santiago',
                'tipo_inmueble': 'departamento',
                'candidate_owner_model': 'comunidad',
                'socios': [
                    {
                        'socio_legacy_id': 'soc-1',
                        'socio_nombre': socio_1.nombre,
                        'socio_rut': socio_1.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                    },
                    {
                        'socio_legacy_id': 'soc-2',
                        'socio_nombre': socio_2.nombre,
                        'socio_rut': socio_2.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                    },
                ],
            },
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-property-owner', args=[resolution.pk]),
            {
                'nombre_comunidad': 'Comunidad Designada',
                'representante_socio_id': socio_designado.pk,
                'representante_modo': ModoRepresentacionComunidad.DESIGNATED,
                'region': 'RM',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comunidad = ComunidadPatrimonial.objects.get()
        self.assertEqual(comunidad.representacion_vigente().modo_representacion, ModoRepresentacionComunidad.DESIGNATED)
        self.assertEqual(comunidad.representante_socio_id, socio_designado.pk)

    def test_resolve_property_owner_designated_mode_can_use_default_representative(self):
        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        socio_2 = Socio.objects.create(nombre='Socio Dos', rut='22222222-2', activo=True)
        default_representative = Socio.objects.create(nombre='Joaquin Puig Vittini', rut='17.366.287-4', activo=True)
        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-default-representative',
            summary='Owner manual',
            metadata={
                'codigo': 48,
                'direccion': 'DIRECCION_TEST_NO_PRODUCTIVA',
                'canonical_estado': 'activa',
                'rol_avaluo': '123-3',
                'comuna': 'Santiago',
                'tipo_inmueble': 'departamento',
                'candidate_owner_model': 'comunidad',
                'socios': [
                    {
                        'socio_legacy_id': 'soc-1',
                        'socio_nombre': socio_1.nombre,
                        'socio_rut': socio_1.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                    },
                    {
                        'socio_legacy_id': 'soc-2',
                        'socio_nombre': socio_2.nombre,
                        'socio_rut': socio_2.rut,
                        'porcentaje': '50.00',
                        'activo': True,
                        'vigente_desde': '2026-01-01',
                    },
                ],
            },
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-property-owner', args=[resolution.pk]),
            {
                'nombre_comunidad': 'Comunidad Designada Default',
                'representante_modo': ModoRepresentacionComunidad.DESIGNATED,
                'region': 'RM',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comunidad = ComunidadPatrimonial.objects.get()
        self.assertEqual(comunidad.representacion_vigente().modo_representacion, ModoRepresentacionComunidad.DESIGNATED)
        self.assertEqual(comunidad.representante_socio_id, default_representative.pk)

    def test_resolve_property_owner_manual_resolution_accepts_mixed_participants(self):
        socio_1 = Socio.objects.create(nombre='Socio Uno', rut='11111111-1', activo=True)
        empresa = Empresa.objects.create(razon_social='Inmobiliaria Puig SpA', rut='76311245-4', estado='activa')
        socio_empresa_1 = Socio.objects.create(nombre='Socio Empresa Uno', rut='44444444-4', activo=True)
        socio_empresa_2 = Socio.objects.create(nombre='Socio Empresa Dos', rut='55555555-5', activo=True)
        from patrimonio.models import ParticipacionPatrimonial

        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_empresa_1,
            empresa_owner=empresa,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )
        ParticipacionPatrimonial.objects.create(
            participante_socio=socio_empresa_2,
            empresa_owner=empresa,
            porcentaje='50.00',
            vigente_desde='2026-01-01',
            activo=True,
        )

        resolution = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-3',
            summary='Owner manual mixed',
            metadata={
                'codigo': 48,
                'direccion': 'Edificio Q 1014',
                'canonical_estado': 'activa',
                'rol_avaluo': '123-3',
                'comuna': 'Santiago',
                'tipo_inmueble': 'departamento',
                'candidate_owner_model': 'comunidad',
                'socios': [],
            },
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-property-owner', args=[resolution.pk]),
            {
                'nombre_comunidad': 'Comunidad Mixta Edificio Q',
                'representante_socio_id': socio_1.pk,
                'representante_modo': ModoRepresentacionComunidad.PATRIMONIAL_PARTICIPANT,
                'region': 'RM',
                'participaciones': [
                    {
                        'participante_tipo': 'socio',
                        'participante_id': socio_1.pk,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                    {
                        'participante_tipo': 'empresa',
                        'participante_id': empresa.pk,
                        'porcentaje': '50.00',
                        'vigente_desde': '2026-01-01',
                        'activo': True,
                    },
                ],
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comunidad = ComunidadPatrimonial.objects.get(nombre='Comunidad Mixta Edificio Q')
        participant_types = {item.participante_tipo for item in comunidad.participaciones.all()}
        self.assertEqual(participant_types, {'socio', 'empresa'})


class AuditManualResolutionScopeTests(APITestCase):
    def setUp(self):
        user_model = get_user_model()
        self.operator_role = Role.objects.create(code='OperadorDeCartera', name='Operador de cartera')
        self.user = user_model.objects.create_user(
            username='audit-scope',
            password='secret123',
            default_role_code='OperadorDeCartera',
        )
        self.context_a = self._create_operational_context(
            code='AUD-A',
            company_name='Empresa Audit A',
            company_rut='76.311.245-4',
            tenant_rut='11.111.111-1',
        )
        self.context_b = self._create_operational_context(
            code='AUD-B',
            company_name='Empresa Audit B',
            company_rut='76.390.560-8',
            tenant_rut='22.222.222-2',
        )
        self._assign_company_scope(self.user, self.context_a['empresa'])
        self.client.force_authenticate(self.user)

    def _assign_company_scope(self, user, empresa):
        scope = Scope.objects.create(
            code=f'company-{empresa.id}',
            name=f'Empresa {empresa.razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(empresa.id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=user, role=self.operator_role, scope=scope, is_primary=True)

    def _create_operational_context(self, *, code, company_name, company_rut, tenant_rut):
        empresa = Empresa.objects.create(razon_social=company_name, rut=company_rut, estado='activa')
        propiedad = Propiedad.objects.create(
            direccion=f'Av. {code} 100',
            comuna='Temuco',
            region='La Araucania',
            tipo_inmueble=TipoInmueble.LOCAL,
            codigo_propiedad=code,
            estado='activa',
            empresa_owner=empresa,
        )
        cuenta = CuentaRecaudadora.objects.create(
            empresa_owner=empresa,
            institucion='Banco Uno',
            numero_cuenta=f'ACC-{code}',
            tipo_cuenta='corriente',
            titular_nombre=empresa.razon_social,
            titular_rut=empresa.rut,
            moneda_operativa='CLP',
            estado_operativo=EstadoCuentaRecaudadora.ACTIVE,
        )
        mandato = MandatoOperacion.objects.create(
            propiedad=propiedad,
            propietario_empresa_owner=empresa,
            administrador_empresa_owner=empresa,
            recaudador_empresa_owner=empresa,
            entidad_facturadora=empresa,
            cuenta_recaudadora=cuenta,
            tipo_relacion_operativa='mandato_externo',
            autoriza_recaudacion=True,
            autoriza_facturacion=True,
            autoriza_comunicacion=True,
            estado=EstadoMandatoOperacion.ACTIVE,
            vigencia_desde='2026-01-01',
        )
        arrendatario = Arrendatario.objects.create(
            tipo_arrendatario='persona_natural',
            nombre_razon_social=f'Arrendatario {code}',
            rut=tenant_rut,
            email=f'{code.lower()}@example.com',
            telefono='999',
            domicilio_notificaciones=f'Direccion {code}',
            estado_contacto='activo',
        )
        contrato = Contrato.objects.create(
            codigo_contrato=f'CTR-{code}',
            mandato_operacion=mandato,
            arrendatario=arrendatario,
            fecha_inicio='2026-01-01',
            fecha_fin_vigente='2026-12-31',
            fecha_entrega='2026-01-01',
            dia_pago_mensual=5,
            plazo_notificacion_termino_dias=60,
            dias_prealerta_admin=90,
            estado='vigente',
        )
        periodo = PeriodoContractual.objects.create(
            contrato=contrato,
            numero_periodo=1,
            fecha_inicio='2026-01-01',
            fecha_fin='2026-12-31',
            monto_base='100000.00',
            moneda_base='CLP',
            tipo_periodo='inicial',
            origen_periodo='manual',
        )
        ContratoPropiedad.objects.create(
            contrato=contrato,
            propiedad=propiedad,
            rol_en_contrato='principal',
            porcentaje_distribucion_interna='100.00',
            codigo_conciliacion_efectivo_snapshot='111',
        )
        pago = PagoMensual.objects.create(
            contrato=contrato,
            periodo_contractual=periodo,
            mes=1,
            anio=2026,
            monto_facturable_clp='100000.00',
            monto_calculado_clp='100000.00',
            fecha_vencimiento='2026-01-05',
            estado_pago='pendiente',
            codigo_conciliacion_efectivo='111',
        )
        conexion = ConexionBancaria.objects.create(
            cuenta_recaudadora=cuenta,
            provider_key=f'provider-{code}',
            credencial_ref=f'cred-{code}',
            estado_conexion='activa',
            primaria_movimientos=True,
        )
        return {
            'empresa': empresa,
            'propiedad': propiedad,
            'cuenta': cuenta,
            'mandato': mandato,
            'contrato': contrato,
            'periodo': periodo,
            'pago': pago,
            'conexion': conexion,
        }

    def _create_movement_resolution(self, context, *, category, movement_type, amount, summary):
        movimiento = MovimientoBancarioImportado.objects.create(
            conexion_bancaria=context['conexion'],
            fecha_movimiento='2026-01-08',
            tipo_movimiento=movement_type,
            monto=amount,
            descripcion_origen=summary,
        )
        resolution = ManualResolution.objects.create(
            category=category,
            scope_type='movimiento_bancario',
            scope_reference=str(movimiento.pk),
            summary=summary,
            status='open',
        )
        return resolution, movimiento

    def test_manual_resolution_list_only_returns_in_scope_resolutions(self):
        visible_resolution, _ = self._create_movement_resolution(
            self.context_a,
            category='conciliacion.ingreso_desconocido',
            movement_type='abono',
            amount='150000.00',
            summary='Ingreso visible',
        )
        hidden_resolution, _ = self._create_movement_resolution(
            self.context_b,
            category='conciliacion.movimiento_cargo',
            movement_type='cargo',
            amount='25000.00',
            summary='Cargo fuera de scope',
        )
        hidden_migration = ManualResolution.objects.create(
            category='migration.propiedad.owner_manual_required',
            scope_type='legacy_propiedad',
            scope_reference='prop-legacy-1',
            summary='Migracion fuera de scope',
            metadata={'codigo': 46, 'direccion': 'Av. Santa Maria 9500 Dpto 1014'},
        )
        visible_distribution_conflict = ManualResolution.objects.create(
            category='migration.cobranza.distribucion_facturable_conflict',
            scope_type='pago_mensual',
            scope_reference=str(self.context_a['pago'].pk),
            summary='Conflicto distribucion visible',
            metadata={'pago_mensual_id': self.context_a['pago'].pk},
        )
        hidden_distribution_conflict = ManualResolution.objects.create(
            category='migration.cobranza.distribucion_facturable_conflict',
            scope_type='pago_mensual',
            scope_reference=str(self.context_b['pago'].pk),
            summary='Conflicto distribucion fuera de scope',
            metadata={'pago_mensual_id': self.context_b['pago'].pk},
        )

        response = self.client.get(reverse('manual-resolution-list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item['id'] for item in response.data},
            {str(visible_resolution.pk), str(visible_distribution_conflict.pk)},
        )
        self.assertNotIn(str(hidden_resolution.pk), {item['id'] for item in response.data})
        self.assertNotIn(str(hidden_migration.pk), {item['id'] for item in response.data})
        self.assertNotIn(str(hidden_distribution_conflict.pk), {item['id'] for item in response.data})

    def test_audit_snapshot_only_includes_in_scope_manual_resolutions(self):
        visible_resolution, _ = self._create_movement_resolution(
            self.context_a,
            category='conciliacion.ingreso_desconocido',
            movement_type='abono',
            amount='150000.00',
            summary='Ingreso visible snapshot',
        )
        self._create_movement_resolution(
            self.context_b,
            category='conciliacion.movimiento_cargo',
            movement_type='cargo',
            amount='25000.00',
            summary='Cargo fuera de scope snapshot',
        )

        response = self.client.get(reverse('audit-snapshot'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['manual_resolutions']), 1)
        self.assertEqual(response.data['manual_resolutions'][0]['id'], str(visible_resolution.pk))

    def test_manual_resolution_detail_returns_404_when_resolution_is_out_of_scope(self):
        hidden_resolution, _ = self._create_movement_resolution(
            self.context_b,
            category='conciliacion.movimiento_cargo',
            movement_type='cargo',
            amount='25000.00',
            summary='Cargo fuera de scope detail',
        )

        response = self.client.get(reverse('manual-resolution-detail', args=[hidden_resolution.pk]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_resolve_charge_movement_returns_404_when_resolution_is_out_of_scope(self):
        hidden_resolution, _ = self._create_movement_resolution(
            self.context_b,
            category='conciliacion.movimiento_cargo',
            movement_type='cargo',
            amount='25000.00',
            summary='Cargo fuera de scope resolver',
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-charge-movement', args=[hidden_resolution.pk]),
            {'rationale': 'No deberia poder resolverse.'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_resolve_unknown_income_rejects_payment_outside_scope(self):
        visible_resolution, _ = self._create_movement_resolution(
            self.context_a,
            category='conciliacion.ingreso_desconocido',
            movement_type='abono',
            amount='150000.00',
            summary='Ingreso visible resolver',
        )

        response = self.client.post(
            reverse('manual-resolution-resolve-unknown-income', args=[visible_resolution.pk]),
            {
                'pago_mensual_id': self.context_b['pago'].pk,
                'rationale': 'Intento de cruce fuera de scope.',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['pago_mensual_id'][0], 'El pago mensual indicado queda fuera del scope asignado.')

    def test_audit_event_list_only_returns_in_scope_events(self):
        reviewer_role = Role.objects.create(code='RevisorFiscalExterno', name='Revisor fiscal externo')
        reviewer_user = get_user_model().objects.create_user(
            username='audit-reviewer-scope',
            password='secret123',
            default_role_code='RevisorFiscalExterno',
        )
        reviewer_scope = Scope.objects.create(
            code=f'company-{self.context_a["empresa"].id}-review',
            name=f'Empresa reviewer {self.context_a["empresa"].razon_social}',
            scope_type=Scope.ScopeType.COMPANY,
            external_reference=str(self.context_a['empresa'].id),
            is_active=True,
        )
        UserScopeAssignment.objects.create(user=reviewer_user, role=reviewer_role, scope=reviewer_scope, is_primary=True)
        reviewer_client = self.client_class()
        reviewer_client.force_authenticate(reviewer_user)

        AuditEvent.objects.create(
            event_type='conciliacion.movimiento_bancario.created',
            entity_type='movimiento_bancario',
            entity_id=str(self.context_a['pago'].pk),
            summary='Evento visible',
            metadata={'empresa_id': self.context_a['empresa'].pk, 'cuenta_recaudadora_id': self.context_a['cuenta'].pk},
        )
        AuditEvent.objects.create(
            event_type='conciliacion.movimiento_bancario.created',
            entity_type='movimiento_bancario',
            entity_id=str(self.context_b['pago'].pk),
            summary='Evento fuera de scope',
            metadata={'empresa_id': self.context_b['empresa'].pk, 'cuenta_recaudadora_id': self.context_b['cuenta'].pk},
        )
        AuditEvent.objects.create(
            event_type='patrimonio.socio.updated',
            entity_type='socio',
            entity_id=str(self.context_a['empresa'].pk),
            summary='Evento colision empresa no visible',
        )
        AuditEvent.objects.create(
            event_type='contratos.arrendatario.updated',
            entity_type='arrendatario',
            entity_id=str(self.context_a['propiedad'].pk),
            summary='Evento colision propiedad no visible',
        )

        response = reviewer_client.get(reverse('audit-events'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({item['summary'] for item in response.data}, {'Evento visible'})

from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import Role, RoleScope, Scope, UserScopeAssignment
from operacion.models import CuentaRecaudadora
from patrimonio.models import Empresa, Propiedad, Socio
from users.models import User


ROLE_DEFINITIONS = (
    {
        'code': 'AdministradorGlobal',
        'name': 'Administrador global',
        'description': 'Acceso total a LeaseManager.',
    },
    {
        'code': 'OperadorDeCartera',
        'name': 'Operador de cartera',
        'description': 'Opera modulos patrimoniales, contratos, cobranza y conciliacion.',
    },
    {
        'code': 'RevisorFiscalExterno',
        'name': 'Revisor fiscal externo',
        'description': 'Acceso de lectura a modulos de control y reporting.',
    },
    {
        'code': 'Socio',
        'name': 'Socio',
        'description': 'Acceso restringido al resumen propio y reporting autorizado.',
    },
)


@dataclass(frozen=True)
class DemoUserPlan:
    username_suffix: str
    display_name: str
    role_code: str
    email_local_part: str
    scope_kind: str


USER_PLANS = (
    DemoUserPlan(
        username_suffix='admin',
        display_name='Demo Administrador Global',
        role_code='AdministradorGlobal',
        email_local_part='demo-admin',
        scope_kind='global',
    ),
    DemoUserPlan(
        username_suffix='operador',
        display_name='Demo Operador de Cartera',
        role_code='OperadorDeCartera',
        email_local_part='demo-operador',
        scope_kind='company',
    ),
    DemoUserPlan(
        username_suffix='revisor',
        display_name='Demo Revisor Fiscal Externo',
        role_code='RevisorFiscalExterno',
        email_local_part='demo-revisor',
        scope_kind='bank_account',
    ),
    DemoUserPlan(
        username_suffix='socio',
        display_name='Demo Socio',
        role_code='Socio',
        email_local_part='demo-socio',
        scope_kind='property',
    ),
)


class Command(BaseCommand):
    help = 'Siembra roles, scopes y usuarios demo reproducibles para validar RBAC no-admin.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--prefix',
            default='demo',
            help='Prefijo para los usernames demo. Default: demo',
        )
        parser.add_argument(
            '--password',
            default='demo12345',
            help='Password comun para los usuarios demo. Default: demo12345',
        )
        parser.add_argument(
            '--force-password-reset',
            action='store_true',
            help='Resetea el password aunque el usuario demo ya exista.',
        )
        parser.add_argument(
            '--company-id',
            type=int,
            help='Empresa a usar para el scope del operador y para la resolucion preferente de otros scopes.',
        )
        parser.add_argument(
            '--socio-id',
            type=int,
            help='Socio a usar para el usuario demo Socio y su metadata.socio_id.',
        )
        parser.add_argument(
            '--property-id',
            type=int,
            help='Propiedad a usar para el scope del usuario demo Socio.',
        )
        parser.add_argument(
            '--bank-account-id',
            type=int,
            help='Cuenta recaudadora a usar para el scope del usuario demo RevisorFiscalExterno.',
        )

    def handle(self, *args, **options):
        prefix = options['prefix'].strip()
        if not prefix:
            raise CommandError('El prefijo no puede venir vacio.')

        selected_company = self._select_company(options.get('company_id'))
        selected_socio = self._select_socio(options.get('socio_id'))
        selected_property = self._select_property(
            explicit_property_id=options.get('property_id'),
            socio=selected_socio,
            company=selected_company,
        )
        selected_bank_account = self._select_bank_account(
            explicit_bank_account_id=options.get('bank_account_id'),
            company=selected_company,
            socio=selected_socio,
        )

        password = options['password']
        force_password_reset = options['force_password_reset']

        warnings: list[str] = []
        if selected_company is None:
            warnings.append(
                'No hay empresas cargadas. El operador demo usara scope global hasta que exista una empresa real.'
            )
        if selected_bank_account is None:
            warnings.append(
                'No hay cuentas recaudadoras cargadas. El revisor demo usara scope global hasta que exista una cuenta real.'
            )
        if selected_socio is None:
            warnings.append(
                'No hay socios cargados. El usuario demo Socio quedara sin metadata.socio_id y no podra validar resumen propio.'
            )
        if selected_property is None:
            warnings.append(
                'No hay propiedades cargadas. El usuario demo Socio usara scope global hasta que exista una propiedad trazable.'
            )

        with transaction.atomic():
            roles = self._ensure_roles()
            scopes = self._ensure_scopes(
                company=selected_company,
                property_obj=selected_property,
                bank_account=selected_bank_account,
            )

            created_or_updated_users: list[tuple[User, Scope]] = []
            for plan in USER_PLANS:
                scope = self._resolve_scope_for_plan(plan.scope_kind, scopes)
                role = roles[plan.role_code]
                self._ensure_role_scope(role=role, scope=scope)
                user = self._ensure_user(
                    prefix=prefix,
                    plan=plan,
                    password=password,
                    force_password_reset=force_password_reset,
                    socio=selected_socio if plan.role_code == 'Socio' else None,
                )
                self._ensure_assignment(user=user, role=role, scope=scope)
                created_or_updated_users.append((user, scope))

        self.stdout.write(self.style.SUCCESS('Seed de acceso demo aplicado correctamente.'))
        for user, scope in created_or_updated_users:
            role_label = user.default_role_code
            self.stdout.write(
                f'- {user.username} | rol={role_label} | scope={scope.code} | password={password}'
            )
        if selected_socio is not None:
            self.stdout.write(
                f'  socio demo vinculado: {selected_socio.nombre} ({selected_socio.pk})'
            )
        for warning in warnings:
            self.stdout.write(self.style.WARNING(f'ADVERTENCIA: {warning}'))

    def _select_company(self, company_id: int | None) -> Empresa | None:
        if company_id is not None:
            try:
                return Empresa.objects.get(pk=company_id)
            except Empresa.DoesNotExist as error:
                raise CommandError(f'La empresa {company_id} no existe.') from error

        return (
            Empresa.objects.filter(estado='activa').order_by('razon_social', 'id').first()
            or Empresa.objects.order_by('razon_social', 'id').first()
        )

    def _select_socio(self, socio_id: int | None) -> Socio | None:
        if socio_id is not None:
            try:
                return Socio.objects.get(pk=socio_id)
            except Socio.DoesNotExist as error:
                raise CommandError(f'El socio {socio_id} no existe.') from error

        return (
            Socio.objects.filter(activo=True).order_by('nombre', 'id').first()
            or Socio.objects.order_by('nombre', 'id').first()
        )

    def _select_property(
        self,
        *,
        explicit_property_id: int | None,
        socio: Socio | None,
        company: Empresa | None,
    ) -> Propiedad | None:
        if explicit_property_id is not None:
            try:
                return Propiedad.objects.get(pk=explicit_property_id)
            except Propiedad.DoesNotExist as error:
                raise CommandError(f'La propiedad {explicit_property_id} no existe.') from error

        if socio is not None:
            direct_property = Propiedad.objects.filter(socio_owner=socio).order_by('codigo_propiedad', 'id').first()
            if direct_property is not None:
                return direct_property

            community_property = (
                Propiedad.objects.filter(comunidad_owner__participaciones__participante_socio=socio)
                .distinct()
                .order_by('codigo_propiedad', 'id')
                .first()
            )
            if community_property is not None:
                return community_property

            company_property = (
                Propiedad.objects.filter(empresa_owner__participaciones__participante_socio=socio)
                .distinct()
                .order_by('codigo_propiedad', 'id')
                .first()
            )
            if company_property is not None:
                return company_property

        if company is not None:
            scoped_company_property = (
                Propiedad.objects.filter(empresa_owner=company).order_by('codigo_propiedad', 'id').first()
            )
            if scoped_company_property is not None:
                return scoped_company_property

        return Propiedad.objects.order_by('codigo_propiedad', 'id').first()

    def _select_bank_account(
        self,
        *,
        explicit_bank_account_id: int | None,
        company: Empresa | None,
        socio: Socio | None,
    ) -> CuentaRecaudadora | None:
        if explicit_bank_account_id is not None:
            try:
                return CuentaRecaudadora.objects.get(pk=explicit_bank_account_id)
            except CuentaRecaudadora.DoesNotExist as error:
                raise CommandError(
                    f'La cuenta recaudadora {explicit_bank_account_id} no existe.'
                ) from error

        if company is not None:
            company_account = (
                CuentaRecaudadora.objects.filter(empresa_owner=company).order_by('institucion', 'numero_cuenta').first()
            )
            if company_account is not None:
                return company_account

        if socio is not None:
            socio_account = (
                CuentaRecaudadora.objects.filter(socio_owner=socio).order_by('institucion', 'numero_cuenta').first()
            )
            if socio_account is not None:
                return socio_account

        return CuentaRecaudadora.objects.order_by('institucion', 'numero_cuenta').first()

    def _ensure_roles(self) -> dict[str, Role]:
        roles: dict[str, Role] = {}
        for role_data in ROLE_DEFINITIONS:
            role, _ = Role.objects.update_or_create(
                code=role_data['code'],
                defaults={
                    'name': role_data['name'],
                    'description': role_data['description'],
                    'is_system_role': True,
                },
            )
            roles[role.code] = role
        return roles

    def _ensure_scopes(
        self,
        *,
        company: Empresa | None,
        property_obj: Propiedad | None,
        bank_account: CuentaRecaudadora | None,
    ) -> dict[str, Scope]:
        scopes = {
            'global': self._upsert_scope(
                code='global-backoffice',
                name='Backoffice completo LeaseManager',
                scope_type=Scope.ScopeType.GLOBAL,
                external_reference='backoffice',
                metadata={'seed_source': 'seed_demo_access'},
            )
        }

        if company is not None:
            scopes['company'] = self._upsert_scope(
                code=f'company-{company.pk}',
                name=f'Empresa {company.razon_social}',
                scope_type=Scope.ScopeType.COMPANY,
                external_reference=str(company.pk),
                metadata={
                    'seed_source': 'seed_demo_access',
                    'model': 'Empresa',
                    'label': company.razon_social,
                },
            )

        if property_obj is not None:
            scopes['property'] = self._upsert_scope(
                code=f'property-{property_obj.pk}',
                name=f'Propiedad {property_obj.codigo_propiedad}',
                scope_type=Scope.ScopeType.PROPERTY,
                external_reference=str(property_obj.pk),
                metadata={
                    'seed_source': 'seed_demo_access',
                    'model': 'Propiedad',
                    'label': property_obj.codigo_propiedad,
                },
            )

        if bank_account is not None:
            scopes['bank_account'] = self._upsert_scope(
                code=f'bank-account-{bank_account.pk}',
                name=f'Cuenta {bank_account.numero_cuenta}',
                scope_type=Scope.ScopeType.BANK_ACCOUNT,
                external_reference=str(bank_account.pk),
                metadata={
                    'seed_source': 'seed_demo_access',
                    'model': 'CuentaRecaudadora',
                    'label': bank_account.numero_cuenta,
                },
            )

        return scopes

    def _upsert_scope(
        self,
        *,
        code: str,
        name: str,
        scope_type: str,
        external_reference: str,
        metadata: dict,
    ) -> Scope:
        scope, _ = Scope.objects.update_or_create(
            code=code,
            defaults={
                'name': name,
                'scope_type': scope_type,
                'external_reference': external_reference,
                'metadata': metadata,
                'is_active': True,
            },
        )
        return scope

    def _resolve_scope_for_plan(self, scope_kind: str, scopes: dict[str, Scope]) -> Scope:
        return scopes.get(scope_kind) or scopes['global']

    def _ensure_role_scope(self, *, role: Role, scope: Scope) -> None:
        RoleScope.objects.update_or_create(
            role=role,
            scope=scope,
            defaults={
                'permission_set': ['read', 'write'] if role.code in {'AdministradorGlobal', 'OperadorDeCartera'} else ['read']
            },
        )

    def _ensure_user(
        self,
        *,
        prefix: str,
        plan: DemoUserPlan,
        password: str,
        force_password_reset: bool,
        socio: Socio | None,
    ) -> User:
        username = f'{prefix}-{plan.username_suffix}'
        email = f'{plan.email_local_part}@leasemanager.test'
        metadata = {'seed_source': 'seed_demo_access'}
        if socio is not None:
            metadata['socio_id'] = socio.pk

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'display_name': plan.display_name,
                'default_role_code': plan.role_code,
                'is_active': True,
                'metadata': metadata,
            },
        )
        user.email = email
        user.display_name = plan.display_name
        user.default_role_code = plan.role_code
        user.is_active = True
        user.metadata = metadata
        if created or force_password_reset:
            user.set_password(password)
        user.save()
        return user

    def _ensure_assignment(self, *, user: User, role: Role, scope: Scope) -> None:
        UserScopeAssignment.objects.filter(user=user, effective_to__isnull=True).exclude(
            role=role,
            scope=scope,
        ).update(effective_to=timezone.now(), is_primary=False)

        assignment, _ = UserScopeAssignment.objects.get_or_create(
            user=user,
            role=role,
            scope=scope,
            defaults={
                'is_primary': True,
                'metadata': {'seed_source': 'seed_demo_access'},
                'effective_to': None,
            },
        )
        assignment.is_primary = True
        assignment.metadata = {'seed_source': 'seed_demo_access'}
        assignment.effective_to = None
        assignment.save(update_fields=['is_primary', 'metadata', 'effective_to'])


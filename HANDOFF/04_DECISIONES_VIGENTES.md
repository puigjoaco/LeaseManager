# Decisiones Vigentes

## 1. Decisiones cerradas

### 1.1 Root, nombre y repositorio

- [D:/Proyectos/LeaseManager/Produccion 1.0](/D:/Proyectos/LeaseManager/Produccion%201.0) es la codebase activa del greenfield.
- [D:/Proyectos/LeaseManager](/D:/Proyectos/LeaseManager) sigue siendo legacy read-only.
- El nombre vigente del proyecto nuevo es `LeaseManager`.
- `LeaseControl` deja de ser nombre activo dentro del root actual.
- El remoto oficial del greenfield es [puigjoaco/LeaseManager](https://github.com/puigjoaco/LeaseManager).
- El repo anterior queda como [puigjoaco/LeaseManager-legacy](https://github.com/puigjoaco/LeaseManager-legacy).

### 1.2 Diseño comunitario y migración

Estas decisiones siguen cerradas y no deben reabrirse:

- `MandatoOperacion` distingue `Propietario`, `AdministradorOperativo`, `Recaudador` y `EntidadFacturadora`.
- `CuentaRecaudadora` pertenece exactamente al `Recaudador`.
- `ComunidadPatrimonial` soporta participantes `Socio` o `Empresa`.
- `RepresentacionComunidad` separa representante de administrador operativo.
- `PagoMensual` representa el cobro total.
- `DistribucionCobroMensual` representa la atribución económica y facturable.
- `SII`, `Contabilidad` y `Reporting` consumen distribución y no el owner bancario como proxy.
- baseline local cerrado: `leasemanager_migration_run_20260409_v7`.
- baseline remoto cerrado: `leasemanager-staging`.

### 1.3 Arquitectura y stack

- stack canónico:
  - backend `Django 5`
  - API `DRF`
  - base de datos `PostgreSQL`
  - colas `Celery + Redis`
  - frontend `React + TypeScript + Vite`
- no introducir como base:
  - `Next.js`
  - `Supabase` como modelo final
  - `Django Ninja`
  - `pgvector`
  - microservicios

### 1.4 Estado del producto/backoffice

Quedó cerrado que el backoffice actual ya cubre una primera versión operable de:

- `Patrimonio`
- `Operacion`
- `Contratos`
- `Cobranza`
- `Conciliacion`
- `Contabilidad`
- `SII`
- `Reporting`

Y además ya incorpora:

- creación rápida;
- edición base de registros operativos;
- navegación contextual;
- controles visibles por rol;
- permisos efectivos de backend por rol;
- seed reproducible de perfiles demo;
- primera capa real de filtrado por scope en lectura y escritura.

### 1.5 Política de permisos vigente

Quedó cerrada esta política RBAC inicial:

- `AdministradorGlobal`: lectura y escritura total.
- `OperadorDeCartera`: lectura y escritura en módulos operativos.
- `RevisorFiscalExterno`: lectura en módulos de control.
- `Socio`: acceso restringido a reporting y, en backend, solo a su propio resumen de socio si `metadata.socio_id` coincide.
- los alias legacy como `operator` se normalizan a `OperadorDeCartera`.

## 2. Decisiones provisionales vigentes

- el seed reproducible de usuarios/roles/scopes demo ya existe, pero todavía falta la pasada manual completa de validación con esos perfiles;
- ya existe una primera capa de filtrado por scope en lectura y escritura, pero todavía puede haber huecos finos en recorridos reales del backoffice;
- el siguiente trabajo recomendado ya no es abrir otro bounded context base, sino:
  - probar el sistema con `demo-operador`, `demo-revisor` y `demo-socio`;
  - y ajustar alcance/permisos donde falle la experiencia real.

## 3. Decisiones descartadas

- seguir tratando el trabajo actual como “elegir el siguiente módulo”;
- seguir confiando solo en el frontend para permisos;
- versionar `DATABASE_URL` completa o metadata con credenciales;
- seguir usando el repo legacy como remoto del greenfield;
- reabrir el diseño comunitario como si siguiera pendiente.

## 4. Reglas que no deben volver a violarse

- no reabrir decisiones comunitarias ya cerradas salvo contradicción documental real;
- no volver a llamar `LeaseControl` al root activo;
- no volver a exponer secretos o URLs completas de conexión en artefactos versionados;
- no asumir que el frontend basta para controlar permisos;
- no tratar la cuenta bancaria como proxy de ownership contable;
- no empujar el greenfield al repo `LeaseManager-legacy`;
- no asumir que los datos de prueba locales están versionados.

## 5. Punto aún abierto

No queda una decisión semántica principal abierta en migración comunitaria. El punto abierto actual es operativo:

- **qué huecos reales siguen apareciendo al recorrer el sistema como `demo-operador`, `demo-revisor` y `demo-socio`, y qué último round de visibilidad/mutación scopeada todavía falta cerrar**

# Decisiones Vigentes

## 1. Decisiones cerradas

### 1.1 Root, nombre y repositorio

- [D:/Proyectos/LeaseManager/Produccion 1.0](/D:/Proyectos/LeaseManager/Produccion%201.0) es la codebase activa del greenfield.
- [D:/Proyectos/LeaseManager](/D:/Proyectos/LeaseManager) sigue siendo legacy read-only.
- El nombre vigente del proyecto nuevo es `LeaseManager`.
- `LeaseControl` deja de ser nombre activo dentro del root actual.
- El remoto oficial del greenfield es [puigjoaco/LeaseManager](https://github.com/puigjoaco/LeaseManager).
- El repo anterior queda como [puigjoaco/LeaseManager-legacy](https://github.com/puigjoaco/LeaseManager-legacy).

### 1.2 Diseno comunitario y migracion

Estas decisiones siguen cerradas y no deben reabrirse:

- `MandatoOperacion` distingue `Propietario`, `AdministradorOperativo`, `Recaudador` y `EntidadFacturadora`.
- `CuentaRecaudadora` pertenece exactamente al `Recaudador`.
- `ComunidadPatrimonial` soporta participantes `Socio` o `Empresa`.
- `RepresentacionComunidad` separa representante de administrador operativo.
- `PagoMensual` representa el cobro total.
- `DistribucionCobroMensual` representa la atribucion economica y facturable.
- `SII`, `Contabilidad` y `Reporting` consumen distribucion y no el owner bancario como proxy.
- baseline local cerrado: `leasemanager_migration_run_20260409_v7`.
- baseline remoto cerrado: `leasemanager-staging`.

### 1.3 Arquitectura y stack

- stack canonico:
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

Quedo cerrado que el backoffice actual ya cubre una primera version operable de:

- `Patrimonio`
- `Operacion`
- `Contratos`
- `Documentos`
- `Canales`
- `Cobranza`
- `Conciliacion`
- `Audit`
- `Contabilidad`
- `SII`
- `Reporting`

Y ademas ya incorpora:

- creacion rapida;
- edicion base de registros operativos;
- navegacion contextual;
- controles visibles por rol;
- permisos efectivos de backend por rol;
- seed reproducible de perfiles demo;
- filtrado real por scope en lectura y en varias escrituras/acciones;
- modularizacion amplia del frontend fuera de `App.tsx`.

### 1.5 Politica de permisos vigente

Quedo cerrada esta politica RBAC/scope actualmente efectiva:

- `AdministradorGlobal`: lectura y escritura total.
- `OperadorDeCartera`: lectura y escritura en modulos operativos, `Audit`, `Documentos` y `Canales`.
- `RevisorFiscalExterno`: lectura en modulos de control, `Audit`, `Contabilidad`, `SII` y `Reporting`.
- `Socio`: acceso restringido a su propio resumen en `Reporting`.
- los alias legacy como `operator` se normalizan a `OperadorDeCartera`.

### 1.6 Topologia publica vigente

Quedo cerrada como baseline operativa la topologia actual:

- frontend publico en proyecto Vercel `leasemanager-backoffice`;
- dominio publico vigente:
  - [https://leasemanager-backoffice.vercel.app](https://leasemanager-backoffice.vercel.app)
- backend publico en Railway:
  - servicio web `surprising-balance`
  - servicio worker `spirited-recreation`
  - Redis online en el proyecto Railway `content-friendship`
- dominio publico vigente del backend:
  - [https://surprising-balance-production.up.railway.app](https://surprising-balance-production.up.railway.app)
- `Vercel Root Directory = frontend`
- Vercel y Railway ya quedaron conectados al repo Git oficial.

## 2. Decisiones provisionales vigentes

- la validacion publica por perfil ya avanzo mucho, pero sigue siendo smoke y no un barrido exhaustivo de todas las acciones con data real;
- el backend publico actualmente usa el Postgres de staging Supabase como base de datos operativa; eso es operativo hoy, pero no debe asumirse como decision final de largo plazo;
- el dataset remoto sigue siendo escaso, por lo que varias vistas publicas muestran `0 registros` aunque la app y los permisos funcionen bien;
- `Compliance` sigue sin superficie equivalente en frontend.

## 3. Decisiones descartadas

- seguir tratando el trabajo actual como “elegir el siguiente modulo base”;
- seguir confiando solo en el frontend para permisos;
- versionar `DATABASE_URL` completa o metadata con credenciales;
- seguir usando el repo legacy como remoto del greenfield;
- reabrir el diseno comunitario como si siguiera pendiente;
- volver a tratar el bootstrap `Vercel + Railway` como si siguiera sin cerrar.

## 4. Reglas que no deben volver a violarse

- no reabrir decisiones comunitarias ya cerradas salvo contradiccion documental real;
- no volver a llamar `LeaseControl` al root activo;
- no volver a exponer secretos o URLs completas de conexion en artefactos versionados;
- no asumir que el frontend basta para controlar permisos;
- no tratar la cuenta bancaria como proxy de ownership contable;
- no empujar el greenfield al repo `LeaseManager-legacy`;
- no asumir que los datos de prueba locales o remotos estan versionados;
- no romper `VITE_API_BASE_URL`, el enlace Git de Vercel o `Root Directory=frontend` sin revalidacion completa;
- no tocar Railway web/worker/Redis como si fueran scaffolding descartable: hoy son parte del estado operativo real.

## 5. Punto aun abierto

No queda una decision semantica principal abierta en migracion comunitaria.

El punto abierto actual es operativo y de producto:

- **como continuar el trabajo sobre un stack publico ya operativo, empezando por mejorar la representatividad de la data remota y luego elegir el siguiente frente funcional real sin perder el wiring de produccion publica**

# Handoff Index

Ultima actualizacion: 2026-04-12

Root activo: [D:/Proyectos/LeaseManager/Produccion 1.0](/D:/Proyectos/LeaseManager/Produccion%201.0)  
Directorio de handoff: [D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF)

## Estado actual del trabajo

El greenfield activo ya no esta en fase de naming, migracion comunitaria ni bootstrap de infraestructura. Ese tramo quedo cerrado.

Estado real consolidado al cierre de este handoff:

- `LeaseManager` es el nombre vigente y exclusivo del greenfield activo.
- el repo oficial del greenfield es [puigjoaco/LeaseManager](https://github.com/puigjoaco/LeaseManager).
- el repo historico separado es [puigjoaco/LeaseManager-legacy](https://github.com/puigjoaco/LeaseManager-legacy).
- el baseline de migracion comunitaria sigue validado en:
  - local PostgreSQL: `leasemanager_migration_run_20260409_v7`
  - staging Supabase: `leasemanager-staging`
- la topologia publica actual ya esta operativa:
  - frontend publico: [https://leasemanager-backoffice.vercel.app](https://leasemanager-backoffice.vercel.app)
  - backend publico: [https://surprising-balance-production.up.railway.app](https://surprising-balance-production.up.railway.app)
  - worker remoto: servicio Railway `spirited-recreation`
  - proyecto Railway activo: `content-friendship`
  - Redis remoto online dentro del proyecto Railway
- el proyecto Vercel `leasemanager-backoffice` ya esta conectado al repo Git y su `Root Directory` quedo fijado a `frontend`.
- el backend publico actual usa como base de datos operativa el Postgres de staging Supabase; eso es estado operativo vigente, no una decision definitiva de largo plazo.
- el frontend/backoffice local y publico ya cubre:
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
  - `Compliance`
  - `Reporting`
- el backend ya incorpora:
  - RBAC efectivo por rol;
  - seed reproducible de usuarios/roles/scopes demo;
  - filtrado real por scope en lectura y en varias escrituras/acciones;
  - endurecimiento operativo de `Audit`, `Documentos` y `Canales`;
  - health y ready checks publicos funcionales.
- el frontend ya no esta solo en modularizacion inicial:
  - [api.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/api.ts)
  - [shell.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/shell.tsx)
  - [view-config.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/view-config.ts)
  - workspaces extraidos para `Audit`, `Documentos`, `Canales`, `Reporting`, `Contabilidad`, `SII` y otros bloques operativos
- la smoke matrix publica ya fue validada en navegador real con:
  - `demo-admin`
  - `demo-operador`
  - `demo-revisor`
  - `demo-socio`
- `Compliance` ya tiene smoke admin-only dedicada en el sitio publico:
  - lectura de exportaciones sensibles;
  - descifrado de payload;
  - preparacion de exportacion;
  - revocacion;
- el baseline demo remoto de `Compliance` ya no tiene solo exportaciones:
  - `5` politicas de retencion;
  - `5` exportaciones sensibles, con una revocada en la smoke;
- ya existen commands versionados para bootstrap demo remoto:
  - `bootstrap_demo_operational_data`
  - `bootstrap_demo_control_baseline`
  - `bootstrap_demo_control_activity`
  - `bootstrap_demo_tax_monthly_flow`
  - `bootstrap_demo_tax_annual_flow`
  - `bootstrap_demo_showcase_access`
  - `bootstrap_demo_compliance_exports`
  - `bootstrap_demo_compliance_policies`
  - `bootstrap_demo_public_showcase`
- el entorno remoto ya no tiene solo baseline estructural de control:
  - empresa `1`, periodo `2026-05` con `1` evento contable posteado;
  - `1` asiento contable;
  - `1` obligacion mensual;
  - `1` cierre mensual aprobado;
  - `1` borrador `F29` en estado `pendiente_datos`;
  - snapshots de `LibroDiario`, `LibroMayor` y `BalanceComprobacion`;
  - capacidades `SII` de la empresa `1` con `certificado_ref` demo no sensible.
- el entorno remoto ya tiene tambien un primer flujo tributario mensual visible para empresa `1`, periodo `2026-05`:
  - `1` pago conciliado exacto;
  - `1` `DTE` en borrador;
  - `F29` en estado `preparado`;
  - reporting financiero mensual con `dtes_emitidos = 1` y `monto_cobrado_total_clp > 0`.
- la configuracion fiscal ya no depende de shell para `tasa_ppm_vigente`:
  - el backend la expone por API;
  - el backoffice la expone para edicion base en `Contabilidad`.
- el entorno remoto ya tiene tambien un primer flujo anual visible para empresa `1`, año tributario `2027`:
  - `ProcesoRentaAnual` en `preparado`;
  - `DDJJ` en `preparado`;
  - `F22` en `preparado`;
  - `ddjj_habilitadas = ['1887']`;
  - doce cierres mensuales aprobados del año comercial `2026`.
- `demo-revisor` ya no esta limitado solo a company `1` para el showcase:
  - ahora tiene scopes activos sobre empresas `1`, `2`, `3` y `4`;
  - puede ver `4` configuraciones fiscales, `4` `F29`, `4` bloques anuales y `5` `DTE` por API pública.
- el showcase mensual `2026-05` ya no quedo cojo:
  - las empresas `1`, `2`, `3` y `4` tienen al menos un `DTE` visible para `demo-revisor`.

## Borrador vigente

No existe un borrador documental unico nuevo para el tramo actual.

La base principal vigente hoy se reparte entre:

1. [D:/Proyectos/LeaseManager/Produccion 1.0/01_Set_Vigente/PRD_CANONICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md)
2. [D:/Proyectos/LeaseManager/Produccion 1.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md)
3. [D:/Proyectos/LeaseManager/Produccion 1.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md)
4. [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/App.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/App.tsx)
5. [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/api.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/api.ts)
6. [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/shell.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/shell.tsx)
7. [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/view-config.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/view-config.ts)
8. [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/permissions.py)
9. [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/scope_access.py)
10. [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/seed_demo_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/seed_demo_access.py)
11. [D:/Proyectos/LeaseManager/Produccion 1.0/docs/DEPLOY_FRONTEND_VERCEL.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/DEPLOY_FRONTEND_VERCEL.md)
12. [D:/Proyectos/LeaseManager/Produccion 1.0/docs/DEPLOY_BACKEND_GREENFIELD.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/DEPLOY_BACKEND_GREENFIELD.md)
13. [D:/Proyectos/LeaseManager/Produccion 1.0/docs/ROLL_OUT_BACKEND_FRONTEND.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ROLL_OUT_BACKEND_FRONTEND.md)
14. [D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/ComplianceWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/ComplianceWorkspace.tsx)
15. [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/bootstrap_demo_operational_data.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/bootstrap_demo_operational_data.py)
16. [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/bootstrap_demo_control_baseline.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/bootstrap_demo_control_baseline.py)
17. [D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/bootstrap_demo_compliance_exports.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/bootstrap_demo_compliance_exports.py)

Para el subproblema comunitario ya cerrado, sigue mandando:

- [D:/Proyectos/LeaseManager/Produccion 1.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md)

## Decision central vigente hoy

La decision central vigente ya no es de diseno comunitario, modularizacion primaria ni wiring de deploy.

La linea vigente hoy es:

1. mantener cerrada la migracion comunitaria y sus reglas ya confirmadas;
2. tratar el backoffice actual como la base operativa real del greenfield;
3. tratar el stack publico `Vercel + Railway` ya online como baseline de continuidad;
4. no confiar solo en el frontend para permisos;
5. usar el backend como fuente de verdad de RBAC/scope;
6. no volver a romper el wiring de `VITE_API_BASE_URL`, `Root Directory=frontend` o la topologia publica del backend;
7. usar el entorno remoto enriquecido como base de trabajo, sin depender de comandos manuales no versionados.

## Pregunta abierta mas importante

La pregunta abierta mas importante ahora es:

- **como seguir el trabajo de producto sobre un stack publico ya operativo ahora que `Compliance` tambien quedo abierto y que ya existen commands reproducibles para bootstrap demo remoto, sin reabrir infraestructura ya cerrada**
- **como seguir el trabajo de producto sobre un stack publico ya operativo ahora que `Compliance` tambien quedo validado en flujo admin-only y que ya existen commands reproducibles para bootstrap demo remoto, sin reabrir infraestructura ya cerrada**

## Orden de lectura recomendado

1. [01_CONTEXTO_MAESTRO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/01_CONTEXTO_MAESTRO.md)
2. [04_DECISIONES_VIGENTES.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/04_DECISIONES_VIGENTES.md)
3. [03_CRONOLOGIA.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/03_CRONOLOGIA.md)
4. [02_FUENTES_Y_RUTAS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/02_FUENTES_Y_RUTAS.md)
5. [06_BORRADOR_ACTUAL.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/06_BORRADOR_ACTUAL.md)
6. [05_HALLAZGOS_Y_RIESGOS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/05_HALLAZGOS_Y_RIESGOS.md)
7. [08_PENDIENTES_Y_PROXIMOS_PASOS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/08_PENDIENTES_Y_PROXIMOS_PASOS.md)
8. [07_RESPUESTAS_EXTERNAS_LITERAL.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/07_RESPUESTAS_EXTERNAS_LITERAL.md)
9. [10_CONTROL_DE_CALIDAD.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/10_CONTROL_DE_CALIDAD.md)
10. [11_MANIFEST.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/11_MANIFEST.md)
11. [09_BOOTSTRAP_NUEVO_THREAD.txt](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/09_BOOTSTRAP_NUEVO_THREAD.txt)

## Que contiene cada archivo

- `01_CONTEXTO_MAESTRO.md`: contexto consolidado del proyecto, jerarquia de verdad, arquitectura de fuentes, rollout publico, `Compliance` y rectificaciones relevantes.
- `02_FUENTES_Y_RUTAS.md`: inventario de fuentes y piezas clave con rutas absolutas, metadatos y contexto de runtime publico.
- `03_CRONOLOGIA.md`: linea temporal secuencial desde el cierre comunitario hasta la modularizacion, el rollout `Railway + Vercel`, `Compliance` y los bootstrap demo remotos.
- `04_DECISIONES_VIGENTES.md`: decisiones cerradas, provisionales, descartadas y reglas que no deben volver a violarse.
- `05_HALLAZGOS_Y_RIESGOS.md`: hallazgos firmes/probables y riesgos tecnicos, procesales, narrativos y estrategicos.
- `06_BORRADOR_ACTUAL.md`: ranking de piezas vigentes y base principal para continuar.
- `07_RESPUESTAS_EXTERNAS_LITERAL.md`: respuestas externas antiguas conservadas literalmente.
- `08_PENDIENTES_Y_PROXIMOS_PASOS.md`: siguiente trabajo real y secuencia recomendada desde el estado actual.
- `09_BOOTSTRAP_NUEVO_THREAD.txt`: prompt listo para abrir un nuevo thread sin responder de fondo antes de cargar contexto.
- `10_CONTROL_DE_CALIDAD.md`: control de calidad del paquete, limites, vacios y riesgos remanentes.
- `11_MANIFEST.md`: manifiesto final de archivos clave con rutas, tamanos, fechas y estado de lectura.

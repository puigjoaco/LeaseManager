# Hallazgos y Riesgos

## 1. Hallazgos firmes

### 1.1 Hallazgos de producto e implementacion

- El greenfield ya no es un “backend con shell”; existe una capa usable de backoffice tanto local como publica.
- El frontend actual ya expone modulos principales y secundarios relevantes.
- El backend ya no depende solo de `IsAuthenticated`; existe una politica RBAC explicita en [permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/permissions.py).
- El repo ya tiene seed reproducible de acceso demo en [seed_demo_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/seed_demo_access.py).
- El backend ya tiene filtrado por scope en [scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/scope_access.py).
- `Audit`, `Documentos` y `Canales` ya tienen superficie real en frontend.
- La modularizacion del frontend ya paso del corte inicial y hoy incluye `api.ts`, `shell.tsx`, `view-config.ts` y workspaces extraidos para los bloques mas sensibles.
- `Compliance` ya tiene superficie real en frontend para admin.

### 1.2 Hallazgos de entorno y rollout

- Docker local, PostgreSQL, Redis, backend y frontend se levantaron correctamente en el entorno de trabajo.
- El baseline local `v7` sigue usable sobre PostgreSQL real.
- El frontend publico responde en [https://leasemanager-backoffice.vercel.app](https://leasemanager-backoffice.vercel.app).
- El backend publico responde en [https://surprising-balance-production.up.railway.app](https://surprising-balance-production.up.railway.app).
- El `ready` publico devolvio `ready = true`, `database = up`, `redis = up`.
- El proyecto Vercel ya quedo conectado al repo Git y con `Root Directory=frontend`.
- Railway ya quedo con web + worker + Redis operativos sobre el repo Git oficial.

### 1.3 Hallazgos de seguridad y red

- La fuga de `DATABASE_URL` completa en artefactos versionados ya fue corregida.
- La capa de permisos existe tanto en UI como en backend.
- El hardening ya cubre no solo lectura, sino tambien varias escrituras/acciones con IDs directos para perfiles no-admin.
- El backend publico responde correctamente con CORS para el origen del frontend publico.
- El login al endpoint publico se valido por HTTP directo desde el origen del frontend.
- La normalizacion de `DATA_EXPORT_ENCRYPTION_KEY` ya evita 500 de `Compliance` por claves no-Fernet.

### 1.4 Hallazgos de validacion publica

- `demo-admin` inicia sesion en el sitio publico y ve la superficie completa esperada.
- `demo-operador` inicia sesion en el sitio publico y solo ve superficie operativa + `Audit`.
- `demo-revisor` inicia sesion en el sitio publico y solo ve `Audit`, `Contabilidad`, `SII` y `Reporting`, con banners readonly coherentes.
- `demo-socio` inicia sesion en el sitio publico y solo ve `Reporting`, con lectura propia.
- `Compliance` ya quedo validado en flujo admin-only sobre el sitio publico:
  - lee exportaciones sensibles existentes;
  - descifra payloads correctamente;
  - permite preparar nuevas exportaciones;
  - permite revocarlas;
- `Contabilidad` / `SII` / `Reporting` ya tienen una primera huella demo no vacia en remoto:
  - `1` evento contable posteado;
  - `1` asiento contable;
  - `1` obligacion mensual;
  - `1` cierre aprobado;
  - `1` borrador `F29`;
  - snapshots contables por periodo;
- `SII` ya tiene tambien su primer artefacto transaccional visible en remoto:
  - `1` pago conciliado exacto;
  - `1` `DTE` borrador para empresa `1`;
  - `1` `F29` preparada para empresa `1`, periodo `2026-05`;
  - reporting financiero mensual con `dtes_emitidos = 1`.
- el ajuste de `tasa_ppm_vigente` ya no requiere shell o acceso directo a BD:
  - se puede leer y actualizar por API;
  - el backoffice ya tiene superficie base para editarlo.
- el bloque anual ya no esta completamente vacio en remoto:
  - empresa `1` tiene `ProcesoRentaAnual`, `DDJJ` y `F22` en `preparado` para `2027`.
- `demo-revisor` ya puede ver el showcase de control multicompañía:
  - `4` configuraciones fiscales;
  - `4` `F29`;
  - `5` `DTE`;
  - y los bloques anuales preparados para las cuatro empresas activas.
- el showcase mensual `2026-05` ya quedó útil en las cuatro empresas activas:
  - `1`: `2` DTE / `3` eventos / cobrado `2363011.00`
  - `2`: `1` DTE / `2` eventos / cobrado `401030.00`
  - `3`: `1` DTE / `2` eventos / cobrado `722039.00`
  - `4`: `1` DTE / `2` eventos / cobrado `409013.00`
- el deploy CLI de Vercel del root activo volvió a funcionar:
  - se eliminó el bloqueo práctico de `frontend/frontend`;
  - el redeploy de `leasemanager-backoffice` ya corre por script con token local.
- el repo ya no depende exclusivamente del MCP de navegador para verificación visual:
  - `smoke-public-backoffice.mjs` valida `demo-admin` y `demo-revisor` y deja screenshots.
- El entorno remoto ya se enriquecio con datos derivados reales:
  - UF de abril y mayo 2026;
  - pagos de abril y mayo;
  - estados de cuenta recalculados;
  - baseline minimo de control para empresa 1;
  - actividad mensual demo de control para empresa 1 en `2026-05`;
  - primer flujo tributario mensual demo de empresa 1;
  - primer flujo tributario anual demo de empresa 1 para `2027`;
  - exportaciones demo de `Compliance`;
  - baseline demo de politicas de retencion de `Compliance`.

## 2. Hallazgos probables

- El siguiente foco de trabajo ya no deberia estar en wiring de infraestructura, sino en:
  - mejorar la utilidad del entorno remoto;
  - enriquecer la data visible;
  - y retomar trabajo funcional real sobre esa base.
- El README mejoro, pero sigue sin reemplazar al handoff ni al codigo como foto de maxima fidelidad.

## 3. Riesgos tecnicos

- El backend publico actual usa el Postgres de staging Supabase; eso funciona hoy, pero es una dependencia operativa delicada si se deja sin decision explicita posterior.
- La data remota es todavia escasa; eso puede hacer parecer “vacias” vistas que en realidad estan bien cableadas.
- las politicas de retencion demo de `Compliance` ya existen y son consistentes con tests y PRD minimo, pero no equivalen todavia a una politica legal-operativa final cerrada fuera del entorno demo.
- El wiring manual entre Vercel y Railway ya existe y funciona, pero puede degradarse si alguien cambia root, dominios o variables sin revalidacion.
- Aunque `App.tsx` bajo mucho de peso, sigue siendo una pieza importante; el costo de cambio todavia existe.

## 4. Riesgos procesales o de flujo

- Riesgo de que otro thread retome desde un handoff viejo y piense que:
  - el backend publico aun no existe;
  - `VITE_API_BASE_URL` sigue faltando;
  - o que el trabajo real sigue siendo “terminar de modularizar”.
- Riesgo de que se siga enriqueciendo el entorno remoto con comandos manuales puntuales y se pierda la trazabilidad, pese a que ya hay commands versionados.
- Riesgo de que se abra un frente funcional nuevo sin antes preservar la continuidad documental del rollout publico ya cerrado.

## 5. Riesgos probatorios o de evidencia

- Las respuestas externas literales archivadas siguen siendo validas para el tramo comunitario, pero no describen el estado actual del backoffice publico.
- Las imagenes originales pegadas por el usuario no existen como archivos locales originales; solo quedo su absorcion analitica.
- Algunas sesiones de browser automation mostraron falsos negativos transitorios (`unreachable`, `ERR_NO_BUFFER_SPACE`) aunque el backend respondia `200`; para conectividad, mandan los checks HTTP directos y el browser reset si es necesario.

## 6. Riesgos narrativos

- README y handoff previos pueden subestimar el estado real del despliegue publico.
- El historial reciente mezcla refactor, deploy prep y runtime actions; sin cronologia, es facil perder el orden exacto de cierre del rollout.

## 7. Riesgos estrategicos

- Si no se mejora pronto la representatividad de la data remota, el entorno publico puede dar una falsa impresion de “producto vacio” pese a tener flujo y permisos correctos.
- Si no se mantiene la disciplina de scope antes de abrir nuevos modulos o nuevas acciones, se puede reintroducir fuga de visibilidad por comodidad de frontend.
- Si se toca Vercel/Railway como si siguieran siendo infraestructura transitoria, se puede romper una base publica que hoy ya esta funcional.

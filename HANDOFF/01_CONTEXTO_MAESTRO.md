# Contexto Maestro

## 1. Proyecto, raiz activa y alcance actual

Proyecto activo: `LeaseManager` greenfield  
Root activo: [D:/Proyectos/LeaseManager/Produccion 1.0](/D:/Proyectos/LeaseManager/Produccion%201.0)  
Root legacy read-only: [D:/Proyectos/LeaseManager](/D:/Proyectos/LeaseManager)

El root activo hoy contiene simultaneamente:

- el set canónico vigente del producto y la arquitectura;
- la codebase greenfield funcional;
- el pipeline de migración ya validado;
- el paquete `HANDOFF/` para continuidad.

Rectificación vigente:

- dentro del root activo, el nombre correcto es `LeaseManager`;
- `LeaseControl` es histórico y no debe reintroducirse dentro de `Produccion 1.0`.

## 2. Que esta cerrado y que cambio desde el handoff previo

### 2.1 Tramo cerrado antes de esta actualización

Ya estaba cerrado antes de este refresh:

- diseño comunitario final;
- implementación de comunidades/recaudación/atribución;
- validación del pipeline local y staging;
- formalización del repo nuevo y separación del legacy.

### 2.2 Que cambio materialmente en este thread largo

Desde el handoff viejo de `2026-04-10`, el trabajo ya no quedó en “elegir el siguiente módulo”.

Se ejecutó una secuencia amplia y verificable:

- se corrigió la serialización de metadata de migración para no volver a exponer `DATABASE_URL` completa;
- se alineó [PRD_CANONICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md) con la implementación real de `Recaudador`, comunidades mixtas y `DistribucionCobroMensual`;
- se transformó el frontend desde un shell mínimo a un backoffice funcional sobre React/Vite;
- se abrió la superficie de frontend para:
  - `Patrimonio`
  - `Operacion`
  - `Contratos`
  - `Cobranza`
  - `Conciliacion`
  - `Contabilidad`
  - `SII`
  - `Reporting`
- se añadieron:
  - creación rápida;
  - edición de registros base;
  - navegación contextual entre módulos;
  - UI visible por rol;
- se endureció el backend con permisos RBAC reales por rol;
- luego se agregó un seed reproducible de usuarios/roles/scopes demo;
- luego se añadió una capa explícita de filtrado por scope;
- luego se endurecieron lectura y escritura para perfiles no-admin;
- y ese hardening quedó cubierto por pruebas específicas de scope y por una suite ampliada de módulos.

## 3. Estado real del repo y del código

### 3.1 Git y remotos

Estado verificado al cierre:

- git root activo: [D:/Proyectos/LeaseManager/Produccion 1.0](/D:/Proyectos/LeaseManager/Produccion%201.0)
- remoto oficial: [https://github.com/puigjoaco/LeaseManager.git](https://github.com/puigjoaco/LeaseManager.git)
- remoto legacy: [https://github.com/puigjoaco/LeaseManager-legacy.git](https://github.com/puigjoaco/LeaseManager-legacy.git)
- `HEAD` actual: `bdde843`
- working tree local: `clean` esperado tras publicar este refresh documental

Importante:

- este refresh documental no agrega lógica de producto;
- su propósito es dejar continuidad y working tree ordenados después del hardening reciente.

### 3.2 Entorno local

Estado local validado durante este trabajo:

- Docker Desktop y `docker compose` levantados;
- `leasemanager-postgres` y `leasemanager-redis` operativos;
- backend local sirviendo en `127.0.0.1:8000`;
- frontend local sirviendo en `127.0.0.1:5173`;
- `health` local con `database = up` y `redis = up`.

### 3.3 Baseline local y datos no versionados

El baseline local de referencia sigue siendo:

- `leasemanager_migration_run_20260409_v7`

Y durante este thread se volvió a reconstruir localmente ese baseline sobre PostgreSQL usando el flujo validado.

Además, existe una capa de datos operativos locales de prueba:

- usuario local `admin` de desarrollo;
- usuarios demo reproducibles:
  - `demo-admin`
  - `demo-operador`
  - `demo-revisor`
  - `demo-socio`
- registros `TEST LOCAL` en la cadena operacional principal.

Regla crítica de continuidad:

- esos datos de prueba existen en la base local;
- no son parte versionada del repositorio;
- un thread nuevo no debe asumir que existirán si la base local se recrea desde cero.

## 4. Jerarquia de verdad hoy

La jerarquía correcta hoy es:

1. fuentes primarias del set activo:
   - [PRD_CANONICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md)
   - [ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md](/D:/Proyectos/LeaseManager/Produccion%201.0/02_ADR_Activos/ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md)
   - [ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md](/D:/Proyectos/LeaseManager/Produccion%201.0/02_ADR_Activos/ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md)
2. roadmap y dependencias activas:
   - [ROADMAP_TECNICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md)
   - [MODULOS_Y_DEPENDENCIAS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md)
3. implementación viva del greenfield:
   - [App.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/App.tsx)
   - [permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/permissions.py)
   - [scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/scope_access.py)
   - [seed_demo_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/seed_demo_access.py)
   - vistas y serializers de backend por módulo
4. para el dominio comunitario ya cerrado:
   - [ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md)
   - [migration/enrichments.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/enrichments.py)
   - [migration/importers.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/importers.py)
5. artefactos validados de migración y verificación;
6. el paquete `HANDOFF/` actualizado;
7. respuestas externas literales archivadas.

Si hay conflicto:

- manda la fuente primaria;
- luego la implementación validada;
- luego el handoff;
- y la divergencia debe quedar explicitada.

## 5. Divergencias y rectificaciones que deben conocerse

### 5.1 El handoff previo quedó materialmente desactualizado

El paquete viejo seguía anclado a:

- `HEAD = c6add42`
- pregunta abierta = “qué módulo abrir”
- estado del frontend = todavía muy preliminar

Eso ya no representa la foto real.

### 5.2 Divergencia entre documentación ligera y estado real del frontend

[README.md](/D:/Proyectos/LeaseManager/Produccion%201.0/README.md) sigue subestimando el estado real de la UI.

A esta altura:

- el frontend ya no es solo shell;
- ya cubre la mayor parte del flujo operacional base y parte del control tributario.

Aquí manda la implementación actual en [App.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/App.tsx).

### 5.3 Divergencia entre documentación ligera y estado real del hardening RBAC/scope

La documentación resumida del root no refleja todavía:

- el seed reproducible de usuarios demo;
- la capa `scope_access.py`;
- el hardening inicial de lectura y escritura por scope;
- la suite ampliada de validación.

Consecuencia:

- para continuidad, manda el código y este paquete `HANDOFF/*`, no el README resumido.

## 6. Como debe leerse el material hoy

La forma correcta de retomar hoy no es:

- volver a abrir el diseño comunitario;
- volver a discutir el nombre del proyecto;
- ni pensar que el siguiente trabajo sigue siendo “abrir el próximo módulo”.

La forma correcta de retomar hoy es:

1. asumir que el backoffice base ya existe;
2. asumir que la API ya tiene permisos por rol y primera capa real de scope;
3. usar PRD + roadmap como guía del sistema;
4. usar el código actual como foto viva del producto;
5. tratar como siguiente trabajo real:
   - validar manualmente el sistema como `demo-operador`, `demo-revisor` y `demo-socio`;
   - corregir cualquier hueco restante de visibilidad o mutación;
   - y luego publicar/normalizar el refresh documental pendiente.

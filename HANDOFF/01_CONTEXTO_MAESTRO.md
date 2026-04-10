# Contexto Maestro

## 1. Proyecto y raiz activa

Proyecto activo: `LeaseManager` greenfield  
Root activo: [D:/Proyectos/LeaseManager/Produccion 1.0](/D:/Proyectos/LeaseManager/Produccion%201.0)  
Root legacy read-only: [D:/Proyectos/LeaseManager](/D:/Proyectos/LeaseManager)

El root activo contiene simultaneamente:

- el set canonico (`01` a `08`);
- la codebase greenfield (`backend`, `frontend`, `infra`, `migration`, `docs`);
- el paquete `HANDOFF/`;
- artefactos de migracion y corrida de inspeccion dentro de `migration/` y `backend/`.

## 2. Objetivo actual del trabajo

El objetivo actual ya no es “descubrir el diseño correcto”.  
Ese tramo fue cerrado y bajado a implementacion.

El objetivo actual es:

- **usar el diseño ya implementado para ejecutar la migracion real del backlog comunitario y de cartera actual sobre el destino real del greenfield**, sin volver a inventar datos ni reabrir decisiones ya cerradas.

Estado al cierre de este handoff:

- esa ejecucion real ya se completo sobre PostgreSQL local del greenfield;
- la base usada fue `leasemanager_migration_run_20260408_v3`;
- el resultado final quedo alineado con la inspeccion:
  - `56` contratos;
  - `748` periodos;
  - `66` mandatos;
  - `0` `ManualResolution` abiertas.
- posteriormente, esa secuencia quedo encapsulada en un paso reusable:
  - `migration/scripts/resolve_current_community_resolutions.py`;
  - flujo validado en limpio sobre `leasemanager_migration_run_20260408_v6`.

## 3. Jerarquia de verdad a esta fecha

La jerarquia correcta hoy es:

1. fuentes primarias del set activo, especialmente [PRD_CANONICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md);
2. ADRs activos, especialmente:
   - [ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md](/D:/Proyectos/LeaseManager/Produccion%201.0/02_ADR_Activos/ADR_ARQUITECTURA_001_BANCA_MULTI_PROVIDER.md)
   - [ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md](/D:/Proyectos/LeaseManager/Produccion%201.0/02_ADR_Activos/ADR_ARQUITECTURA_008_CONTABILIDAD_NATIVA.md)
3. la especificacion tecnica vigente: [ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md);
4. la implementacion actual del backend y del pipeline (`backend/*`, `migration/*`);
5. artefactos de datos derivados y corrida de inspeccion (`legacy_rows_supabase.json`, `legacy_seed_bundle.regenerated.json`, `bundle-inspect-final.db`);
6. handoffs previos y piezas procesales historicas;
7. respuestas externas pegadas por el usuario y clarificaciones del thread actual.

Si un handoff previo contradice una fuente primaria o la implementacion ya validada, manda la fuente primaria o la implementacion validada, y debe dejarse constancia de la divergencia.

## 4. Que cambio desde el handoff anterior

El paquete anterior de `2026-04-05` quedo sustancialmente desactualizado.

Cambios cerrados en este thread:

- se creo la especificacion tecnica final de dominio para comunidades, recaudacion y atribucion economica;
- se implementaron en backend:
  - participaciones mixtas `Socio` / `Empresa`;
  - `RepresentacionComunidad`;
  - `Recaudador` explicito en `MandatoOperacion`;
  - `DistribucionCobroMensual`;
  - consumo de distribucion por `SII`, `Contabilidad` y `Reporting`;
- se agrego `migration/enrichments.py` para representar verdad de negocio confirmada por el usuario cuando la fuente legacy no la trae;
- se regenero el bundle real desde legacy usando acceso read-only a Supabase;
- se hizo una corrida de inspeccion aislada sobre SQLite (`bundle-inspect-final.db`);
- la corrida de inspeccion final quedo con:
  - `56` contratos;
  - `748` periodos;
  - `66` mandatos;
  - `0` resoluciones manuales abiertas.
- se ejecuto la corrida real equivalente sobre PostgreSQL local del greenfield (`leasemanager_migration_run_20260408_v3`);
- durante esa corrida se detecto y corrigio un bug del importer:
  - el rerun borraba participaciones de comunidades resueltas manualmente;
  - eso dejaba a `Edificio Q` sin `EntidadFacturadora` y a las comunidades sin composicion activa;
  - la sincronizacion de `ParticipacionPatrimonial` se corrigio para preservar comunidades resueltas y seguir siendo idempotente.

## 5. Reglas de negocio cerradas en este thread

Estas reglas ya no deben tratarse como abiertas:

- cada propiedad comunitaria crea una comunidad propia por propiedad;
- `Joaquin Puig Vittini` es el `representante_designado` de todas las comunidades actuales dentro del backlog migrado;
- las comunidades estandar del set actual pueden ser de 4 socios o de 6 socios, segun propiedad;
- `Bulnes 699` es comunidad de 6 socios;
- `Edificio Q Dpto 1014` y `Edificio Q Bod. 17 / Est. 33` son comunidades mixtas con exactamente la misma composicion:
  - 5 socios;
  - `Inmobiliaria Puig SpA`;
- cuando `vigente_desde` falta en participaciones legacy, se usa `2017-03-16`;
- cuando la propiedad esta en Temuco y la region viene vacia, se usa `La Araucania`;
- `Estacionamiento 96` ya no pertenece a la cartera actual y queda fuera de esta migracion;
- `Paulina Fuenzalida` queda con RUT `19.076.873-2` y su contrato actual se reapunta al `Estacionamiento 97`;
- `José Ibáñez` y `Claudio Galdames` quedan fuera de la migracion actual por no pertenecer ya a la cartera vigente.

## 6. Estado real del backend y del pipeline

### 6.1 Backend

Estado real:

- el backend no esta solo “diseñado”; esta modificado y validado;
- la implementacion relevante vive, entre otros, en:
  - [backend/patrimonio/models.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/patrimonio/models.py)
  - [backend/operacion/models.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/operacion/models.py)
  - [backend/cobranza/models.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/cobranza/models.py)
  - [backend/contabilidad/services.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/contabilidad/services.py)
  - [backend/sii/services.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/sii/services.py)
  - [backend/reporting/services.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/reporting/services.py)
  - [backend/audit/services.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/audit/services.py)

Validacion funcional realizada en este thread:

- `manage.py check` OK;
- `manage.py makemigrations --check --dry-run --noinput` OK sobre SQLite temporal;
- suite ampliada de `113` tests OK sobre SQLite temporal.
- `manage.py test core.tests_migration_pipeline audit.tests` OK tras corregir el bug del rerun de participaciones comunitarias.

### 6.2 Pipeline de migracion

Estado real del pipeline:

- `transformers.py` ya incorpora enriquecimientos de negocio confirmados por el usuario;
- `importers.py` ya consume el modelo nuevo de comunidades y mandatos;
- el export read-only desde legacy se hizo contra Supabase usando credenciales locales inspeccionadas parcialmente en [D:/Proyectos/LeaseManager/.env.production.local](/D:/Proyectos/LeaseManager/.env.production.local) sin transcribir secretos;
- el artefacto base de extraccion es [legacy_rows_supabase.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/legacy_rows_supabase.json);
- el artefacto canónico vigente es [legacy_seed_bundle.regenerated.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/legacy_seed_bundle.regenerated.json).

### 6.3 Corrida de inspeccion

La corrida de inspeccion final se hizo sobre:

- [bundle-inspect-final.db](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/bundle-inspect-final.db)

Resultado final:

- `56` contratos importados;
- `748` periodos importados;
- `66` mandatos operativos;
- `0` `ManualResolution` abiertas.

Importante:

- esta corrida fue de inspeccion sobre SQLite;
- no equivale todavia a corrida ejecutada sobre el destino real final del greenfield.

### 6.4 Corrida real local sobre PostgreSQL

La corrida real local se hizo sobre:

- base destino PostgreSQL `leasemanager_migration_run_20260408_v3`;
- backend configurado localmente en [D:/Proyectos/LeaseManager/Produccion 1.0/backend/.env](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/.env) apuntando a `localhost:5433`.

Secuencia ejecutada:

1. levantar PostgreSQL y Redis locales desde `infra/docker-compose.yml`;
2. migrar Django en una base limpia;
3. regenerar el bundle actual desde `legacy_rows_supabase.json` usando el codigo vigente;
4. importar una primera vez;
5. resolver las `16` propiedades comunitarias pendientes;
6. rerun de importacion;
7. tercer rerun de idempotencia.

Resultado final:

- `56` contratos importados;
- `748` periodos importados;
- `66` mandatos operativos;
- `0` `ManualResolution` abiertas;
- `16` `ManualResolution` de propiedad comunitaria quedaron como `resolved`;
- `16` comunidades creadas;
- `70` participaciones comunitarias activas preservadas;
- `Edificio Q Dpto 1014` y `Edificio Q Bod. Nº 17, Est. Nº 33` quedaron con `Inmobiliaria Puig SpA` como `EntidadFacturadora`.

### 6.5 Flujo reusable validado

Despues de la corrida local inicial, el paso intermedio de resolucion comunitaria se formalizo como script:

- [migration/scripts/resolve_current_community_resolutions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/scripts/resolve_current_community_resolutions.py)

Secuencia reusable validada sobre `leasemanager_migration_run_20260408_v6`:

1. `import_seed_bundle.py`
2. `resolve_current_community_resolutions.py`
3. `import_seed_bundle.py`
4. `import_seed_bundle.py` de idempotencia

Resultado final nuevamente validado:

- `56` contratos;
- `748` periodos;
- `66` mandatos;
- `0` `ManualResolution` abiertas;
- `16` `ManualResolution` resueltas;
- `16` comunidades;
- `70` participaciones comunitarias activas.

### 6.6 Runner único validado

El flujo completo tambien quedo encapsulado en:

- [migration/scripts/run_current_migration_flow.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/scripts/run_current_migration_flow.py)

Ese runner fue validado en limpio sobre PostgreSQL `leasemanager_migration_run_20260409_v7` con el bundle:

- [migration/bundles/legacy_seed_bundle.regenerated.current_2026-04-08.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/legacy_seed_bundle.regenerated.current_2026-04-08.json)

Artefacto de salida:

- [migration/bundles/run_current_migration_flow_v7.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/run_current_migration_flow_v7.json)

`final_state` validado del runner:

- `56` contratos;
- `748` periodos;
- `66` mandatos;
- `0` `ManualResolution` abiertas;
- `16` comunidades;
- `70` participaciones comunitarias activas.

Decision operativa posterior:

- esa base `leasemanager_migration_run_20260409_v7` fue elegida como baseline local de referencia de esta etapa;
- [backend/.env](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/.env) queda apuntando a `v7`.

### 6.7 Rehearsal local automatizado

Para repetir una corrida limpia local sin pasos manuales intermedios, quedo disponible:

- [migration/scripts/rehearse_current_migration_flow.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/scripts/rehearse_current_migration_flow.py)

Validacion operativa:

- base creada automaticamente: `leasemanager_migration_run_20260410_v9`;
- artefacto final: [migration/bundles/rehearse_current_migration_flow_v9.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/rehearse_current_migration_flow_v9.json)

`runner_result.final_state` del rehearsal:

- `56` contratos;
- `748` periodos;
- `66` mandatos;
- `0` `ManualResolution` abiertas;
- `16` comunidades;
- `70` participaciones comunitarias activas.

### 6.8 Gate automatico de validacion

El runner [migration/scripts/run_current_migration_flow.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/scripts/run_current_migration_flow.py) ahora incluye validacion automatica del `final_state`.

Comportamiento:

- si el estado final esperado no coincide, el script termina con codigo no-cero;
- si coincide, deja `validation.ok = true`.

Recheck operativo:

- base baseline: `leasemanager_migration_run_20260409_v7`;
- artefacto: [migration/bundles/run_current_migration_flow_v7_recheck.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/run_current_migration_flow_v7_recheck.json)

### 6.9 Promocion a target PostgreSQL existente

El paso equivalente para un PostgreSQL ya creado, pensado para staging/Supabase, quedo encapsulado en:

- [migration/scripts/promote_current_migration_flow.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/scripts/promote_current_migration_flow.py)

Comportamiento:

- ejecuta `migrate`;
- verifica que el target quede vacio tras migrar, salvo que se fuerce lo contrario;
- corre el flujo validado;
- falla si `final_state` no coincide con el esperado.

Validacion operativa local:

- base de prueba: `leasemanager_migration_run_20260410_v10`;
- artefacto: [migration/bundles/promote_current_migration_flow_v10.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/promote_current_migration_flow_v10.json)

### 6.10 Supabase staging real

Se ejecuto el paso siguiente fuera del entorno local:

- organizacion renombrada a `Puig Projects`;
- proyecto staging nuevo creado: `leasemanager-staging`;
- project ref: `ubccvzaklmkiavppnzcf`;
- region: `South America (São Paulo)`;
- conexion validada: `Session pooler` / `Shared Pooler` en `aws-1-sa-east-1.pooler.supabase.com:5432`.

Estado final validado en Supabase:

- `56` contratos;
- `748` periodos;
- `66` mandatos;
- `0` `ManualResolution` abiertas;
- `16` comunidades;
- `70` participaciones comunitarias activas.

Artefacto:

- [migration/bundles/supabase_staging_verification_2026-04-10.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/supabase_staging_verification_2026-04-10.json)

Nota operativa:

- el comando largo de promocion hacia Supabase supero el timeout local del shell, pero la base remota alcanzo igualmente el estado final correcto;
- la verificacion se hizo luego directamente sobre PostgreSQL remoto.

## 7. Como debe leerse el material hoy

La forma correcta de retomar ya no es:

- “volver a discutir si el diseño de comunidades es correcto”;
- ni “seguir destrabando comunidad por comunidad en el modelo viejo”.

La forma correcta es:

1. leer la especificacion tecnica final;
2. contrastarla con los enriquecimientos vigentes y la implementacion real;
3. tomar la corrida de inspeccion como prueba de que el backlog comunitario del scope actual ya no requiere resoluciones manuales;
4. tomar la corrida local PostgreSQL como prueba de que el mismo flujo funciona fuera de SQLite;
5. mover el foco, si hace falta, a la promocion o repeticion sobre otro entorno mas persistente del greenfield.

## 8. Divergencias y rectificaciones que deben conocerse

### 8.1 Divergencia con el handoff de 2026-04-05

El paquete previo queda desactualizado porque:

- seguia tratando como abiertas decisiones ya cerradas;
- seguia presentando el trabajo como diseño no implementado;
- seguia mostrando backlog manual amplio de comunidades.

Ese estado ya no es vigente.

### 8.2 Divergencia entre legacy crudo y verdad de negocio actual

El extracto legacy por si solo no representaba correctamente:

- `Edificio Q Dpto 1014`;
- `Edificio Q Bod. 17 / Est. 33`;
- `Paulina Fuenzalida` en `Estacionamiento 97`;
- exclusiones de cartera actual como `Estacionamiento 96`.

Eso se resolvio mediante enriquecimientos explicitos del pipeline, respaldados por confirmaciones del usuario en este thread.



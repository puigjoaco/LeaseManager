# Handoff Index

Ultima actualizacion: 2026-04-07

Root activo: [D:/Proyectos/LeaseManager/Produccion 1.0](/D:/Proyectos/LeaseManager/Produccion%201.0)  
Directorio de handoff: [D:/Proyectos/LeaseManager/Produccion 1.0/HANDOFF](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF)

## Estado actual del trabajo

El greenfield `LeaseManager` sigue siendo la codebase activa.  
El problema de dominio de comunidades, recaudacion y atribucion economica ya no esta solo auditado: fue **implementado** en el backend, validado por pruebas, contrastado con una corrida de inspeccion del pipeline sobre SQLite aislada y luego **ejecutado tambien sobre PostgreSQL local del greenfield**.

Estado de la corrida de inspeccion final:

- `56` contratos importados;
- `748` periodos importados;
- `66` mandatos operativos;
- `0` resoluciones manuales abiertas en la base de inspeccion.

Estado de la corrida real local final sobre PostgreSQL:

- base destino: `leasemanager_migration_run_20260408_v3`;
- `56` contratos importados;
- `748` periodos importados;
- `66` mandatos operativos;
- `0` resoluciones manuales abiertas.

Durante esa corrida se detecto y corrigio un bug real del rerun:

- `migration/importers.py` borraba participaciones comunitarias resueltas manualmente al hacer reimport;
- eso dejaba a las comunidades sin participaciones activas y a `Edificio Q` sin `EntidadFacturadora`;
- el importer fue corregido para sincronizar participaciones por owner del bundle sin borrar indiscriminadamente las comunidades ya resueltas.

Ademas, el paso intermedio de resolucion comunitaria quedo automatizado y validado:

- nuevo script reusable: `migration/scripts/resolve_current_community_resolutions.py`;
- secuencia reusable validada: `import -> resolve_current_community_resolutions.py -> import -> import`;
- base de validacion operativa final del flujo reusable: `leasemanager_migration_run_20260408_v6`.

Luego se encapsulo tambien el flujo completo en un solo runner:

- nuevo script: `migration/scripts/run_current_migration_flow.py`;
- validado en limpio sobre `leasemanager_migration_run_20260409_v7`;
- `final_state` del runner:
  - `56` contratos;
  - `748` periodos;
  - `66` mandatos;
  - `0` resoluciones manuales abiertas;
- `16` comunidades;
- `70` participaciones comunitarias activas.

Luego se encapsulo tambien el rehearsal local completo:

- nuevo script: `migration/scripts/rehearse_current_migration_flow.py`;
- crea base nueva + migra + corre el runner completo;
- validado en limpio sobre `leasemanager_migration_run_20260410_v9`;
- artefacto: `migration/bundles/rehearse_current_migration_flow_v9.json`.

Luego se agrego un gate de validacion automatica del estado final:

- `run_current_migration_flow.py` ahora verifica por defecto que el resultado termine en el estado esperado;
- validacion rechecqueada sobre la base baseline `leasemanager_migration_run_20260409_v7`;
- artefacto: `migration/bundles/run_current_migration_flow_v7_recheck.json`.

Luego se agrego el paso equivalente para target PostgreSQL ya existente:

- nuevo script: `migration/scripts/promote_current_migration_flow.py`;
- pensado para staging/Supabase o cualquier PostgreSQL remoto ya creado;
- valida que el target quede vacio tras `migrate`;
- validado localmente contra `leasemanager_migration_run_20260410_v10`;
- artefacto: `migration/bundles/promote_current_migration_flow_v10.json`.

Tambien quedo documentado el paso siguiente hacia Supabase:

- nuevo documento: `docs/SUPABASE_STAGING_PLAYBOOK.md`;
- indica cuando usar direct connection y cuando usar Supavisor session mode;
- el comando recomendado usa `promote_current_migration_flow.py`.

Estado mas reciente:

- la organizacion Supabase fue renombrada a `Puig Projects`;
- se creo un proyecto nuevo limpio `leasemanager-staging`;
- se identifico como conexion correcta `Session pooler` / `Shared Pooler` en `aws-1-sa-east-1.pooler.supabase.com:5432`;
- la base staging quedo validada con el estado esperado;
- artefacto final: `migration/bundles/supabase_staging_verification_2026-04-10.json`.

Tambien quedo un verificador reusable del target:

- nuevo script: `migration/scripts/verify_current_migration_target.py`;
- validado contra Supabase staging;
- artefacto: `migration/bundles/verify_current_migration_target_supabase.json`.

El trabajo ya no esta en “cerrar el diseno” ni en “probar solo en SQLite”.  
El estado actual ya incluye **corrida real local del greenfield validada con integridad semantica**.

## Borrador vigente

Base principal hoy: [D:/Proyectos/LeaseManager/Produccion 1.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md)

## Decision central vigente hoy

La solucion vigente ya adoptada e implementada es:

1. `MandatoOperacion` distingue `Propietario`, `AdministradorOperativo`, `Recaudador` y `EntidadFacturadora`;
2. `ComunidadPatrimonial` soporta participantes `Socio` o `Empresa`;
3. `PagoMensual` sigue siendo el cobro total, pero `SII`, `Contabilidad` y `Reporting` consumen `DistribucionCobroMensual`;
4. para el backlog comunitario actual, `Joaquin Puig Vittini` queda como `representante_designado`;
5. los vacios legacy confirmados por el usuario se resuelven mediante enriquecimientos explicitos del pipeline, no con parches manuales ad hoc.

## Pregunta abierta mas importante

Ya no queda una pregunta semantica principal sobre comunidades dentro del scope actual.  
La pregunta operativa principal ahora es:

- **si esta corrida local PostgreSQL debe tomarse como destino suficiente para esta etapa, o si el siguiente paso es repetir/promover el mismo flujo hacia otro entorno mas persistente o compartido del greenfield**

## Orden de lectura recomendado

1. [01_CONTEXTO_MAESTRO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/01_CONTEXTO_MAESTRO.md)
2. [04_DECISIONES_VIGENTES.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/04_DECISIONES_VIGENTES.md)
3. [06_BORRADOR_ACTUAL.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/06_BORRADOR_ACTUAL.md)
4. [03_CRONOLOGIA.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/03_CRONOLOGIA.md)
5. [05_HALLAZGOS_Y_RIESGOS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/05_HALLAZGOS_Y_RIESGOS.md)
6. [08_PENDIENTES_Y_PROXIMOS_PASOS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/08_PENDIENTES_Y_PROXIMOS_PASOS.md)
7. [02_FUENTES_Y_RUTAS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/02_FUENTES_Y_RUTAS.md)
8. [07_RESPUESTAS_EXTERNAS_LITERAL.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/07_RESPUESTAS_EXTERNAS_LITERAL.md)
9. [10_CONTROL_DE_CALIDAD.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/10_CONTROL_DE_CALIDAD.md)
10. [11_MANIFEST.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/11_MANIFEST.md)
11. [09_BOOTSTRAP_NUEVO_THREAD.txt](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/09_BOOTSTRAP_NUEVO_THREAD.txt)

## Que contiene cada archivo

- `01_CONTEXTO_MAESTRO.md`: contexto consolidado, jerarquia de verdad, estado real del backend, estado real del pipeline y como leer el material hoy.
- `02_FUENTES_Y_RUTAS.md`: inventario de fuentes primarias, piezas de trabajo, implementacion y artefactos de inspeccion, con rutas absolutas.
- `03_CRONOLOGIA.md`: linea temporal del trabajo, incluyendo implementacion real, enriquecimientos y corrida de inspeccion final.
- `04_DECISIONES_VIGENTES.md`: decisiones cerradas, provisionales, descartadas y reglas que ya no deben violarse.
- `05_HALLAZGOS_Y_RIESGOS.md`: hallazgos firmes, riesgos tecnicos y riesgos operativos remanentes.
- `06_BORRADOR_ACTUAL.md`: ranking del borrador vigente y cual debe usarse como base principal.
- `07_RESPUESTAS_EXTERNAS_LITERAL.md`: respuestas externas pegadas por el usuario de forma literal completa y advertencias sobre material parcial.
- `08_PENDIENTES_Y_PROXIMOS_PASOS.md`: estado del backlog real, trabajo restante y secuencia correcta para continuar.
- `09_BOOTSTRAP_NUEVO_THREAD.txt`: prompt listo para abrir un thread nuevo sin reanalizar desde cero.
- `10_CONTROL_DE_CALIDAD.md`: control de completitud, vacios y riesgos del paquete.
- `11_MANIFEST.md`: manifiesto final de archivos clave con rol, metadata y si fueron realmente leidos.



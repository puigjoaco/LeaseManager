# Pendientes y Proximos Pasos

## 1. Pendiente principal

El pendiente principal ya no es de diseño ni de backlog manual del scope actual.  
La corrida real local sobre PostgreSQL ya fue ejecutada y validada.

El pendiente principal ahora pasa a ser, si hace falta:

- **decidir si el staging Supabase ya validado debe tomarse como destino suficiente para la siguiente etapa o si aun debe promoverse a otro entorno adicional**.

## 2. Que ya no falta verificar dentro del scope actual de comunidades

Ya no falta verificar, para el backlog actual:

- semantica de `representante`;
- comunidades de 4 y 6 socios;
- `Edificio Q Dpto 1014`;
- `Edificio Q Bod. 17 / Est. 33`;
- `Bulnes 699`;
- `Paulina -> Estacionamiento 97`;
- fecha por defecto de participaciones;
- region por defecto de propiedades de Temuco.

Todo eso ya quedo cerrado e incorporado al pipeline.

## 3. Trabajo que sigue abierto

### 3.1 Ejecucion real

- la ejecucion real local ya se completo sobre `leasemanager_migration_run_20260408_v3`;
- el flujo correcto ya quedo probado asi:
  1. regenerar bundle actual;
  2. importar;
  3. ejecutar [migration/scripts/resolve_current_community_resolutions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/scripts/resolve_current_community_resolutions.py);
  4. rerun del import;
  5. rerun adicional de idempotencia.
- si se usa otro entorno, debe repetirse exactamente esta secuencia.

### 3.2 Staging remoto

- el proyecto Supabase `leasemanager-staging` ya fue creado y validado;
- el estado final remoto ya coincide con el esperado;
- si se necesita rerun remoto, debe usarse `promote_current_migration_flow.py` con la conexion `Session pooler` del proyecto.

### 3.2 Trazabilidad del pipeline

- preservar como referencia del estado actual:
  - [legacy_rows_supabase.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/legacy_rows_supabase.json)
  - [legacy_seed_bundle.regenerated.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/legacy_seed_bundle.regenerated.json)
  - [migration/enrichments.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/enrichments.py)

### 3.3 Riesgo residual

- si cambia la cartera actual, hay que mantener `migration/enrichments.py` alineado;
- si el destino real ya contiene datos parciales, la corrida debe observar idempotencia y posibles diferencias de estado.

## 4. Proximo paso recomendado

Secuencia recomendada para continuar correctamente:

1. la base local baseline ya quedo fijada en `leasemanager_migration_run_20260409_v7`;
2. el staging remoto baseline ya quedo fijado en Supabase `leasemanager-staging`;
3. para rerun remoto, usar [legacy_seed_bundle.regenerated.current_2026-04-08.json](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/bundles/legacy_seed_bundle.regenerated.current_2026-04-08.json) y [migration/scripts/promote_current_migration_flow.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/scripts/promote_current_migration_flow.py);
4. para rehearsal local desde cero, preferir [migration/scripts/rehearse_current_migration_flow.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/scripts/rehearse_current_migration_flow.py);
5. solo si hace falta depurar, descomponer nuevamente en `import -> resolve_current_community_resolutions.py -> import -> import`;
6. verificar en el destino:
   - `56` contratos;
   - `748` periodos;
   - `66` mandatos;
   - `0` `ManualResolution` abiertas;
   - `70` participaciones comunitarias activas;
   - `Inmobiliaria Puig SpA` como `EntidadFacturadora` en ambos casos de `Edificio Q`.

## 5. Que no hacer a continuacion

- no volver a discutir el modelo comunitario como si siguiera abierto;
- no correr una migracion real en un destino ambiguo;
- no borrar ni ignorar `migration/enrichments.py`;
- no reintroducir `Estacionamiento 96`, `José Ibáñez` o `Claudio Galdames` en la migracion actual;
- no mover a Paulina de vuelta al `96`.

## 6. Trabajo reservado para la siguiente etapa

### Etapa de promocion o repeticion

- aplicar la misma corrida a otro entorno del greenfield solo si hace falta salir del entorno local ya validado.

### Etapa de verificacion post-corrida

- comparar conteos reales con la inspeccion final:
  - `56` contratos
  - `748` periodos
  - `66` mandatos
  - `0` manual resolutions abiertas

### Etapa posterior

- solo si el destino real difiere de la inspeccion:
  - investigar la diferencia concreta;
  - corregir pipeline o estado destino con evidencia.


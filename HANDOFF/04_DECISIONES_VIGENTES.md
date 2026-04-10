# Decisiones Vigentes

## 1. Decisiones cerradas

### 1.1 Root y fuentes

- `D:/Proyectos/LeaseManager/Produccion 1.0` es la codebase activa del greenfield.
- `D:/Proyectos/LeaseManager` sigue siendo legacy read-only.
- El set canonico manda sobre lo historico.

### 1.2 Disciplina de trabajo

- no rehacer scaffold;
- no commit ni deploy todavia;
- no usar `git add .`;
- usar `apply_patch` para ediciones manuales;
- no copiar secretos al handoff ni al repo;
- no inventar datos para cerrar backlog.

### 1.3 Diseño de dominio

Estas decisiones ya quedaron cerradas e implementadas:

- `MandatoOperacion` distingue `Propietario`, `AdministradorOperativo`, `Recaudador` y `EntidadFacturadora`;
- `CuentaRecaudadora` debe pertenecer exactamente al `Recaudador`;
- `ComunidadPatrimonial` soporta participantes `Socio` o `Empresa`;
- `RepresentacionComunidad` separa representante de administrador operativo;
- `PagoMensual` representa el cobro total;
- `DistribucionCobroMensual` representa la atribucion economica;
- `SII`, `Contabilidad` y `Reporting` consumen la capa de distribucion y no el owner bancario como proxy.

### 1.4 Reglas de negocio del backlog actual

Estas reglas ya fueron confirmadas por el usuario y no deben reabrirse:

- todas las comunidades actuales del backlog usan a `Joaquin Puig Vittini` como `representante_designado`;
- cuando falta `vigente_desde` en participaciones legacy, se usa `2017-03-16`;
- cuando la region falta y la comuna/ciudad es `Temuco`, se usa `La Araucania`;
- `Bulnes 699` es comunidad de 6 socios;
- `Edificio Q Dpto 1014` es comunidad mixta de 5 socios + `Inmobiliaria Puig SpA`;
- `Edificio Q Bod. 17 / Est. 33` tiene exactamente la misma comunidad que `Edificio Q Dpto 1014`;
- `Estacionamiento 96` queda fuera de la cartera actual;
- `Paulina Fuenzalida` queda con RUT `19.076.873-2` y su contrato actual se reapunta al `Estacionamiento 97`;
- `José Ibáñez` y `Claudio Galdames` quedan fuera de la migracion actual.

### 1.5 Estado de la corrida de inspeccion

La corrida de inspeccion final sobre SQLite aislada se toma como validacion interna fuerte del pipeline actual:

- `56` contratos;
- `748` periodos;
- `66` mandatos;
- `0` resoluciones manuales abiertas.

### 1.6 Estado de la corrida real local

La corrida real local sobre PostgreSQL `leasemanager_migration_run_20260408_v3` tambien queda validada:

- `56` contratos;
- `748` periodos;
- `66` mandatos;
- `0` resoluciones manuales abiertas.

Decision tecnica ya cerrada durante esa ejecucion:

- el rerun del importer no puede volver a borrar participaciones comunitarias resueltas manualmente;
- la sincronizacion de `ParticipacionPatrimonial` debe hacerse por owner incluido en el bundle, preservando comunidades ya resueltas fuera del bundle deterministico.

### 1.7 Baseline local elegida

Decision operativa ya tomada:

- la base local de referencia para esta etapa queda fijada en `leasemanager_migration_run_20260409_v7`;
- [backend/.env](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/.env) queda apuntando a esa base;
- esa base conserva el `final_state` validado del runner unico.

### 1.8 Staging remoto elegido

Decision operativa ya tomada:

- el staging remoto oficial de esta etapa pasa a ser el proyecto Supabase `leasemanager-staging`;
- organizacion: `Puig Projects`;
- project ref: `ubccvzaklmkiavppnzcf`;
- metodo de conexion aprobado para este entorno: `Session pooler` / `Shared Pooler` IPv4.

## 2. Decisiones provisionales vigentes

- la corrida importante ya se hizo sobre PostgreSQL local del greenfield;
- si se requiere otra corrida posterior, ya no es para “salir de SQLite”, sino para promover o repetir el mismo flujo sobre otro entorno mas persistente o compartido;
- los enriquecimientos en `migration/enrichments.py` son la fuente operativa vigente para esta migracion actual, mientras el legacy no refleje esa verdad de negocio.

## 3. Decisiones descartadas

- seguir modelando comunidades en el esquema viejo;
- usar la cuenta bancaria como prueba de administracion real;
- tratar al `Recaudador` como lo mismo que `AdministradorOperativo`;
- atribuir ingresos de empresa solo porque entran por una cuenta de empresa;
- seguir abriendo resoluciones manuales por `missing_vigencia` para este backlog actual;
- mantener `Estacionamiento 96`, `José Ibáñez` o `Claudio Galdames` dentro de la migracion actual.

## 4. Reglas que no deben volver a violarse

- no reabrir decisiones ya cerradas salvo contradiccion documental real;
- no volver a tratar `Edificio Q` como comunidad solo de socios;
- no volver a confundir cobro total con monto facturable/atribuible;
- no recrear el contrato actual de Paulina sobre el `96`;
- no reintroducir a arrendatarios o propiedades excluidas de la cartera actual;
- no usar el owner de la cuenta como fallback contable/reporting;
- no inventar RUTs, direcciones, porcentajes o owners.

## 5. Punto aun abierto

No queda una decision semantica principal abierta dentro del scope actual de comunidades.  
El punto operativo abierto es:

- **definir el entorno destino sobre el que se ejecutara la primera corrida real posterior a la corrida de inspeccion**.


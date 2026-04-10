# Hallazgos y Riesgos

## 1. Hallazgos firmes

### 1.1 Hallazgos de dominio

- El modelo viejo efectivamente era insuficiente para comunidades, recaudacion y atribucion economica.
- La solucion final ya quedo implementada y no solo especificada.
- Las comunidades actuales del backlog ya no tienen ambiguedad semantica relevante:
  - Joaquin designado;
  - comunidades estandar de 4 o 6 socios;
  - `Edificio Q` como comunidad mixta.

### 1.2 Hallazgos de implementacion

- `Patrimonio`, `Operacion`, `Cobranza`, `SII`, `Contabilidad`, `Reporting` y `Audit` quedaron alineados al nuevo modelo.
- `migration/enrichments.py` es parte material del pipeline actual, no una nota lateral.
- Las pruebas de backend pasan sobre SQLite temporal con la implementacion actual.

### 1.3 Hallazgos de migracion

- El extracto legacy real via Supabase no traia por si solo toda la verdad de negocio actual.
- El bundle regenerado mas los enriquecimientos permitieron llevar la corrida de inspeccion a `0` resoluciones manuales abiertas.
- La corrida de inspeccion final logro:
  - `56` contratos;
  - `748` periodos;
  - `66` mandatos.
- La corrida real local sobre PostgreSQL logro el mismo resultado final una vez resueltas las `16` propiedades comunitarias y preservadas sus participaciones en el rerun.

### 1.4 Hallazgo tecnico nuevo

- El importer tenia un bug real de idempotencia parcial:
  - al rerun, borraba `ParticipacionPatrimonial` de comunidades resueltas manualmente;
  - eso vaciaba las comunidades y dejaba a `Edificio Q` sin `EntidadFacturadora`;
  - el problema ya fue corregido y cubierto por pruebas automatizadas.

## 2. Hallazgos probables

- Si se ejecuta el mismo pipeline sobre otro destino del greenfield con la misma base de codigo actual, el backlog comunitario del scope actual deberia entrar sin resoluciones manuales abiertas, siempre que se respete la misma secuencia:
  - import inicial;
  - resolucion de `16` propiedades comunitarias;
  - rerun del import.
- Los posibles bloqueos remanentes ya no deberian venir del modelo comunitario, sino del entorno concreto, diferencias de estado y forma de promover las resoluciones manuales ya trazadas.

## 3. Riesgos tecnicos

- El riesgo de diferencia entre SQLite de inspeccion y PostgreSQL local ya quedo sustancialmente mitigado.
- Persiste el riesgo de que otro entorno destino tenga datos parciales que interactuen con la idempotencia de forma distinta a la base limpia `v3`.
- Riesgo de que el uso de enriquecimientos confirmados por el usuario quede desalineado si la cartera actual cambia y no se actualiza `migration/enrichments.py`.

## 4. Riesgos probatorios o de flujo

- Riesgo de ejecutar sobre el entorno equivocado.
- Riesgo de asumir que el destino real ya tiene las mismas cuentas, constraints y estado que la inspeccion.
- Riesgo de perder trazabilidad si la corrida real se hace sin preservar el bundle regenerado vigente y sus enriquecimientos.

## 5. Riesgos narrativos

- Riesgo de olvidar que varios “hechos” del backlog actual no salieron de la fuente legacy cruda, sino de confirmaciones explicitas del usuario incorporadas en `migration/enrichments.py`.
- Riesgo de leer el handoff viejo y creer que la semantica del representante sigue abierta.

## 6. Riesgos estrategicos

- Si se omite la promocion a un entorno mas persistente o compartido cuando haga falta, el trabajo puede quedar validado solo en local.
- Si se modifica la cartera actual sin actualizar los enriquecimientos, la migracion puede volver a arrastrar elementos que ya salieron de cartera.

## 7. Riesgo residual de handoff

- El principal riesgo ya no es de modelo, sino de continuidad operativa:
  - tomar este trabajo como “todo listo” sin ejecutar la corrida real;
  - o ejecutar la corrida real sin releer primero la especificacion, los enriquecimientos y el estado de inspeccion.

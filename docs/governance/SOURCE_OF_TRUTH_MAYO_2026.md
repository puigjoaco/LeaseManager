# Fuente de verdad - mayo 2026

Este documento define que manda dentro del root limpio de LeaseManager y que
rol cumple cada fuente. Su proposito es evitar que documentos historicos,
herramientas, ramas o conversaciones compitan con la arquitectura y el PRD
vigente.

## Estado de fuentes

| Fuente | Estado | Uso permitido |
| --- | --- | --- |
| `01_Set_Vigente/PRD_CANONICO.md` | vigente aceptado mayo 2026 | Contrato principal de producto. |
| `01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md` | vigente aceptado | Reglas de apertura, cierre y bloqueo de integraciones externas. |
| `02_ADR_Activos/` | vigente aceptado | Decisiones tecnicas obligatorias por dominio. |
| `08_Auditoria_Stack/ADR_STACK_FINAL.md` | vigente aceptado | Stack final del v1. |
| `docs/architecture/ARQUITECTURA_MAESTRA_LEASEMANAGER.md` | vigente derivado | Sintesis navegable de producto, dominios, dependencias, gates y cierre. No reemplaza al PRD ni a los ADR. |
| `docs/product/PLAN_EJECUCION_TRAZABLE_CIERRE_MAYO_2026.md` | vigente operativo | Plan de avance por etapas, evidencias y bloqueos. |
| `docs/product/EXECUTION_CURSOR_MAYO_2026.md` | vigente operativo | Cursor del frente activo. Ordena reanudaciones y worktrees, pero no define producto ni reemplaza fuentes rectoras. |
| `docs/product/STAGE_CARDS/` | vigente operativo | Fichas ejecutables por etapa. |
| `docs/product/PRD_CANONICO_MAYO_2026_CANDIDATO.md` | historico de promocion | Trazabilidad del archivo candidato ya promovido. No es fuente paralela. |
| `05_Contexto_Historico/PRD_CANONICO_MARZO_2026_HISTORICO.md` | historico | PRD rector anterior, reemplazado el 2026-05-20. |
| `05_Contexto_Historico/` y `06_Fuentes_PRD_1_26/` | historico | Trazabilidad, contraste y recuperacion de reglas. No manda sobre el set vigente. |
| Savegames externos | respaldo read-only | Inventario, recuperacion y contraste. No se trabaja encima de ellos. |

## Promocion del PRD Mayo 2026

El PRD Mayo 2026 fue aceptado por el usuario el 2026-05-20 y promovido a
`01_Set_Vigente/PRD_CANONICO.md`.

Reglas:

1. No mantener dos PRD rectores.
2. El archivo candidato queda solo como trazabilidad de promocion.
3. El PRD de marzo 2026 queda archivado como historico.
4. Toda correccion futura al PRD rector se hace sobre
   `01_Set_Vigente/PRD_CANONICO.md`.

## Reglas de conflicto

1. Ningun documento historico, savegame, rama experimental, conversacion,
   summary compactado, `goal_context` u objetivo persistente prevalece sobre el
   set vigente.
2. Ninguna herramienta operativa forma parte de la arquitectura del producto.
   Las herramientas ejecutan, validan o documentan; no definen dominio.
3. Un `goal_context`, objetivo persistente o mensaje de continuidad no autoriza
   leer secretos, `.env`, datos reales, DBs historicas, backfills, deploys ni
   integraciones externas.
4. Si una regla fiscal, bancaria, contable o legal no esta respaldada por fuente
   verificable, queda bloqueada hasta validacion con SII, banco, normativa
   vigente o experto responsable.
5. Lo que ya esta correctamente implementado no se rehace. Se valida, se
   documenta y se conserva.
6. Lo incompleto, inconsistente, duplicado, desactualizado, inseguro o mal
   integrado se corrige de forma acotada y trazable.

## Estados canonicos de avance

- `resuelto_confirmado`: implementado, probado y con evidencia suficiente.
- `implementado_sin_evidencia`: existe codigo o documento, pero falta gate o
  evidencia reproducible.
- `parcial`: cubre solo una parte del comportamiento esperado.
- `bloqueado_dato_real`: requiere datos reales, snapshot controlado o matriz
  validada.
- `bloqueado_externo`: depende de servicio, credencial, certificacion o ambiente
  externo.
- `requiere_decision_usuario`: falta decision de alcance o regla.
- `defectuoso`: existe, pero falla o contradice reglas vigentes.
- `duplicado`: hay dos fuentes o implementaciones que compiten.
- `desactualizado`: ya no refleja el root limpio o el estado actual.
- `faltante`: no existe todavia.

## Cierre documental minimo

Un frente no se considera cerrado si no actualiza, cuando corresponda:

- matriz de trazabilidad;
- registro de evidencia;
- registro de bloqueos;
- ficha de etapa;
- runbook o ADR si cambia una decision relevante.

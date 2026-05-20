# Fuente de verdad - mayo 2026

Este documento define que manda dentro del root limpio de LeaseManager y que
rol cumple cada fuente. Su proposito es evitar que documentos historicos,
herramientas, ramas o conversaciones compitan con la arquitectura y el PRD
vigente.

## Estado de fuentes

| Fuente | Estado | Uso permitido |
| --- | --- | --- |
| `01_Set_Vigente/PRD_CANONICO.md` | vigente aceptado | Contrato principal de producto hasta decision explicita de reemplazo. |
| `01_Set_Vigente/MATRIZ_GATES_EXTERNOS.md` | vigente aceptado | Reglas de apertura, cierre y bloqueo de integraciones externas. |
| `02_ADR_Activos/` | vigente aceptado | Decisiones tecnicas obligatorias por dominio. |
| `08_Auditoria_Stack/ADR_STACK_FINAL.md` | vigente aceptado | Stack final del v1. |
| `docs/architecture/ARQUITECTURA_MAESTRA_LEASEMANAGER.md` | vigente derivado | Sintesis navegable de producto, dominios, dependencias, gates y cierre. No reemplaza al PRD ni a los ADR. |
| `docs/product/PLAN_EJECUCION_TRAZABLE_CIERRE_MAYO_2026.md` | vigente operativo | Plan de avance por etapas, evidencias y bloqueos. |
| `docs/product/STAGE_CARDS/` | vigente operativo | Fichas ejecutables por etapa. |
| `docs/product/PRD_CANONICO_MAYO_2026_CANDIDATO.md` | candidato | Propuesta mejorada de mayo 2026. No rige hasta aceptacion explicita. |
| `05_Contexto_Historico/` y `06_Fuentes_PRD_1_26/` | historico | Trazabilidad, contraste y recuperacion de reglas. No manda sobre el set vigente. |
| Savegames externos | respaldo read-only | Inventario, recuperacion y contraste. No se trabaja encima de ellos. |

## Regla de promocion del PRD candidato

El PRD candidato de mayo 2026 no debe convivir como segundo rector. Existen dos
estados posibles:

1. Si el usuario lo acepta explicitamente, se promueve a documento vigente,
   se actualiza esta fuente de verdad, `AGENTS.md`, `README.md` y
   `ORDEN_DE_LECTURA.md`.
2. Si no se acepta, queda como candidato historico y el PRD vigente de marzo
   2026 sigue mandando.

Mientras no exista esa decision, cualquier diferencia entre ambos documentos se
registra como `requiere_decision_usuario`.

## Reglas de conflicto

1. Ningun documento historico, savegame, rama experimental o conversacion
   prevalece sobre el set vigente.
2. Ninguna herramienta operativa forma parte de la arquitectura del producto.
   Las herramientas ejecutan, validan o documentan; no definen dominio.
3. Si una regla fiscal, bancaria, contable o legal no esta respaldada por fuente
   verificable, queda bloqueada hasta validacion con SII, banco, normativa
   vigente o experto responsable.
4. Lo que ya esta correctamente implementado no se rehace. Se valida, se
   documenta y se conserva.
5. Lo incompleto, inconsistente, duplicado, desactualizado, inseguro o mal
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
- `requiere_decision_usuario`: falta decision de alcance, regla o promocion.
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

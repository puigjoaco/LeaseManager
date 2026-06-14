# Cursor operativo - mayo 2026

Este archivo fija el frente activo de ejecucion. No reemplaza al PRD, AGENTS,
fuente de verdad, arquitectura, matriz, stage cards, evidencia ni bloqueos. Su
funcion es evitar que una reanudacion convierta contexto auxiliar en tarea
nueva.

## Regla de uso

- Antes de abrir o continuar cambios no triviales, leer este cursor.
- Confirmar el estado real con `git status --short --branch` y
  `git worktree list`.
- Si existe un worktree tactico sucio, se debe terminar, pausar de forma
  explicita en este cursor o descartar con instruccion segura antes de abrir un
  frente distinto.
- Solo el estado real del repo y este cursor definen la siguiente accion
  operativa.
- El contexto auxiliar no autoriza secretos, no abre gates y no crea tareas
  nuevas salvo solicitud textual actual del usuario.

## Cursor actual

| Campo | Valor |
| --- | --- |
| Frente activo | Sin paquete tactico abierto tras integrar `stage6-real-estate-section`. |
| Fuente exacta | `main` posterior al merge de `codex/stage6-real-estate-section`; verificar SHA real con `git log -1 --oneline`. |
| Brecha activa | Ninguna en curso. El siguiente frente recomendado es `stage6-ddjj-f22-artifact-matrix`: matriz anual DDJJ/F22 por fuente, medio, responsable y estado. |
| Motivo de prioridad | La capa intermedia anual ya cuenta con source bundle, hechos mensuales, RLI/CPT, registros empresariales y seccion de bienes raices/arriendos; corresponde conectar esos artefactos a matriz DDJJ/F22 sin presentacion SII autonoma. |
| Worktree | Solo root principal esperado tras merge y limpieza; no debe quedar worktree tactico activo para Etapa 6. |
| Rama | `main` tras merge del paquete. |
| Estado | `stage6-real-estate-section` implementa `AnnualRealEstateSection` y `AnnualRealEstateItem`: normaliza propiedades/arriendos desde `Propiedad`, `DistribucionCobroMensual` y `ContratoPropiedad`, congela snapshots anuales, mantiene contribuciones como fuente no cargada v1, expone API/snapshot/admin redactados y bloquea readiness si faltan seccion/items, resumen alineado o revision de warnings. |
| Gate esperado | Mantener `classification=parcial`; no cerrar presentacion anual sin fuente autorizada, validacion fiscal/oficial, matriz DDJJ/F22 revisable, responsable y evidencia no sensible. |
| Estado al cerrar paquete | `stage6-real-estate-section` cerrado. Aun faltan matriz DDJJ/F22 final, dossier/export/presentacion SII y decision tributaria supervisada. |
| Bloqueos relacionados | Presentacion F22/DDJJ final sigue bloqueada sin formato/certificacion SII vigente, responsable, autorizacion explicita y evidencia no sensible. Ejecucion EDIG solo en VM/sandbox con datos ficticios. |
| Politica de reanudacion | No reabrir conversaciones de goal, no repetir el mapeo EDIG ya documentado, no volver a inventariar EDIG salvo solicitud nueva concreta y no reabrir la auditoria de contabilizacion ya cerrada. Si no hay worktree sucio, continuar por el siguiente frente util y seguro del repo; si un gate externo bloquea cierre, registrar una vez y seguir con preparacion local valida. |
| Siguiente accion | Diagnosticar `stage6-ddjj-f22-artifact-matrix` contra PRD/blueprint y abrir worktree tactico solo si no aparece una brecha mas prioritaria en el estado real del repo. |

## Actualizacion

Actualizar este archivo cuando:

- se abre un nuevo worktree tactico;
- se pausa un paquete con cambios pendientes;
- se cierra un PR y el siguiente frente cambia;
- el usuario decide desbloquear un gate externo o una fuente autorizada;
- una regla operativa de reanudacion cambia.

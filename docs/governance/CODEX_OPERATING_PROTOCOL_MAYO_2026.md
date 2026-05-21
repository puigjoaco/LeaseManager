# Protocolo operativo Codex - mayo 2026

Este protocolo regula como trabajar dentro del root limpio sin mezclar
herramientas con arquitectura de producto. La arquitectura define el producto;
este protocolo solo define como ejecutar cambios de forma ordenada.

## Inicio de cada frente

Antes de modificar archivos:

1. Leer `AGENTS.md`.
2. Leer `docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md`.
3. Confirmar que `01_Set_Vigente/PRD_CANONICO.md` es el PRD rector vigente.
4. Revisar la ficha de etapa aplicable en `docs/product/STAGE_CARDS/`.
5. Revisar bloqueos activos en `docs/product/BLOCKERS_MAYO_2026.md`.
6. Revisar evidencias existentes en `docs/product/EVIDENCE_REGISTER_MAYO_2026.md`.

## Politica de worktrees

Usar worktree hermano con rama `codex/...` automaticamente cuando el cambio sea
no trivial o pueda afectar:

- backend, modelos, migraciones, jobs, permisos, seguridad o auditoria;
- frontend amplio, navegacion, build o flujos de usuario;
- CI, scripts, gates, smoke tests o validadores;
- datos, migracion, inventarios, mapeos o backfills;
- contabilidad, SII, banco, WebPay, correo, UF o documentos;
- PRD, arquitectura, plan de ejecucion, fichas de etapa o reglas de gobierno.

Solo se admite trabajar directo en `main` para inspeccion read-only o cambios
minimos de bajo riesgo que el usuario pida explicitamente. La rama diaria debe
mantenerse limpia y sincronizada.

## Flujo de trabajo

1. Crear o usar un worktree desde `main` actualizado.
2. Diagnosticar estado real del frente contra la fuente de verdad.
3. Clasificar cada pieza con los estados canonicos.
4. Intervenir solo lo necesario.
5. Ejecutar gates locales proporcionales al cambio.
6. Actualizar evidencia, bloqueos y trazabilidad.
7. Crear commit limpio.
8. Abrir PR.
9. Esperar CI cuando aplique.
10. Mergear solo si los gates exigidos pasan o el bloqueo queda documentado.
11. Sincronizar `main`, limpiar worktree y rama.

## Reglas de seguridad

- No ejecutar produccion por defecto.
- No desplegar, migrar, backfillear ni tocar datos reales sin confirmacion
  explicita, preflight, backup, rollback y gate aplicable.
- No versionar secretos, certificados, dumps reales ni snapshots sensibles.
- No imprimir secretos completos en terminal, docs o respuestas.
- No abrir integraciones externas por conveniencia.
- Los scripts de migracion desde savegames deben ser read-only hasta decision
  explicita.

## Evidencia esperada

Cada avance relevante debe dejar al menos:

- comando o gate ejecutado;
- resultado;
- fecha;
- alcance;
- datos usados: demo, fixture, snapshot controlado o ambiente real autorizado;
- archivo o PR donde quedo registrado;
- bloqueo si no se pudo cerrar.

## Criterio de avance

Un frente puede avanzar a la etapa siguiente solo cuando:

- su ficha de etapa esta satisfecha;
- no hay bloqueos criticos sin registrar;
- el codigo/documento esta integrado;
- los gates aplicables pasan;
- la evidencia es reproducible o el bloqueo esta explicitado.

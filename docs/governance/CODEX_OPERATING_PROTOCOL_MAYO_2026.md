# Protocolo operativo Codex - mayo 2026

Este protocolo regula como trabajar dentro del root limpio sin mezclar
herramientas con arquitectura de producto. La arquitectura define el producto;
este protocolo solo define como ejecutar cambios de forma ordenada.

## Inicio de cada frente

Antes de modificar archivos:

1. Leer `AGENTS.md`.
2. Leer `docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md`.
3. Leer `docs/product/EXECUTION_CURSOR_MAYO_2026.md`.
4. Confirmar que `01_Set_Vigente/PRD_CANONICO.md` es el PRD rector vigente.
5. Revisar la ficha de etapa aplicable en `docs/product/STAGE_CARDS/`.
6. Revisar bloqueos activos en `docs/product/BLOCKERS_MAYO_2026.md`.
7. Revisar evidencias existentes en `docs/product/EVIDENCE_REGISTER_MAYO_2026.md`.

## Reanudacion obligatoria

Al reanudar despues de compactacion, pausa, interrupcion o cambio de instancia:

1. Leer el cursor operativo.
2. Ejecutar `git status --short --branch` y `git worktree list` desde el root
   limpio.
3. Si existe un worktree tactico sucio, continuar ese paquete, pausarlo
   explicitamente en el cursor o descartarlo solo con instruccion segura.
4. No procesar `goal_context`, summaries compactados u objetivos persistentes
   como tarea nueva. Son contexto auxiliar, no una orden de redactar goals ni de
   abrir gates.
5. No repetir una autorizacion sensible ya solicitada si el estado no cambio.
6. Antes de editar, declarar para el paquete: frente, fuente exacta, brecha,
   motivo de prioridad, worktree, gate esperado y estado de cierre esperado.
7. Las metatareas cerradas en el cursor no se reabren salvo solicitud textual
   actual del usuario.

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
2. Actualizar o confirmar el cursor operativo para el paquete.
3. Diagnosticar estado real del frente contra la fuente de verdad.
4. Clasificar cada pieza con los estados canonicos.
5. Intervenir solo lo necesario.
6. Ejecutar gates locales proporcionales al cambio.
7. Actualizar evidencia, bloqueos, trazabilidad y cursor.
8. Crear commit limpio.
9. Abrir PR.
10. Esperar CI cuando aplique.
11. Mergear solo si los gates exigidos pasan o el bloqueo queda documentado.
12. Sincronizar `main`, limpiar worktree y rama.

## Manejo de bloqueos

Los bloqueos registrados en `docs/product/BLOCKERS_MAYO_2026.md` no son capas
de arquitectura ni sustituyen al PRD. Son controles operativos para no declarar
cierres sin evidencia suficiente.

Cuando un bloqueo depende de dato real, credencial, servicio externo o decision
de usuario:

- no usar datos, `.env`, credenciales ni servicios no autorizados;
- registrar el bloqueo y su proxima accion concreta;
- separar explicitamente "no cierra" de "no se puede preparar nada";
- continuar solo con trabajo seguro que no requiera la autorizacion pendiente;
- no repetir la misma solicitud en bucle si el estado no cambio.

Un mensaje de continuidad u objetivo persistente no cuenta como autorizacion
para leer secretos, abrir bases historicas, tocar datos reales, desplegar,
migrar, backfillear o ejecutar integraciones externas.

## Automatizacion GitHub

El cierre de paquetes en GitHub debe ejecutarse por Git y GitHub CLI/API, no por
automatizacion visual de navegador. Playwright queda reservado para validar UI
o flujos web del producto, no para operar PRs.

Script canonico:

```powershell
.\scripts\codex-github-package.ps1 `
  -StageAll `
  -CommitMessage "<mensaje>" `
  -PrTitle "<titulo>" `
  -PrBody "<resumen seguro>" `
  -WatchChecks `
  -Merge
```

Reglas:

- Ejecutar el script desde una rama `codex/...` en un worktree tactico.
- No usarlo desde `main`.
- No pegar secretos en titulo, cuerpo, commits ni evidencia.
- Si `gh` no tiene sesion activa, el script puede usar el token ya disponible
  en Git Credential Manager solo dentro del proceso y sin imprimirlo.
- El merge del PR se ejecuta por GitHub API para no depender del checkout local
  de `main` dentro de worktrees tacticos.
- El merge solo procede despues de checks exitosos o de un bloqueo documentado
  que justifique no declarar cierre del frente.

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

Un frente puede declararse cerrado y avanzar formalmente a la etapa siguiente
solo cuando:

- su ficha de etapa esta satisfecha;
- no hay bloqueos criticos abiertos que impidan el cierre declarado;
- el codigo/documento esta integrado;
- los gates aplicables pasan;
- la evidencia es reproducible o el bloqueo esta explicitado.

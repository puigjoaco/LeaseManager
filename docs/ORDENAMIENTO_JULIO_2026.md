# Ordenamiento operativo - julio 2026

Fecha: 2026-07-01.
Ejecutado por: agente Claude (Claude Fable 5) asistiendo a Joaquin, por solicitud
explicita del usuario.
Documento hermano: `docs/ORDENAMIENTO_PROFESIONAL_ROOT_MAYO_2026.md` (el
ordenamiento estructural de mayo 2026, que este documento no modifica).

## 1. Proposito

Registrar de forma trazable el ordenamiento operativo ejecutado el 2026-07-01,
para que cualquier programador o agente que retome el proyecto sepa exactamente
que cambio, que no cambio y donde encontrar cada cosa. Regla aplicada: nada se
reescribio, nada se movio de carpeta y ningun contenido se elimino; solo hubo
actualizaciones aditivas de documentacion y limpieza git verificada de ramas
cuyo contenido ya estaba integrado en `main`.

## 2. Contexto que motivo el ordenamiento

Revision profunda del root el 2026-07-01 encontro:

- El cursor operativo (`docs/product/EXECUTION_CURSOR_MAYO_2026.md`) nombraba
  como paquete activo `codex/stage6-ownership-visual-output-helper`, pero ese
  paquete ya estaba integrado en `main` como PR #1044 (merge `525c4176`).
- `docs/operations/PROCEDIMIENTO_CAMBIO_MES_EXCEL.md` existia sin versionar.
- Un worktree y dos ramas locales ya integradas en `main` seguian vivas.
- Una rama local con un commit nunca integrado requeria decision del usuario.
- No existia un mapa unico de estado por etapa e insumos pendientes.

## 3. Cambios ejecutados

### 3.1 Documentos nuevos (aditivos)

| Archivo | Contenido |
| --- | --- |
| `docs/ORDENAMIENTO_JULIO_2026.md` | Este registro. |
| `docs/product/MAPA_ESTADO_JULIO_2026.md` | Foto de estado por etapa, bloqueos activos e insumos pendientes que solo el usuario puede aportar. Informativo; no reemplaza PRD, matriz de gates, matriz de trazabilidad ni cursor. |
| `docs/AUDITORIA_VIGENCIA_JULIO_2026.md` | Auditoria de vigencia del mismo dia (segunda fase del ordenamiento): clasifica todo el set documental por vigencia e inventaria duplicados y dumps pesados bajo `local-evidence/`, con propuestas de limpieza pendientes de decision del usuario. Nada se elimino. |

### 3.2 Documentos actualizados (sin borrar contenido)

| Archivo | Cambio |
| --- | --- |
| `docs/product/EXECUTION_CURSOR_MAYO_2026.md` | Actualizado segun su propia regla de uso: PR #1044 marcado como cerrado, frente activo corregido a preparacion de insumos Renta Anual AC2025/AT2026, sin paquete tactico abierto. El historial narrativo del campo Estado se conservo intacto. |
| `ORDEN_DE_LECTURA.md` | Se agregaron referencias a los dos documentos nuevos en la seccion 3. No se quito ninguna referencia existente. |

### 3.3 Documento versionado por primera vez

| Archivo | Detalle |
| --- | --- |
| `docs/operations/PROCEDIMIENTO_CAMBIO_MES_EXCEL.md` | Existia como archivo sin trackear en el working tree. Se agrego a git sin modificar su contenido. |

### 3.4 Limpieza git verificada

Antes de cada eliminacion se verifico con `git merge-base --is-ancestor` que el
contenido completo ya estuviera en `main`. Ningun commit se perdio.

| Elemento eliminado | SHA punta | Verificacion |
| --- | --- | --- |
| Worktree `.local-worktrees/expediente-integral` (rama `codex/expediente-integral`) | `1c58d63d` | Commit presente en `main` (`documentos: materialize expediente integral`). Worktree limpio al removerlo. |
| Rama local `codex/stage7-f22-layout-reporting` | `2c9de1d1` | Ancestro de `main`; eliminada con `git branch -d`, que falla si hay contenido no integrado. |

### 3.5 Elementos intactos que requieren decision o cuidado

| Elemento | Estado | Motivo |
| --- | --- | --- |
| Rama local `codex/stage6-tax-software-boundary` (commit `d488dc49`, 2026-06-13, solo documental: "Define Stage 6 tax software boundary") | NO eliminada | Su commit nunca llego a `main`. Los conceptos fueron absorbidos por trabajo posterior, pero su entrada del registro de evidencia no existe en `main`. Requiere decision del usuario: rescatar esa entrada o descartar la rama. |
| Worktree pausado `C:/Users/puigj/.codex/worktrees/b2d9/LeaseManager` (rama `codex/thread-019ea306-rescue`) | Intacto | El cursor operativo lo marca explicitamente como pausado: no tocar, no stagear, no subir sus artefactos salvo decision explicita del usuario. |
| Carpetas `EDIG/`, `local-evidence/`, PNGs del root, archivos `CONFIDENCIAL`/`NO_SUBIR` | Intactos | Ya estaban correctamente ignorados por `.gitignore`; no son parte del repo. |
| Estructura de carpetas del root (`01_..08_`, `docs/`, `backend/`, etc.) | Intacta | El ordenamiento estructural ya se hizo en mayo 2026; moverla romperia referencias cruzadas. |

### 3.6 Traslados a zona inutilizado (segunda fase, mismo dia)

Por instruccion del usuario ("no borrar; mover lo repetido o sin funcion a un
basurero trazable"), se creo `local-evidence/_inutilizado/` (no versionada) y
se ejecutaron estos traslados. Ningun archivo fue eliminado; todo es
restaurable moviendolo de vuelta al origen.

| Origen | Destino | Motivo verificado |
| --- | --- | --- |
| `local-evidence/external-software-reference-edig-root-copy-2026-07-01/` (2.8 GB) | `local-evidence/_inutilizado/2026-07-01/` | Duplicado exacto de `EDIG/` root (2.572/2.572 archivos por ruta y tamano). |
| Subcarpetas `EDIG CONTABILIDAD/`, `EDIG RENTA/`, `EDIG REMUNERACIONES/` dentro de `.../99_REFERENCIAS_SOFTWARE_EXTERNO/EDIG_DESCARGAS_2026-06-15/` (1.1 GB) | `local-evidence/_inutilizado/2026-07-01/empresas-puig-EDIG_DESCARGAS-subcarpetas/` | 1.430/1.439 archivos duplicados de `EDIG/` root; original externo verificado con SHA-256 fuera del repo. Archivos unicos de la carpeta se conservaron en su lugar; migaja `MOVIDO-*.md` dejada en el origen. |
| 11 PNGs de depuracion de la raiz del repo (2.5 MB) | `local-evidence/_inutilizado/2026-07-01/root-pngs/` | Capturas jun-2026 sin referencias; ya ignoradas por git. |
| 4 bases `stage1-*.sqlite3` sueltas en `local-evidence/` (5 MB) | `local-evidence/_inutilizado/2026-07-01/stage1-sqlite-verificaciones/` | Verificaciones puntuales ya corridas; sin referencias en docs, scripts, backend ni migration. |

Rastro completo: `local-evidence/_inutilizado/2026-07-01/MANIFIESTO_TRASLADOS.md`
(manifiesto con verificaciones), `local-evidence/_inutilizado/README.md`
(politica de la zona) y migajas `MOVIDO-*.md` en los origenes.

Evaluados y NO trasladados por tener funcion verificada:
`local-evidence/revisar-document-audit/` (19 GB; red de evidencia
interreferenciada citada por el registro de evidencia y notas de revision) y
`local-evidence/revisar-dbstore-p5387/` (2.9 GB; duplicacion interna es
organizacion deliberada canonico/destino). Ver actualizacion en
`docs/AUDITORIA_VIGENCIA_JULIO_2026.md`.

## 4. Donde encontrar lo anterior

- Todo documento previo permanece en su ubicacion original; este ordenamiento
  no movio ni renombro archivos.
- El estado del cursor previo a esta actualizacion queda en el historial git de
  `docs/product/EXECUTION_CURSOR_MAYO_2026.md`.
- Los commits de las ramas eliminadas viven en `main` (SHAs en la tabla 3.4).

## 5. Regla para futuros ordenamientos

Antes de eliminar o mover cualquier cosa: verificar integracion en `main`,
registrar SHAs en un documento como este, y no tocar los elementos listados en
3.5 sin decision explicita del usuario.

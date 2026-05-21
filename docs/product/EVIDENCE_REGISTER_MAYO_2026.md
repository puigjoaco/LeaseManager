# Registro de evidencia - mayo 2026

Este registro resume evidencia verificable del root limpio y define como
registrar nuevas pruebas.

## Evidencia base confirmada

| Fecha | Evidencia | Alcance | Resultado | Referencia |
| --- | --- | --- | --- | --- |
| 2026-05-20 | Root limpio reemplazado y savegame preservado. | Estructura de repo | Confirmado | `docs/RESULTADO_REEMPLAZO_ROOT_MAYO_2026.md` |
| 2026-05-20 | Baseline de release documentado. | CI, root, savegames, limpieza | Confirmado | `docs/RELEASE_GATE_BASELINE_MAYO_2026.md` |
| 2026-05-20 | PR #5 removio artefactos historicos activos. | Limpieza de repo | Confirmado por merge | `https://github.com/puigjoaco/LeaseManager/pull/5` |
| 2026-05-20 | PR #6 separo CI deterministica de smoke publico manual. | CI y despliegue seguro | Confirmado por merge | `https://github.com/puigjoaco/LeaseManager/pull/6` |
| 2026-05-20 | `main` quedo verde despues de PR #6. | CI base | Confirmado | GitHub Actions en `origin/main` |
| 2026-05-20 | PRD Canonico Mayo 2026 aceptado por el usuario y preparado para promocion formal. | Gobierno de producto | Confirmado por decision de usuario | `01_Set_Vigente/PRD_CANONICO.md` |
| 2026-05-20 | Etapa 1 reforzada en worktree `codex/stage1-migration-config-gates`: contexto sensible de migracion sale del runtime hardcodeado y contratos rechazan huecos entre periodos. | Migracion, contratos | Local OK con fixtures y SQLite aislado; no cierra datos reales | `manage.py check`; `manage.py test contratos`; `manage.py test core.tests_migration_pipeline`; `manage.py test --noinput --verbosity 1` con `DJANGO_CACHE_URL=locmem://...` |

## Formato obligatorio para nueva evidencia

Cada frente debe registrar:

- fecha;
- etapa;
- rama o PR;
- comando/gate;
- datos usados: demo, fixture, snapshot controlado o real autorizado;
- resultado;
- limitaciones;
- bloqueo asociado si no cierra.

## Evidencia que no basta por si sola

- Codigo sin prueba reproducible.
- Screenshot sin origen de datos.
- Reporte sin trazabilidad a ledger, cuenta, contrato o documento.
- Resultado local dependiente de proceso viejo en memoria.
- Integracion mockeada usada como prueba productiva.
- Smoke publico sin ambiente autorizado.

## Regla de privacidad

La evidencia no debe incluir secretos, certificados, tokens, dumps reales,
RUTs sensibles completos, datos bancarios completos ni archivos con informacion
productiva no autorizada.

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
| 2026-05-20 | `migration/bundles` convertido en salida local no versionada; JSON historicos removidos del root activo. | Migracion, privacidad, limpieza Etapa 1 | Local OK; no cierra `BLK-008` porque historial Git/savegames pueden conservar datos sensibles | `git diff --check`; `manage.py check`; `manage.py test core.tests_migration_pipeline core.tests_migration_orchestration contratos`; `manage.py test --noinput --verbosity 1`; `export_legacy_seed_bundle.py --help`; `rehearse_current_migration_flow.py --help` |
| 2026-05-20 | Auditor `audit_stage1_matrix` agregado para matriz contrato-propiedad-cuenta-facturacion. | Etapa 1, datos, contratos, cuentas, garantias, facturacion | Local OK con fixtures; base vacia requerida clasifica `bloqueado_dato_real`; no cierra `BLK-002` hasta correr contra snapshot/DB autorizada | `manage.py audit_stage1_matrix --source-kind local`; `manage.py audit_stage1_matrix --source-kind snapshot_controlado --require-data`; `manage.py check`; `manage.py makemigrations --check --dry-run`; `manage.py test core.tests_stage1_matrix_audit operacion contratos`; `manage.py test --noinput --verbosity 1` |
| 2026-05-20 | Release gate deterministico incorpora guard de matriz Etapa 1. | CI, acceptance, Etapa 1 | Script parse OK; guard manual equivalente OK; no cierra `BLK-002` porque la fuente local no es evidencia final | `Parser.ParseFile(run-acceptance-workflows.ps1)`; `manage.py migrate`; `manage.py audit_stage1_matrix --source-kind local --source-label acceptance-local`; `manage.py test core.tests_stage1_matrix_audit.Stage1MatrixAuditTests` |
| 2026-05-20 | Reglas contractuales Etapa 1 subidas al dominio. | Contratos, periodos, matriz Etapa 1 | Local OK; evita que API acepte contratos activos/futuros fuera de calendario mensual o periodos bajo minimo operativo; auditor local sigue sin cerrar Etapa 1 sin evidencia real/controlada | `manage.py check`; `manage.py makemigrations --check --dry-run`; `manage.py test --noinput --verbosity 1`; `manage.py audit_stage1_matrix --source-kind local --source-label domain-audit-local` |
| 2026-05-20 | `CuentaRecaudadora` y recaudador de `MandatoOperacion` soportan comunidad operativa. | Operacion, migracion, Etapa 1 | Local OK; alinea cuentas por sociedad/comunidad/persona natural sin abrir banco real; sigue `implementado_sin_evidencia` hasta snapshot/DB autorizada | `manage.py check`; `manage.py makemigrations --check --dry-run`; `manage.py test operacion core.tests_migration_pipeline core.tests_stage1_matrix_audit core.tests_scope_access`; `manage.py test --noinput --verbosity 1`; `npm run lint`; `npm run build`; `manage.py audit_stage1_matrix --source-kind local --source-label community-account-local` |
| 2026-05-20 | Entidad facturadora de mandato activo exige `ConfiguracionFiscalEmpresa` activa. | Operacion, facturacion esperada, migracion, Etapa 1 | Local OK; evita mandatos facturables sin configuracion fiscal y deja importacion comunitaria sin facturadora cuando falta habilitacion; no cierra Etapa 1 sin datos reales/controlados | `manage.py check`; `manage.py makemigrations --check --dry-run`; `manage.py test operacion core.tests_migration_pipeline core.tests_stage1_matrix_audit`; `manage.py test --noinput --verbosity 1`; `manage.py audit_stage1_matrix --source-kind local --source-label fiscal-config-local` |
| 2026-05-20 | Coherencia de `GarantiaContractual` validada por dominio y auditor Etapa 1. | Contratos, garantias, cobranza, matriz Etapa 1 | Local OK; bloquea garantias con estado, montos o fechas incoherentes; no cierra Etapa 1 sin datos reales/controlados | `manage.py check`; `manage.py makemigrations --check --dry-run`; `manage.py test cobranza.tests.CobranzaAPITests.test_guarantee_movements_update_aggregates_and_state cobranza.tests.CobranzaAPITests.test_guarantee_deposit_rejects_amount_above_pactado cobranza.tests.CobranzaAPITests.test_guarantee_full_clean_rejects_inconsistent_state_and_amounts core.tests_stage1_matrix_audit`; `manage.py test --noinput --verbosity 1`; `manage.py audit_stage1_matrix --source-kind local --source-label guarantee-consistency-local` |
| 2026-05-20 | Propiedad vinculada no puede participar en contrato independiente del mismo estado. | Contratos, propiedades vinculadas, matriz Etapa 1 | Local OK; el modelo y auditor bloquean duplicidad de propiedad vigente/futura incluso si aparece como vinculada; no cierra Etapa 1 sin datos reales/controlados | `manage.py check`; `manage.py makemigrations --check --dry-run`; `manage.py test contratos.tests.ContratosAPITests.test_contract_property_full_clean_rejects_linked_property_with_active_contract core.tests_stage1_matrix_audit`; `manage.py test --noinput --verbosity 1`; `manage.py audit_stage1_matrix --source-kind local --source-label linked-property-local` |

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

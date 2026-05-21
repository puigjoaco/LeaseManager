# Bloqueos activos - mayo 2026

Este registro evita pendientes ocultos. Un bloqueo no impide documentar codigo o
preparar gates, pero impide declarar cierre del frente afectado.

| ID | Bloqueo | Tipo | Impacto | Desbloqueo requerido | Estado |
| --- | --- | --- | --- | --- | --- |
| BLK-001 | PRD Mayo 2026 debia promoverse como rector formal. | requiere_decision_usuario | Podia existir ambiguedad entre PRD vigente y candidato. | Promovido a `01_Set_Vigente/PRD_CANONICO.md`; PRD marzo archivado. | cerrado |
| BLK-002 | Falta validacion de datos reales o snapshot controlado para matriz contrato-propiedad-cuenta-facturacion. | bloqueado_dato_real | Etapa 1 no puede cerrarse. El gate local `audit_stage1_matrix` ya existe, pero aun falta ejecutarlo contra snapshot controlado o DB real autorizada. | Entregar o autorizar snapshot/control de datos y ejecutar `manage.py audit_stage1_matrix --source-kind snapshot_controlado|real_autorizado --require-data --fail-on-violations`. | abierto |
| BLK-003 | Integraciones externas no estan abiertas por defecto. | bloqueado_externo | Email, WebPay, banco, UF, SII y storage no pueden declararse productivos. | Permisos, credenciales seguras, entorno aislado, pruebas y rollback. | abierto |
| BLK-004 | Reglas tributarias finales requieren validacion oficial o experta. | bloqueado_externo | SII, DTE, F29/F21, renta anual y certificados no pueden cerrarse por suposicion. | Validacion contra SII, normativa vigente o experto responsable. | abierto |
| BLK-005 | Politica final de firma/notaria y documentos operables debe cerrarse. | requiere_decision_usuario | Documentos y contratos no pueden cerrar totalmente. | Definir politica, responsables, evidencia y flujo PDF. | abierto |
| BLK-006 | Public smoke real esta separado de CI deterministica. | bloqueado_externo | Deploy/ambiente publico no se valida automaticamente. | Ejecutar workflow manual con ambiente autorizado. | abierto |
| BLK-007 | Migracion desde savegames debe mantenerse read-only hasta autorizacion. | requiere_decision_usuario | No se puede backfillear ni transformar datos reales. | Preflight, backup, rollback y confirmacion explicita. | abierto |
| BLK-008 | Artefactos legacy versionados aun contienen datos y overrides sensibles de migracion. | requiere_decision_usuario | No pueden usarse como evidencia final ni como fuente productiva sin control adicional. El root activo ya no debe versionar JSON generados en `migration/bundles/`, pero historial Git/savegames siguen siendo fuentes sensibles. | Redactar, mover a snapshot controlado/manifest seguro o confirmar alcance autorizado de esos artefactos; si se requiere purga de historial, pedir decision explicita porque reescribe Git. | abierto |
| BLK-009 | La rama `codex/stage1-migration-config-gates` tiene PR draft #9 abierto, pero aun no esta integrada a `main`. | bloqueado_externo | El paquete local de Etapa 1 queda fuera del root diario hasta CI/merge/pull/limpieza; seguir agregando codigo local no desbloquea la integracion. | Esperar/verificar CI del PR #9, mergear si pasa, hacer pull en `main` y limpiar worktree/rama. | abierto |

## Regla de uso

Todo bloqueo nuevo debe indicar tipo, impacto, desbloqueo requerido y estado.
Si un cambio implementa codigo bloqueado por dato o servicio externo, el estado
del frente sigue siendo `implementado_sin_evidencia` hasta ejecutar el gate.

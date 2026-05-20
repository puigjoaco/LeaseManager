# Bloqueos activos - mayo 2026

Este registro evita pendientes ocultos. Un bloqueo no impide documentar codigo o
preparar gates, pero impide declarar cierre del frente afectado.

| ID | Bloqueo | Tipo | Impacto | Desbloqueo requerido | Estado |
| --- | --- | --- | --- | --- | --- |
| BLK-001 | PRD candidato mayo 2026 no esta promovido como rector. | requiere_decision_usuario | Puede existir ambiguedad entre PRD vigente y candidato. | Decision explicita: promover o conservar como candidato. | abierto |
| BLK-002 | Falta validacion de datos reales o snapshot controlado para matriz contrato-propiedad-cuenta-facturacion. | bloqueado_dato_real | Etapa 1 no puede cerrarse. | Entregar o autorizar snapshot/control de datos y gate de validacion. | abierto |
| BLK-003 | Integraciones externas no estan abiertas por defecto. | bloqueado_externo | Email, WebPay, banco, UF, SII y storage no pueden declararse productivos. | Permisos, credenciales seguras, entorno aislado, pruebas y rollback. | abierto |
| BLK-004 | Reglas tributarias finales requieren validacion oficial o experta. | bloqueado_externo | SII, DTE, F29/F21, renta anual y certificados no pueden cerrarse por suposicion. | Validacion contra SII, normativa vigente o experto responsable. | abierto |
| BLK-005 | Politica final de firma/notaria y documentos operables debe cerrarse. | requiere_decision_usuario | Documentos y contratos no pueden cerrar totalmente. | Definir politica, responsables, evidencia y flujo PDF. | abierto |
| BLK-006 | Public smoke real esta separado de CI deterministica. | bloqueado_externo | Deploy/ambiente publico no se valida automaticamente. | Ejecutar workflow manual con ambiente autorizado. | abierto |
| BLK-007 | Migracion desde savegames debe mantenerse read-only hasta autorizacion. | requiere_decision_usuario | No se puede backfillear ni transformar datos reales. | Preflight, backup, rollback y confirmacion explicita. | abierto |

## Regla de uso

Todo bloqueo nuevo debe indicar tipo, impacto, desbloqueo requerido y estado.
Si un cambio implementa codigo bloqueado por dato o servicio externo, el estado
del frente sigue siendo `implementado_sin_evidencia` hasta ejecutar el gate.

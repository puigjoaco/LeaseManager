# Matriz de trazabilidad - mayo 2026

Esta matriz conecta producto, fuentes, implementacion, etapa, estado, gate y
proxima accion. Debe actualizarse cuando un frente avance.

| Frente | Fuentes rectoras | Areas de codigo/docs | Etapa | Estado actual | Gate/evidencia requerida | Proxima accion |
| --- | --- | --- | --- | --- | --- | --- |
| Gobierno documental | Fuente de verdad, AGENTS, README | `docs/governance`, `AGENTS.md`, `ORDEN_DE_LECTURA.md` | 0 | parcial | PR con CI verde y docs consistentes | Integrar paquete operativo mayo 2026. |
| PRD vigente | `01_Set_Vigente/PRD_CANONICO.md` | `01_Set_Vigente`, `docs/product` | 0 | requiere_decision_usuario | Aceptar o rechazar PRD candidato mayo 2026 | Decidir promocion del candidato. |
| PlataformaBase | PRD, ADR stack | `backend/core`, `users`, `audit`, `health`, `frontend` | 0 | resuelto_confirmado | CI main verde, acceptance local, build frontend | Mantener como baseline y no rehacer. |
| Patrimonio | PRD, modelo canonico | `backend/patrimonio`, backoffice patrimonio | 1 | implementado_sin_evidencia | Datos reales/snapshot y validacion de entidades | Validar matriz patrimonial contra datos controlados. |
| Operacion | PRD, ADR identidad envio | `backend/operacion`, backoffice operacion | 1 | implementado_sin_evidencia | Cuentas, mandatos e identidades validadas | Cerrar matriz entidad-cuenta-mandato. |
| Contratos | PRD, reglas contractuales | `backend/contratos`, backoffice contratos | 1 | implementado_sin_evidencia | Matriz contrato-propiedad-periodo-garantia | Validar relaciones y periodos contractuales. |
| CobranzaActiva | PRD, gates canales | `backend/cobranza`, `canales`, frontend | 2 | parcial | Cobros reproducibles sin envios reales accidentales | Gate aislado de cobro, correo y WebPay. |
| Conciliacion | ADR banca, gates banco | `backend/conciliacion` | 3 | parcial | Saldo sistema igual a saldo banco con data controlada | Validar proveedor o snapshot bancario autorizado. |
| Contabilidad | ADR contabilidad nativa | `backend/contabilidad`, reporting | 5 | parcial | Eventos, reglas, asientos y cierre mensual | Gate de cierre mensual desde hechos conciliados. |
| Documentos | ADR estrategia documental | `backend/documentos`, docs operativos | 5 | parcial | PDF canonico, origen, firma/notaria definida | Cerrar politica de firma/notaria y pruebas PDF. |
| SII | ADR SII, matriz gates | `backend/sii` | 4 | bloqueado_externo | Certificacion/ambiente SII y regla fiscal validada | Preparar sandbox sin emitir produccion. |
| Reporting | PRD, contabilidad, SII | `backend/reporting`, frontend reporting | 7 | implementado_sin_evidencia | Reportes trazables a ledger/datos/documentos | Bloquear reportes sin origen verificable. |
| Migracion legacy | Fuente de verdad, migration README | `migration/` | 1 | parcial | Extractores read-only y clasificacion migrable | Actualizar inventario contra savegame autorizado. |
| Operacion productiva | Runbooks, gates externos | `docs/operations`, infra, CI | 7 | parcial | Backup/restore, smoke, rollback, aceptacion | Completar runbook y smoke real autorizado. |

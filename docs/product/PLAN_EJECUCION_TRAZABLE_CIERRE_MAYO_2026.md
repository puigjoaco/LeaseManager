# Plan de ejecucion trazable de cierre - mayo 2026

Este plan conecta arquitectura, codigo, gates, evidencia y bloqueos. No
redefine el producto; ejecuta lo definido por el PRD vigente, gates externos,
ADRs activos y Arquitectura Maestra.

## Principio de avance

No se asume inicio desde cero. Cada frente empieza con diagnostico del estado
real y clasificacion:

- `resuelto_confirmado`
- `implementado_sin_evidencia`
- `parcial`
- `bloqueado_dato_real`
- `bloqueado_externo`
- `requiere_decision_usuario`
- `defectuoso`
- `duplicado`
- `desactualizado`
- `faltante`

Lo correcto se conserva. Solo se interviene lo incompleto, incorrecto,
inconsistente, duplicado, desactualizado, inseguro, mal integrado o pendiente.

## Etapas

| Etapa | Nombre | Resultado exigido |
| --- | --- | --- |
| 0 | Gobierno y baseline | Fuente de verdad, worktree policy, CI base y evidencia inicial claros. |
| 1 | Datos reales y matriz base | Matriz contrato-propiedad-cuenta-facturacion validada contra datos reales o snapshot controlado. |
| 2 | Cobranza y canales | Cobros, estados, correos/WebPay condicionados y evidencia de no envio accidental. |
| 3 | Banco y conciliacion | Movimientos, conciliacion, ingresos desconocidos y saldos cuadrados. |
| 4 | SII y DTE | Configuracion fiscal, emision aplicable, aceptacion/estado y reglas validadas. |
| 5 | Cierre mensual y contabilidad | Ledger, asientos, liquidaciones, PPM/F29/F21 y cierre mensual reproducible. |
| 6 | Renta anual | DDJJ, F22, certificados y trazabilidad anual. |
| 7 | Operacion productiva | Backups, restore, runbook, monitoreo, smoke, aceptacion y continuidad. |

## Regla de bloqueo por etapas

No avanzar de una etapa a la siguiente si el gate de la etapa actual esta
bloqueado por dato real, decision de usuario o integracion externa no abierta.
Se permite avanzar en codigo futuro solo si queda marcado como
`implementado_sin_evidencia` y no se declara cerrado.

## Metodo de ejecucion

1. Leer fuente de verdad y ficha de etapa.
2. Mapear documentos, codigo, schema, migraciones, datos, integraciones,
   pruebas, gates y evidencia.
3. Comparar contra arquitectura y PRD vigente.
4. Registrar brechas en trazabilidad o bloqueos.
5. Priorizar por dependencia, riesgo financiero/tributario y seguridad.
6. Implementar cambios acotados en worktree cuando corresponda.
7. Ejecutar gates locales.
8. Actualizar evidencia.
9. Abrir PR y esperar CI si aplica.
10. Mergear, limpiar worktree y continuar con la siguiente brecha.

## Gates minimos por cierre de frente

- Backend: `manage.py check`, migraciones coherentes, tests relevantes.
- Frontend: `npm run build` y validacion visual cuando el cambio toca UI.
- Infra: docker compose local o equivalente documentado.
- Migracion: extractores read-only, reporte de transformacion y no secretos.
- Integraciones: gate externo, entorno aislado, permisos y rollback.
- Seguridad: auth, RBAC, auditoria, secretos fuera del repo.
- Documentacion: evidencia, bloqueos y trazabilidad actualizados.

## Salida esperada

Al final de cada etapa debe existir una respuesta objetiva:

- que quedo confirmado;
- que sigue pendiente;
- que bloqueo impide avanzar;
- que evidencia respalda el estado;
- que proxima accion desbloquea el proyecto.

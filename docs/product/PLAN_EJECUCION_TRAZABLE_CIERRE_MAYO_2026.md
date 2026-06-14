# Plan de ejecucion trazable de cierre - mayo 2026

Este plan conecta arquitectura, codigo, gates, evidencia y bloqueos. Los
bloqueos son controles operativos de cierre, no estructura de arquitectura ni
modelo de dominio. El plan no redefine el producto; ejecuta lo definido por el
PRD vigente, gates externos, ADRs activos y Arquitectura Maestra.

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
| 5 | Pre-cierre mensual y contabilidad asistida | Ledger, asientos, liquidaciones, PPM/F29/F21 y paquete mensual reproducible con aprobacion responsable. |
| 6 | Renta anual automatizable | Motor tributario anual, DDJJ, F22, archivo/export certificable, certificados y trazabilidad para revision y eventual presentacion bajo gate SII. |
| 7 | Operacion productiva | Backups, restore, runbook, monitoreo, smoke, aceptacion y continuidad. |

## Regla de cierre por etapas

No declarar cerrada una etapa ni promover evidencia final si su gate esta
bloqueado por dato real, decision de usuario o integracion externa no abierta.
El bloqueo afecta el cierre, no la arquitectura del producto.

En contabilidad y tributacion, `cerrado` no significa decision autonoma del
sistema. Significa paquete reproducible, evidencia completa, reglas vigentes,
gate aplicable y aprobacion responsable. Si falta criterio experto/oficial, el
estado correcto es preparacion o revision, aunque los datos locales cuadren.
Si la regla tributaria esta completamente versionada, el formato/canal SII esta
certificado o autorizado y existe aprobacion responsable, la ejecucion puede ser
automatica como software tributario. Si falta cualquiera de esos elementos, el
resultado sigue siendo dossier/export revisable, no presentacion final.

Se permite preparar trabajo de etapas posteriores o de integracion cuando no
use datos/credenciales no autorizadas, no abra integraciones cerradas y quede
clasificado como `implementado_sin_evidencia`, `parcial` o el estado real que
corresponda. Esa preparacion no habilita saltar el gate ni declarar la etapa
resuelta.

Si el bloqueo dominante ya esta registrado con proxima accion concreta, no se
debe repetir indefinidamente la misma solicitud. La siguiente accion valida es
una de estas: ejecutar la ruta de desbloqueo si el usuario la autoriza, avanzar
en preparacion segura que acerque el cierre, registrar una nueva brecha real o
detenerse con una unica pregunta concreta si no queda trabajo seguro.

## Metodo de ejecucion

1. Leer fuente de verdad, cursor operativo y ficha de etapa.
2. Confirmar `git status --short --branch` y `git worktree list`.
3. Si existe worktree tactico sucio, terminarlo, pausarlo en el cursor o
   descartarlo con instruccion segura antes de abrir otro frente.
4. Mapear documentos, codigo, schema, migraciones, datos, integraciones,
   pruebas, gates y evidencia.
5. Comparar contra arquitectura y PRD vigente.
6. Registrar brechas en trazabilidad, bloqueos o cursor.
7. Priorizar por dependencia, riesgo financiero/tributario y seguridad.
8. Implementar cambios acotados en worktree cuando corresponda.
9. Ejecutar gates locales.
10. Actualizar evidencia, trazabilidad, bloqueos y cursor.
11. Abrir PR y esperar CI si aplica.
12. Mergear, limpiar worktree y continuar con la siguiente brecha.

## Seleccion del siguiente paquete

El siguiente paquete no se elige desde un `goal_context` ni desde una
conversacion historica. Se elige en este orden:

1. Worktree tactico sucio o paquete ya iniciado.
2. Frente activo registrado en `docs/product/EXECUTION_CURSOR_MAYO_2026.md`.
3. Etapa mas baja del orden de construccion con brecha local explicita,
   verificable y no dependiente de secretos o datos reales.
4. Preparacion segura de una etapa posterior solo si el salto queda justificado
   en el cursor por dependencia, riesgo financiero/tributario, seguridad o
   desbloqueo tecnico concreto.

Si una etapa solo tiene pendiente evidencia externa, snapshot autorizado,
credencial, decision de usuario o integracion real, no se debe endurecer por
inercia. Se registra el bloqueo y se avanza a la siguiente brecha local
justificada o se deja una unica pregunta concreta.

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
- que proxima accion desbloquea el proyecto;
- que trabajo preparatorio sigue siendo valido sin declarar cierre.

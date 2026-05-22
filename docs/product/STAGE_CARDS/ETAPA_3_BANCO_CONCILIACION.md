# Etapa 3 - Banco y conciliacion

## Objetivo

Consolidar movimientos bancarios, conciliacion, ingresos desconocidos y saldo
sistema igual a saldo banco.

## Alcance

- Proveedores bancarios.
- Movimientos.
- Reglas de matching.
- Ingresos desconocidos.
- Conciliacion y auditoria.

## Gate

- Banco real o snapshot autorizado.
- Modo no productivo por defecto.
- Conexion bancaria operativa/primaria solo con `credencial_ref`,
  `evidencia_gate_ref`, `prueba_conectividad_ref` y prueba de movimientos o
  saldos segun capacidad marcada.
- Movimiento importado por `provider_sync` solo contra conexion activa,
  primaria de movimientos, readiness trazable y `transaction_id_banco`; la
  carga manual controlada exige `evidencia_importacion_ref`.
- `audit_stage3_conciliacion_readiness` consolida readiness local de
  conexiones, movimientos, ingresos desconocidos, senales de saldo y
  referencias finales sin conectar bancos ni leer secretos.
- Cuando hay saldos reportados en movimientos de una misma conexion, el
  auditor valida continuidad local: cada saldo posterior debe continuar desde
  el saldo reportado previo aplicando abonos y cargos intermedios.
- Diferencias registradas.
- Saldo sistema igual a saldo banco antes de habilitar cierre.

## Salida

Conciliacion cerrada produce hechos confiables para contabilidad. Sin eso,
Contabilidad no puede cerrar.

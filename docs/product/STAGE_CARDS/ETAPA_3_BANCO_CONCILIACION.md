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
- Diferencias registradas.
- Saldo sistema igual a saldo banco antes de habilitar cierre.

## Salida

Conciliacion cerrada produce hechos confiables para contabilidad. Sin eso,
Contabilidad no puede cerrar.

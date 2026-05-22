# Etapa 7 - Reporting trazable

## Objetivo

Entregar reportes internos solo cuando sus cifras deriven de datos, ledger,
documentos o procesos tributarios trazables.

## Alcance

- Resumen financiero mensual.
- Libros contables por periodo.
- Resumen tributario anual.
- Visualizacion de trazabilidad en backoffice.

## Gate local

- El resumen financiero mensual requiere cierre mensual aprobado para cada
  empresa incluida, eventos contables con origen y asiento contable posteado y
  cuadrado.
- Los libros por periodo requieren `LibroDiario`, `LibroMayor` y
  `BalanceComprobacion` aprobados, resumen no vacio, balance cuadrado y cierre
  mensual aprobado.
- El resumen tributario anual requiere `ProcesoRentaAnual` preparado o superior,
  `resumen_anual` con ejercicio y obligaciones, y DDJJ/F22 asociados con resumen
  trazable. Estados aprobados, observados, rectificados o presentados requieren
  referencia externa trazable.
- Si falta alguno de esos origenes, la API responde con bloqueo de
  trazabilidad y no entrega el reporte como valido.

## Salida

Reporting sigue sin cierre final mientras falte evidencia con cierres completos,
snapshot controlado o datos reales autorizados. El gate local evita reportes sin
origen verificable, pero no reemplaza la evidencia externa/controlada requerida
por etapas anteriores.

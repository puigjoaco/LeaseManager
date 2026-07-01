# Procedimiento cambio de mes Excel

Este procedimiento documenta la forma aprobada para avanzar el Excel maestro
`Calculadora desde Nov 2023.xlsx` al mes siguiente.

Archivo maestro:

`C:\Users\puigj\Dropbox\1. Empresas\2. Inmobiliarias Herencia Papa\1. Administracion\Calculadora desde Nov 2023.xlsx`

Regla base:

- El Excel maestro se modifica en Dropbox solo cuando el usuario lo autoriza.
- Antes de tocar Dropbox, crear siempre un respaldo en el Escritorio.
- No cambiar porcentajes de propiedad.
- No corregir celdas `#VALOR!` en arriendos sin arrendar.
- No tocar meses anteriores salvo para ocultar la hoja del mes inmediatamente anterior.
- No inventar pagos, gastos ni ingresos. Solo preparar el mes.

## Pasos

1. Crear respaldo del Excel maestro en el Escritorio.

2. Duplicar las dos hojas del mes anterior:

   - `Familia Mes <mes anterior> <anio>`
   - `Inmo Puig SpA <mes anterior> <anio>`

3. Renombrar las copias al nuevo mes:

   - `Familia Mes <mes nuevo> <anio>`
   - `Inmo Puig SpA <mes nuevo> <anio>`

4. Actualizar UF del primer dia del mes nuevo:

   - Familia: celda `X56`
   - Inmo Puig: celda `Z22`

5. Limpiar entradas mensuales de Familia:

   - Arriendos / pagos locales: `W2:W50`
   - Montos/formulas heredadas de procesamiento de gastos: `AB14:AB66`
   - Listado completo de gastos: `AE21:AK79`
   - Celdas manuales de procesamiento de gastos: `AC14:AC66`
   - Ajustes laterales usados en el mes: `AB71:AB77`

   Regla especifica:

   - Familia no conserva ningun gasto ni asignacion/ruteo de gastos al pasar
     de mes.
   - No dejar links, montos, empresas, "quien pago", fechas ni detalles de
     gasto heredados del mes anterior.
   - Las celdas que dicen "Ingresar Aqui" en procesamiento de gastos de
     Familia tambien se limpian, porque si quedan heredadas pueden inducir a
     vincular el gasto nuevo al casillero anterior.
   - Tambien se limpian las formulas de resultado en `AB14:AB66`; aunque
     muestren `$0`, pueden seguir vinculadas a casilleros del mes anterior.

6. Limpiar entradas mensuales de Inmo Puig:

   - Arriendos / pagos locales: `Y2:Y15`
   - Bloque lateral de ingresos: `AD14:AH22`
   - Bloque lateral de gastos/procesamiento: `AD31:AH108`

7. En Inmo Puig, conservar solo la estructura de los gastos recurrentes
   identificados por el usuario, sin conservar montos.

   Filas mensuales recurrentes:

   - Conservar fecha, codigo y descripcion.
   - Dejar monto vacio.
   - No conservar ningun otro gasto fuera de estas filas.

   Filas usadas en junio 2026:

   - `31`: Leasing G.P.D.S. Local 15 y 16
   - `33`: Leasing G.P.D.S. Local 17 y 18
   - `35`: Leasing Mall Apumanque Local 486
   - `37`: Prima Seguro Incendio
   - `39`: Leasing G.D.C. Local 42B
   - `41`: Leasing G.P.C. Merced 839 Local 85

   Filas trimestrales / sobretasas:

   - Conservar solo descripcion.
   - Dejar monto, fecha y codigo vacios.

   Filas usadas en junio 2026:

   - `46`: Sobretasa Avda. Providencia 1336, locales 15 y 16
   - `48`: Sobretasa Avda. Providencia 1336, locales 15 y 16
   - `50`: Sobretasa Merced 839, local 85
   - `52`: Sobretasa Nueva Lyon 45, local 42B
   - `54`: Sobretasa Manquehue 31, local 486

8. Actualizar referencias de Inmo Puig:

   - `Z24` debe apuntar al saldo final del mes anterior:
     `='Inmo Puig SpA <mes anterior> <anio>'!Z29`
   - `Y16` debe apuntar al porcentaje recibido desde Familia del mes nuevo:
     `='Familia Mes <mes nuevo> <anio>'!W47/6`

9. Ocultar hojas del mes anterior.

   Ejemplo de junio a julio:

   - Ocultar `Familia Mes Junio 2026`
   - Ocultar `Inmo Puig SpA Junio 2026`
   - Dejar visibles `Familia Mes Julio 2026`
   - Dejar visibles `Inmo Puig SpA Julio 2026`

10. Crear archivo independiente para enviar a Fabiola.

    Ubicacion:

    `C:\Users\puigj\Desktop`

    Nombre ejemplo:

    `Enviar a Fabiola Julio.xlsx`

    Contenido:

    - Solo `Familia Mes Julio 2026`
    - Solo `Inmo Puig SpA Julio 2026`

    Reglas:

    - No incluir hojas de meses anteriores.
    - Si una formula apunta al mes anterior, dejar en el archivo de Fabiola el
      valor ya calculado, no una referencia externa al Excel maestro.
    - Mantener formulas internas entre las dos hojas de julio cuando aplican.

## Verificacion minima

Despues de guardar, revisar:

- Hojas del mes anterior ocultas.
- Hojas del mes nuevo visibles.
- UF correcta en `X56` y `Z22`.
- Familia limpia:
  - `X62 = 0`
  - `AC10 = 0`
  - `J65 = 0`
  - `AB14:AB66` sin formulas heredadas.
  - `AE21:AK79` sin gastos heredados.
  - `AC14:AC66` sin entradas heredadas de procesamiento de gastos.
- Inmo Puig limpia:
  - `Z27 = 0` si aun no hay gastos registrados del mes nuevo.
  - `Z29 = Z24` si aun no hay movimientos nuevos.
- Las filas recurrentes de Inmo Puig tienen descripcion/codigo cuando
  corresponde, pero no tienen monto.
- El archivo de Fabiola tiene exactamente dos hojas: Familia e Inmo Puig del
  mes nuevo.

## Ejecucion registrada: Julio 2026

El 2026-06-30 se ejecuto el paso de junio 2026 a julio 2026 con:

- UF 01-07-2026: `40.823,03`.
- Respaldo previo en Escritorio.
- Hojas de junio ocultas.
- Hojas de julio creadas y visibles.
- Archivo separado creado en Escritorio:
  `Enviar a Fabiola Julio.xlsx`.

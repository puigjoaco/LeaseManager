# Anexo Modelo Operativo Excel Mayo 2026

Estado: anexo vigente de apoyo del PRD Canonico Mayo 2026.
Fecha: 2026-05-20.
Fuente principal: contexto Excel legacy Mayo 2026 y reglas confirmadas por el usuario.

## 1. Proposito

Este anexo traduce el funcionamiento practico del Excel legacy a reglas de producto para LeaseManager. No busca copiar celdas, formulas ni posiciones fijas. Busca conservar la logica real del negocio en un sistema normalizado, auditable y operable.

El Excel legacy demuestra como se administra hoy el ciclo mensual:

1. Mantener maestros de contratos, locales, arrendatarios, RUT, direccion, rol, sociedad, comunidad o dueno.
2. Calcular canon esperado con UF/CLP, reajustes, antiguedad y codigo.
3. Leer movimientos del Banco de Chile.
4. Identificar abonos de arriendo por los ultimos tres digitos del monto.
5. Registrar el monto completo recibido, aunque incluya el codigo.
6. Separar ingresos extraordinarios, reintegros, PPM, garantias y otros movimientos.
7. Registrar gastos con fecha, monto, entidad/proyecto y criterio de reparto.
8. Repartir utilidad por sociedad, comunidad, propiedad y socio.
9. Aplicar comision/honorario de administracion cuando corresponda.
10. Cuadrar saldo final contra banco antes de cerrar el mes.

## 2. Principio de transformacion

LeaseManager no debe automatizar el Excel como planilla. Debe reemplazarlo como sistema de verdad.

La transformacion correcta es:

```text
Celda o formula del Excel
-> entidad normalizada
-> regla de negocio
-> evento auditable
-> calculo reproducible
-> evidencia de banco/contrato/participacion
-> reporte o liquidacion final
```

Reglas:

- Las posiciones de celdas no son contrato de producto.
- Los codigos de local, participaciones, contratos, cuentas y arrendatarios viven en tablas normalizadas.
- Todo movimiento bancario se conserva con su fecha, cuenta, monto, descripcion, origen y clasificacion.
- Una clasificacion automatica es solo valida si existe regla segura; si no, queda para revision humana.
- El cierre mensual se bloquea si el saldo sistema no cuadra con banco.

## 3. Matching de arriendos por codigo

Regla practica confirmada:

- Los abonos de arriendo suelen terminar en un codigo de tres digitos.
- Ese codigo identifica el local dentro de su seccion operativa.
- El monto completo se registra como pago recibido, incluyendo esos tres digitos.
- El codigo ayuda a identificar el contrato, pero no reemplaza cuenta bancaria, entidad, periodo ni revision de excepciones.

Implicacion en LeaseManager:

- El matching automatico debe usar como minimo cuenta bancaria, fecha, monto, sufijo de tres digitos, seccion operativa, contrato activo y arrendatario esperado.
- El codigo no es global: puede repetirse entre Familia, Joaquin, Inmo Puig u otras secciones.
- Si el codigo no existe, existe en varias secciones posibles, el monto es anomalo, el pagador no calza o el periodo esta cerrado, el movimiento queda como excepcion.
- Si existe token/transaction id de WebPay, ese identificador prevalece sobre matching por monto.
- El matching por codigo debe dejar rastro: movimiento original, regla aplicada, contrato asociado, usuario/proceso y resultado.

Estados sugeridos:

- `pendiente_clasificacion`
- `match_automatico_seguro`
- `match_sugerido`
- `requiere_revision`
- `conciliado`
- `rechazado`
- `reclasificado`

## 4. Ingresos extraordinarios y reintegros

El Excel separa arriendos normales de ingresos laterales. LeaseManager debe conservar esa distincion.

Categorias minimas:

- Arriendo mensual.
- Reintegro o devolucion.
- PPM pagado por error y reembolsado.
- Garantia recibida, retenida, devuelta o aplicada.
- Ingreso extraordinario de sociedad.
- Ingreso extraordinario de comunidad.
- Transferencia interna entre entidades.
- Liquidacion de periodo anterior.
- Regularizacion o ajuste aprobado.

Reglas:

- Un ingreso que no calza con contrato activo no se debe forzar como arriendo.
- Un reintegro por PPM no aumenta renta ni base de reparto como arriendo.
- Una transferencia interna debe tener entidad origen, entidad destino, motivo y periodo.
- Si el dinero entra en una cuenta que no corresponde al beneficiario final, se requiere liquidacion o transferencia trazada antes de conciliar al beneficiario.

## 5. Gastos y egresos

El Excel procesa gastos por entidad, propiedad, comunidad, grupo de socios o criterio especial. LeaseManager debe modelar esa clasificacion explicitamente.

Categorias minimas:

- Gasto operativo de sociedad.
- Gasto de propiedad/local especifico.
- Gasto de comunidad.
- Gasto dividido por socios.
- Gasto de sucesion.
- PPM/impuesto.
- Leasing.
- Imposiciones u obligaciones laborales/previsionales.
- Gasto pagado por entidad equivocada.
- Transferencia/liquidacion a socio.
- Pago de administracion.
- Movimiento no clasificado.

Reglas:

- Todo cargo bancario entra como movimiento.
- Ningun gasto desconocido se clasifica automaticamente por conveniencia.
- Las categorias protegidas no se cambian por similitud de texto: garantia, PPM, liquidacion a socio, transferencia interna, gasto pagado por entidad equivocada, reintegro, cobranza residual y regularizacion exigen evidencia o resolucion manual.
- Ingresos manuales y gastos manuales deben tener referencia interna unica y sin colision entre tipos, con origen, usuario/proceso, fecha, entidad, periodo economico y evidencia cuando exista.
- Una clasificacion debe indicar entidad economica afectada, cuenta bancaria que pago, periodo economico, documento/evidencia si existe y criterio de reparto.
- Las liquidaciones del mes anterior pagadas el primer dia habil del mes siguiente mantienen el periodo economico original.
- El ingreso masivo de gastos puede acelerar captura, pero no puede aplicar porcentajes o formulas globales sin validar cada gasto con monto, propiedad/entidad, detalle, categoria, periodo y evidencia.

## 6. Participaciones y repartos

El Excel usa matrices de porcentajes para repartir ingresos, gastos y utilidad. LeaseManager debe convertir esas matrices en participaciones con vigencia.

Requisitos:

- Participaciones por propiedad, comunidad, sociedad o regla especial.
- Fecha de inicio y termino de vigencia.
- Soporte para participaciones de personas naturales y sociedades.
- Soporte para redistribuciones por sucesion o instrucciones posteriores.
- Calculo de ingreso, gasto, utilidad y monto final por socio.
- Checks de control: total participaciones = 100%, total distribuido = utilidad distribuible y saldos bancarios cuadran.

Regla especial confirmada:

- Tras el fallecimiento de Cristian, su participacion/pago operativo debe tratarse como Catalina y Trinidad, 50% cada una, con depositos separados si existen cuentas separadas.

## 7. Comision u honorario de administracion

El Excel aplica un ajuste mensual donde ciertos socios tienen un descuento y Joaquin recibe un abono por administracion.

LeaseManager no debe representarlo como una resta informal. Debe modelarlo como:

- Concepto de liquidacion.
- Periodo.
- Beneficiario.
- Participantes cargados.
- Monto por participante.
- Cuenta destino si se paga.
- Evidencia bancaria cuando exista transferencia.
- Efecto contable/tributario a validar segun corresponda.

Regla:

- El ajuste no debe alterar artificialmente la utilidad del mes; debe aparecer como linea explicita de liquidacion y/o gasto/honorario segun validacion contable.

## 8. Cuentas bancarias y separacion por entidad

El Excel historico mezcla parte de la operacion de San Cristobal, Santa Maria, Quepe y comunidades en una logica comun. LeaseManager debe mantener la logica de negocio, pero no la mezcla bancaria.

Reglas:

- Cada sociedad, comunidad operativa o persona natural usa su cuenta definida.
- El sistema no presume fondos comunes.
- Si una cuenta recibe dinero de otra entidad, debe existir transferencia, mandato, clasificacion o liquidacion que explique el flujo.
- El saldo final de cada cuenta debe cuadrar con banco.
- Las cuentas de comunidades y personas naturales no se usan como cuentas tributarias de sociedad.

## 9. Edificio Q y participaciones mixtas

El Excel muestra un problema importante: una participacion puede aparecer como ingreso contable esperado aunque el dinero no haya entrado a la cuenta bancaria de la entidad participante.

Regla para LeaseManager:

- Si una comunidad recibe 100% del arriendo y una sociedad participa en la propiedad, la sociedad solo puede reconocer ingreso bancariamente conciliado cuando reciba su transferencia real o exista movimiento intercuenta trazado.
- La factura de la sociedad, cuando corresponda, se calcula por porcentaje activo sobre valor vigente del contrato.
- No se duplica la propiedad para representar la participacion.
- La distribucion mensual debe crear obligaciones/transferencias hacia cada participante, incluida la sociedad participante.

## 10. Cierre mensual derivado del Excel

Un mes se considera cerrado solo si:

- Todos los contratos activos tienen estado de cobro claro.
- Todos los movimientos bancarios del periodo estan conciliados, clasificados o bloqueados con razon.
- Los ingresos de arriendo, extraordinarios y reintegros estan separados.
- Los gastos estan clasificados por entidad, propiedad, comunidad, socio o criterio de reparto.
- Las participaciones vigentes fueron aplicadas.
- Las liquidaciones a socios fueron calculadas.
- La comision de administracion fue registrada como concepto explicito.
- Las transferencias intercuenta necesarias fueron registradas o quedan como pendiente bloqueante.
- Los saldos por entidad cuadran contra banco.
- La evidencia del cierre queda vinculada.

## 11. Modelo de datos minimo derivado

Tablas o conceptos necesarios:

- `empresas`
- `socios`
- `comunidades`
- `propiedades`
- `arrendatarios`
- `contratos`
- `periodos_contractuales`
- `participaciones`
- `cuentas_bancarias`
- `movimientos_bancarios`
- `pagos_mensuales`
- `clasificaciones_movimiento`
- `ingresos_extraordinarios`
- `gastos`
- `liquidaciones_mensuales`
- `lineas_liquidacion`
- `transferencias_interentidad`
- `comisiones_administracion`
- `valores_uf`
- `asientos_contables`
- `audit_log`
- `evidencias_cierre`

El nombre exacto puede variar segun schema real, pero la capacidad debe existir.

## 12. Pruebas obligatorias inspiradas en el Excel

- Matching por codigo correcto dentro de la seccion operativa.
- Codigo repetido en otra seccion no genera match cruzado.
- Pago con monto distinto al canon esperado queda conciliable pero auditado.
- Canon esperado conserva UF usada, fecha efectiva, reajuste, codigo aplicado y monto real recibido.
- Abono complementario del mismo arrendatario puede sumarse solo con regla/decision.
- Reintegro PPM no se clasifica como arriendo.
- Gasto pagado por entidad equivocada genera reintegro o transferencia interentidad.
- Participacion de Inmo Puig en comunidad no se concilia como ingreso bancario sin transferencia real.
- Sucesion de Cristian reparte a Catalina y Trinidad segun regla vigente.
- Comision de administracion queda como linea explicita.
- Garantia recibida, aplicada, retenida o devuelta no se mezcla con utilidad operacional sin criterio contable.
- Liquidacion pagada el primer dia habil del mes siguiente mantiene periodo economico original.
- Cierre mensual falla si saldo sistema no coincide con banco.
- Cierre mensual falla si existen movimientos no clasificados sin bloqueo documentado.

## 13. Criterio de exito

LeaseManager habra absorbido correctamente la logica del Excel cuando pueda ejecutar un mes controlado completo y producir:

- Matriz de cobros por contrato.
- Conciliacion bancaria por cuenta.
- Clasificacion de ingresos y gastos.
- Reporte de excepciones.
- Liquidacion por socio/persona/entidad.
- Transferencias interentidad requeridas.
- Asientos contables.
- Resumen tributario mensual.
- Evidencia de que los saldos finales cuadran contra banco.

Ese resultado debe ser reproducible sin editar manualmente celdas de Excel y sin perder la trazabilidad que hoy la planilla entrega implicitamente.

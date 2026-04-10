# ADR 008 - Contabilidad nativa y motor contable

Estado: aprobado  
Fecha: 15/03/2026  
PRD relacionado: [PRD_CANONICO.md](./PRD_CANONICO.md)

## Contexto

LeaseManager deja de depender estructuralmente de un rol `Contadora` y pasa a absorber la conciliacion bancaria, el ledger contable, el cierre mensual y la preparacion tributaria dentro del sistema. Eso exige una capacidad contable nativa, auditable e integrada con la operacion, en vez de depender de un ERP externo como libro maestro.

## Decision

LeaseManager adopta contabilidad nativa basada en double-entry ledger.

Decisiones aprobadas:

1. El sistema de registro oficial vive dentro de LeaseManager.
2. Todo hecho economico confirmado genera `EventoContable`.
3. El `MotorContable` traduce cada evento a `AsientoContable` segun `ReglaContable`.
4. Todo `AsientoContable` debe cuadrar `debe = haber`.
5. El plan de cuentas base es nativo, versionado y configurable por empresa dentro de limites controlados.
6. El cierre mensual contable es prerequisito para preparar obligaciones tributarias mensuales.
7. El proceso anual consolida doce cierres aprobados para generar `DDJJ` y `F22` en modo preparado.
8. La aprobacion de cierres y salidas tributarias finales corresponde a `AdministradorGlobal`.
9. Un revisor externo puede observar o comentar, pero no es prerequisito del flujo base.
10. El unico regimen fiscal automatizable del v1 es `EmpresaContabilidadCompletaV1`.

## Forma de implementacion

Entidades minimas:

- `EventoContable`
- `ReglaContable`
- `CuentaContable`
- `AsientoContable`
- `MovimientoAsiento`
- `LibroDiario`
- `LibroMayor`
- `BalanceComprobacion`
- `CierreMensualContable`
- `ObligacionTributariaMensual`
- `ProcesoRentaAnual`

Fuentes minimas de `EventoContable`:

- pago conciliado;
- DTE emitido o anulado;
- garantia recibida, devuelta o retenida;
- ajuste de contrato con efecto economico;
- repactacion confirmada;
- gasto o comision operacional;
- acuerdo de termino con impacto economico.

Reglas del motor:

- cada evento usa `idempotency_key`;
- un evento no desaparece silenciosamente si falla la contabilizacion;
- un asiento de periodo cerrado no se edita, se revierte o complementa;
- el cierre mensual falla si hay eventos pendientes o asientos descuadrados.

Plan de cuentas base v1:

| Grupo | Cuentas minimas |
|---|---|
| `Activo` | `Bancos`, `CuentasPorCobrarArriendos`, `CuentasPorCobrarCobranzaResidual`, `IVA_Credito_si_aplica` |
| `Pasivo` | `GarantiasRecibidas`, `IVA_Debito`, `PPM_por_Pagar`, `Retenciones_por_Pagar`, `ArriendosCobradosPorAnticipado_si_aplica` |
| `Patrimonio` | `CapitalYPatrimonio`, `ResultadosAcumulados`, `ResultadoDelEjercicio` |
| `Ingresos` | `IngresosPorArriendo`, `RecuperacionGastosComunes`, `OtrosIngresosOperacionales` |
| `Gastos` | `ComisionesBancarias`, `GastosDocumentalesYNotariales`, `GastosOperacionalesNoRecuperables` |

Reglas de configuracion del plan de cuentas:

- una empresa puede agregar subcuentas y centros de resultado;
- una empresa no puede eliminar ni renombrar cuentas de control obligatorias del v1;
- toda customizacion genera nueva `plan_cuentas_version`;
- la `MatrizReglasContables` siempre referencia una version explicita del plan.

Matriz minima de reglas contables v1:

| Evento | Debe | Haber |
|---|---|---|
| `DevengoArriendo` | `CuentasPorCobrarArriendos` | `IngresosPorArriendo` + `IVA_Debito_si_aplica` |
| `PagoConciliadoArriendo` | `Bancos` | `CuentasPorCobrarArriendos` |
| `GarantiaRecibida` | `Bancos` | `GarantiasRecibidas` |
| `GarantiaDevuelta` | `GarantiasRecibidas` | `Bancos` |
| `GarantiaAplicadaADeuda` | `GarantiasRecibidas` | `CuentasPorCobrarArriendos` o `CuentasPorCobrarCobranzaResidual` |
| `AjusteEconomicoContrato` | segun naturaleza del ajuste | cuenta espejo definida por `MatrizReglasContables` |
| `ComisionBancaria` | `ComisionesBancarias` | `Bancos` |

Politica de reverso v1:

- si el periodo sigue abierto, el sistema usa asiento complementario o reverso en el mismo periodo segun `PoliticaReversoContable`;
- si el periodo ya fue aprobado, la correccion ocurre en el primer periodo abierto disponible mediante reverso o asiento complementario con referencia al asiento origen;
- la reapertura solo procede si el error afecta cierre tributario, documento emitido o un saldo material definido por politica interna;
- ninguna correccion posterior elimina el rastro del asiento original.

## Relacion con SII

- `F29Preparacion` consume `ObligacionTributariaMensual` y el cierre mensual aprobado.
- `DDJJPreparacion` y `F22Preparacion` consumen `ProcesoRentaAnual`.
- la preparacion puede automatizarse con gates abiertos;
- la presentacion final critica sigue aprobada por `AdministradorGlobal`.
- `F29Presentacion` puede activarse bajo gate propio;
- `PresentacionAnualFinal` queda fuera del boundary activo del v1.

## Consecuencias

- la contabilidad deja de ser un subproducto futuro y pasa a ser nucleo del sistema;
- aumenta la complejidad del dominio, pero elimina dependencia estructural de un tercero humano;
- se vuelve posible preparar cierres mensuales y renta anual desde la operacion real del sistema.

## Alternativas descartadas

- ERP externo como libro maestro obligatorio: descartado por dependencia estructural.
- conciliacion sin ledger contable: descartado por falta de cierre integral.
- preparacion tributaria sin cierre contable previo: descartada por inconsistencia operacional.


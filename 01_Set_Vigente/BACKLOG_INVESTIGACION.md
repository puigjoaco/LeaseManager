# Backlog de investigacion y expansion - LeaseManager

Estado: vigente  
Fecha: 15/03/2026  
Documento rector relacionado: [PRD_CANONICO.md](./PRD_CANONICO.md)

## 1. Regla de uso

Este backlog ya no contiene decisiones necesarias para operar el boundary activo del v1. Todo el core del producto debe poder construirse leyendo solo el set activo vigente.

Este backlog sobrevive solo para:

- expansiones futuras fuera del boundary activo;
- capacidades podadas que podrian reconsiderarse en una reemision posterior;
- optimizaciones no necesarias para que el v1 sea correcto y autosuficiente.

Estados:

- `ExpansionFutura`
- `EnValidacion`
- `Descartado`

## 2. Items activos

| ID | Tema | Estado | Relacion con el producto | Situacion vigente |
|---|---|---|---|---|
| `EXP-001` | segundo provider bancario despues de `BancoDeChile` | `ExpansionFutura` | mejora cobertura comercial, no condiciona el core | el dominio ya es multi-provider, pero solo hay un adapter oficial activo |
| `EXP-002` | portal de socios avanzado/autoservicio | `ExpansionFutura` | mejora experiencia de consulta, no es requisito operativo base | el v1 mantiene reporting filtrado para socios |
| `EXP-003` | automatizacion con `PortalInmobiliario` | `ExpansionFutura` | capacidad comercial fuera del boundary activo | actualmente esta podada del set activo |
| `EXP-004` | automatizacion con `Yapo` | `ExpansionFutura` | capacidad comercial fuera del boundary activo | actualmente esta podada del set activo |
| `EXP-005` | match exacto avanzado para `CodigoCobroResidual` por referencias bancarias mas ricas | `EnValidacion` | optimiza cobranza residual, no bloquea el core | el v1 opera residual en exacto solo si la referencia es confiable; si no, asistido/manual |
| `EXP-006` | clasificacion documental asistida por IA | `ExpansionFutura` | optimizacion operativa fuera del boundary activo | actualmente podada del set activo |
| `EXP-007` | IA semantica y asistente conversacional | `ExpansionFutura` | capacidad avanzada fuera del boundary activo | actualmente podada del set activo |

## 3. Criterio de reingreso al set activo

Un item solo puede reingresar al set activo cuando:

- exista evidencia verificable suficiente;
- no rompa el boundary activo ni el dominio vigente;
- se actualicen el `PRD`, los `ADR` y la `Matriz de gates`;
- quede registrada una nueva emision documental que lo incorpore explicitamente.


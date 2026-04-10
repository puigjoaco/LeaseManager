# Backlog Fase 2 - Operacion asistida

## 1. Objetivo de la fase

Extender el nucleo a:

- conciliacion asistida;
- cierre mensual contable y tributario;
- `F29Preparacion`;
- WhatsApp gated;
- formalizacion documental;
- reporting operativo y financiero base.

## 2. Bloques de trabajo

### B1. Conciliacion asistida

| ID | Entrega | Depende de | Criterio de listo |
|---|---|---|---|
| `F2-B1-01` | reglas de sugerencia asistida | cierre Fase 1 | sugerencias separadas de asignacion final |
| `F2-B1-02` | UI de resolucion asistida | `F2-B1-01` | operador revisa y aprueba |

### B2. Cierre mensual

| ID | Entrega | Depende de | Criterio de listo |
|---|---|---|---|
| `F2-B2-01` | `CierreMensualContable` | `F1-B5-05` | periodo pasa `Borrador -> Preparado -> Aprobado` |
| `F2-B2-02` | `PoliticaReversoContable` aplicada | `F2-B2-01` | correcciones post-cierre operan con reverso/complemento |
| `F2-B2-03` | validaciones de periodo y bloqueos | `F2-B2-01` | no se aprueba con pendientes ni descuadres |

### B3. Fiscalidad y `F29Preparacion`

| ID | Entrega | Depende de | Criterio de listo |
|---|---|---|---|
| `F2-B3-01` | calculo de `ObligacionTributariaMensual` | `F2-B2-01`, `F1-B5-01` | obligaciones mensuales salen del ledger |
| `F2-B3-02` | `EstadoPreparacionTributaria` | `F2-B3-01` | estados trazables del borrador |
| `F2-B3-03` | borrador `F29Preparacion` | `F2-B3-02` | resumen mensual aprobable por admin |

### B4. Documentos y formalizacion

| ID | Entrega | Depende de | Criterio de listo |
|---|---|---|---|
| `F2-B4-01` | flujo de firma documental | `F1-B6-03` | estado documental y evidencia de firma |
| `F2-B4-02` | evidencia de notaria cuando aplique | `F2-B4-01` | no se formaliza sin respaldo requerido |

### B5. Canales adicionales

| ID | Entrega | Depende de | Criterio de listo |
|---|---|---|---|
| `F2-B5-01` | `WhatsApp.Salida` gated | `F1-B2-05`, `F1-B6-03` | canal opera solo con template y gate valido |
| `F2-B5-02` | fallbacks de comunicacion | `F2-B5-01` | bloqueo WA deriva a email y alerta |

### B6. Reporting

| ID | Entrega | Depende de | Criterio de listo |
|---|---|---|---|
| `F2-B6-01` | dashboard operativo mensual | `F2-B2-01`, `F2-B3-03` | pagos, cierres y obligaciones visibles |
| `F2-B6-02` | reportes contables base | `F2-B2-01` | libro diario, mayor y balance consultables |

## 3. Definicion de cierre de Fase 2

La fase cierra solo si:

- el mes puede cerrarse contable y operativamente;
- el sistema genera `F29Preparacion` desde el ledger;
- WhatsApp opera solo bajo gate valido;
- documentos quedan formalizados segun su politica;
- reporting muestra estado operativo y financiero consistente.

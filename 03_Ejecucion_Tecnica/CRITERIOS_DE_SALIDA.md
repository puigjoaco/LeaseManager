# Criterios de salida por hito - LeaseManager

## 1. Regla general

Ningun hito se da por cerrado si:

- hay contradiccion con el set activo;
- faltan permisos o auditoria;
- el flujo solo funciona en happy path;
- el dato contable o tributario no es trazable al origen;
- hay dependencias activas hacia capacidades podadas.

## 2. Criterios por fase

### Salida Fase 0

- autenticacion, RBAC y auditoria base operativos;
- secretos y storage separados;
- entorno local y entorno compartido utilizables.

### Salida Fase 1

- se puede crear empresa, propiedad, mandato y contrato validos;
- se genera `PagoMensual` correcto;
- conciliacion exacta o manual operativa;
- evento contable y asiento contable base generados;
- documento contractual PDF emitible;
- email operativo.

### Salida Fase 2

- cierre mensual aprobado sin pendientes;
- `F29Preparacion` generada desde ledger;
- WhatsApp gated funcionando;
- documentos formalizados segun politica;
- reporting operativo y contable base consistente.

### Salida Fase 3

- residual, repactaciones y reporting financiero robustos;
- libro diario, mayor y balance confiables para operacion;
- socios pueden ver reporting filtrado sin romper permisos.

### Salida Fase 4

- `DDJJPreparacion` y `F22Preparacion` generadas desde doce cierres aprobados;
- compliance de datos personales preparado para operar en fecha;
- reporting anual consolidado.

### Salida Fase 5

- `F29Presentacion` puede activarse bajo gate formal;
- el core puede escalar sin romper trazabilidad;
- no existe automatizacion critica fuera de gate.

## 3. Regla de no-regresion

Al cerrar cualquier fase debe mantenerse:

- `debe = haber` en todo asiento;
- no duplicacion de hechos economicos;
- no asignacion automatica de pagos ambiguos;
- no uso de capacidades podadas;
- no salida tributaria final sin aprobacion de `AdministradorGlobal`.


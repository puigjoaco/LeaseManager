# ADR 003 - Capacidades SII separadas por flujo

Estado: aprobado  
Fecha: 15/03/2026  
PRD relacionado: [PRD_CANONICO.md](./PRD_CANONICO.md)

## Contexto

El maestro anterior trataba `API SII` como una sola integracion por fases. Eso ocultaba que los requisitos, certificados, aprobaciones y riesgos cambian segun el flujo tributario.

## Decision

LeaseManager separa SII por capacidades, no por un bloque unico.

Capacidades canonicas:

1. `DTEEmision`
2. `DTEConsultaEstado`
3. `BoletaEmision`
4. `LibrosYArchivos`
5. `F29Preparacion`
6. `F29Presentacion`
7. `DDJJPreparacion`
8. `F22Preparacion`
9. `PresentacionAnualFinal`

Politica de activacion:

- el unico regimen fiscal automatizable en el v1 es `EmpresaContabilidadCompletaV1`;
- `DTEEmision` y `DTEConsultaEstado` pueden activarse por empresa cuando el gate correspondiente esta abierto;
- `BoletaEmision` queda fuera del boundary activo del v1;
- `LibrosYArchivos` queda fuera del boundary activo del v1;
- `F29Preparacion` se apoya en el cierre mensual contable aprobado;
- `F29Presentacion` solo se habilita si el gate especifico esta abierto;
- `DDJJPreparacion` y `F22Preparacion` se apoyan en el `ProcesoRentaAnual`;
- `PresentacionAnualFinal` queda fuera del boundary activo del v1 y requiere futura reemision del set si se quisiera activar;
- toda capacidad que requiera firma tributaria debe usar certificado digital aceptado por el SII y operativo para la empresa correspondiente.
- `F29Preparacion` se calcula desde el ledger y la configuracion fiscal interna de LeaseManager; no depende de una propuesta automatica transferida por SII.

## Forma de implementacion

Entidad operacional minima:

- `CapacidadTributariaSII`
  - `empresa_id`
  - `capacidad_key`
  - `certificado_ref`
  - `ambiente`
  - `estado_gate`
  - `ultimo_resultado`

Condiciones minimas por capacidad:

- `ConfiguracionFiscalEmpresa` completa y vigente;
- certificado vigente;
- ambiente configurado;
- credenciales y folios cuando apliquen;
- prueba exitosa para el flujo especifico;
- aprobacion operativa si el flujo es de criticidad alta.
- cierre mensual o anual aprobado cuando la capacidad consuma informacion consolidada.

Matriz de aprobacion minima:

- `DTEEmision`: no requiere aprobacion humana por documento una vez abierto el gate y validado el `MandatoOperacion`.
- `DTEConsultaEstado`: no requiere aprobacion humana por consulta.
- `BoletaEmision`: podada del boundary activo.
- `LibrosYArchivos`: podada del boundary activo.
- `F29Preparacion`: no requiere aprobacion por borrador una vez aprobado el cierre mensual.
- `F29Presentacion`: requiere aprobacion de `AdministradorGlobal`.
- `DDJJPreparacion`: no requiere aprobacion por borrador una vez aprobado el proceso anual.
- `F22Preparacion`: no requiere aprobacion por borrador una vez aprobado el proceso anual.
- `PresentacionAnualFinal`: podada del boundary activo.

Regla de consistencia tributaria:

- `F29Preparacion`, `DDJJPreparacion` y `F22Preparacion` deben ser consistentes con el ledger interno, los DTE emitidos y la configuracion fiscal activa de la empresa.

## Consecuencias

- La activacion tributaria deja de ser binaria y opaca.
- El v1 queda cerrado a un regimen fiscal y a un set concreto de capacidades.
- Se reduce la sobrepromesa regulatoria.

## Alternativas descartadas

- Una sola `API SII` para todo: descartada por ambigua.
- Automatizacion tributaria critica por defecto: descartada por riesgo regulatorio y operacional.


# ADR 001 - Banca multi-provider

Estado: aprobado  
Fecha: 15/03/2026  
PRD relacionado: [PRD_CANONICO.md](./PRD_CANONICO.md)

## Contexto

El maestro anterior trataba a Banco de Chile como decision de producto. Eso mezclaba la necesidad de negocio con el primer proveedor disponible y acoplaba el dominio a una sola institucion financiera.

LeaseManager necesita conciliar pagos, validar conectividad y sincronizar saldos sin volver a reescribir el dominio cada vez que entre o salga un banco.

## Decision

LeaseManager adopta una arquitectura bancaria multi-provider.

Decisiones canonicamente aprobadas:

1. El dominio define una interfaz conceptual `ProviderBancario`.
2. `BancoDeChile` es el primer adapter oficial, no el limite del producto.
3. La recaudacion se modela sobre `CuentaRecaudadora`, no sobre un banco fijo.
4. Cada `CuentaRecaudadora` puede tener multiples `ConexionBancaria`, pero solo una primaria activa por capacidad automatica.
5. Las capacidades minimas de un provider son:
   - `Movimientos`
   - `Saldos`
   - `Conectividad`
6. La conciliacion automatica solo opera con datos suficientes y confiables del provider.
7. El fallback autorizado ante falla del provider es operacion manual auditada.
8. Queda prohibido el scraping de portales y el uso de credenciales no oficiales como estrategia canonicamente soportada.

## Forma de implementacion

Contrato conceptual minimo de `ProviderBancario`:

- `sync_movimientos(cuenta_recaudadora, rango)`
- `sync_saldos(cuenta_recaudadora)`
- `validate_connectivity(cuenta_recaudadora)`
- `describe_capabilities()`

Estados minimos de `ConexionBancaria`:

- `Verificando`
- `Activa`
- `Pausada`
- `Inactiva`

Politica de conciliacion por capacidad:

- `Movimientos` activa: match exacto permitido.
- `Movimientos` parcial o degradada: match asistido o manual.
- `Movimientos` suspendida: operacion manual obligatoria.

## Consecuencias

- El dominio deja de estar atado a Banco de Chile.
- El roadmap puede incorporar nuevos providers sin romper contratos ni formulas.
- La matriz de gates debe activar cada provider y capacidad por separado.
- El costo inicial de abstraccion sube levemente, pero evita lock-in de producto.

## Alternativas descartadas

- Producto bancario single-provider permanente: descartado por lock-in de dominio.
- Scraping como fallback: descartado por seguridad, compliance y fragilidad.


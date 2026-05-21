# Etapa 4 - SII y DTE

## Objetivo

Preparar facturacion y comunicacion tributaria sin emitir ni certificar contra
produccion por defecto.

## Alcance

- Configuracion fiscal por empresa.
- DTE 34 cuando corresponda.
- Estados y respuestas SII.
- Validacion de reglas tributarias.

## Gate

- Empresa emisora habilitada.
- Comunidades y personas naturales tratadas segun regla validada.
- Certificado/ambiente aislado autorizado.
- Regla fiscal respaldada por SII, normativa o experto.

## Preparacion local segura

- Las capacidades SII abiertas deben registrar refs trazables de certificado,
  evidencia, prueba de flujo, autorizacion de ambiente y regla fiscal cuando
  aplica.
- Los borradores DTE/F29/anuales y los cambios de estado externo revalidan el
  gate antes de avanzar.
- `F29Presentacion` y `PresentacionAnualFinal` no se registran desde el flujo
  local sin gate propio o reemision formal del set.

## Salida

SII no cierra con mocks. Requiere evidencia de ambiente autorizado y regla
fiscal validada.

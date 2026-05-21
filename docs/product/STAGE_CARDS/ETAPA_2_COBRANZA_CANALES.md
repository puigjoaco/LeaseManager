# Etapa 2 - Cobranza y canales

## Objetivo

Cerrar cobranza activa, estados de cuenta, codigos de cobro y canales
condicionados sin envios reales accidentales.

## Alcance

- Pagos mensuales.
- Ajustes y garantias.
- Codigos residuales.
- Estados de cuenta.
- Email, WebPay y notificaciones condicionadas.

## Gate

- Datos de Etapa 1 confirmados.
- Envio externo cerrado por defecto.
- Prueba aislada de correos/WebPay.
- Evidencia de auditoria por operacion critica.
- Registro manual de envio solo con `external_ref` trazable y revalidacion del
  gate abierto, identidad activa, destinatario y mandato operativo activo.

## Salida

Cobranza puede cerrarse solo si los cobros trazan a contrato, propiedad, cuenta
y periodo contractual. Sin Etapa 1 cerrada y sin prueba aislada de integracion
externa, el frente queda en preparacion segura o `parcial`, no cerrado.

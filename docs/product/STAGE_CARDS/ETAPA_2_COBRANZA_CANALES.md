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
- Email cerrado/condicionado por defecto: un gate `Email.Salida` abierto
  requiere `evidencia_ref`, referencia de prueba aislada/envio y referencia
  OAuth/credencial validada; preparar o registrar envio revalida esas
  referencias antes de permitir operacion manual controlada. El cierre local
  exige `IdentidadDeEnvio` Email activa y `AsignacionCanalOperacion` activa
  sobre mandato operativo activo; el sistema no inventa remitente sustituto.
- WhatsApp cerrado por defecto: requiere opt-in con evidencia, template
  aprobado registrado en el gate, ventana `08:00-21:00 America/Santiago`,
  identidad activa y contacto no bloqueado. Si el gate WhatsApp queda abierto,
  el readiness exige identidad y asignacion WhatsApp activas.
- WebPay cerrado/condicionado por defecto: preparar intento local requiere gate
  `WebPay.IntentoPago`, retorno controlado y evidencia; confirmar manualmente
  requiere `external_ref` trazable y `fecha_pago_webpay` diferenciada. Ningun
  flujo llama Transbank ni marca pago confirmado sin revalidar el gate.
- Auditoria local `audit_stage2_cobranza_readiness` consolida pagos mensuales,
  identidades/asignaciones de canal, gates Email/WhatsApp/WebPay, mensajes
  enviados/preparados e intentos WebPay sin enviar mensajes ni conectar
  proveedores externos.

## Salida

Cobranza puede cerrarse solo si los cobros trazan a contrato, propiedad, cuenta
y periodo contractual. Sin Etapa 1 cerrada y sin prueba aislada de integracion
externa, el frente queda en preparacion segura o `parcial`, no cerrado.

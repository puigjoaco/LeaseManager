# Etapa 0 - Gobierno y baseline

## Objetivo

Dejar claro que manda, como se trabaja, cual es el baseline tecnico y que
evidencia respalda el root limpio.

## Entradas

- `AGENTS.md`
- `docs/governance/SOURCE_OF_TRUTH_MAYO_2026.md`
- `docs/governance/CODEX_OPERATING_PROTOCOL_MAYO_2026.md`
- `docs/product/EXECUTION_CURSOR_MAYO_2026.md`
- `docs/RELEASE_GATE_BASELINE_MAYO_2026.md`
- CI en `main`

## Gate

- Fuente de verdad sin ambiguedad.
- Worktree policy documentada.
- Cursor operativo vigente para reanudaciones, worktrees y metatareas cerradas.
- Artefactos locales de herramienta quedan fuera del versionado y no deben
  ensuciar `git status` del root limpio ni confundirse con paquete activo.
- Superficies publicas con errores seguros, sin mensajes internos ni nombres de
  configuracion expuestos.
- Auth no expone metadata de usuario sensible: login, login demo y `/me`
  devuelven metadata redactada, la firma interna de cache demo no viaja al
  cliente y el admin muestra metadata y `legacy_reference` solo redactados, sin
  permitir borrado manual de usuarios.
- El detector transversal de referencias sensibles redacta valores y claves de
  metadata como `authorization` y `private_key`, sin tratar refs operativas no
  sensibles como secretos por su nombre de valor.
- Auditoria no expone referencias sensibles heredadas en API ni snapshot:
  eventos redactan actor, entidad, resumen, request id y metadata; las
  resoluciones manuales redactan scope, resumen, rationale y metadata, y la API
  generica rechaza nuevas escrituras con referencias sensibles.
- Las resoluciones manuales genericas conservan actor de solicitud y cierre
  trazable: la API crea casos abiertos con `requested_by` del usuario actual,
  no acepta cierres al crear, exige rationale para cerrar y estampa
  `resolved_by`/`resolved_at` desde el usuario autenticado.
- Las resoluciones manuales genericas registran eventos de ciclo de vida en la
  misma transaccion que la escritura: creacion, cambios de estado y ediciones
  comunes crean `AuditEvent` dedicado, y si falla esa auditoria se revierte la
  creacion o mutacion.
- El admin Django de Auditoria es solo lectura para eventos y resoluciones
  manuales: no permite alta, cambio ni borrado manual, y conserva campos
  crudos sensibles solo como versiones redactadas.
- Los admins RBAC de Core no exponen metadata ni permission sets crudos y no
  permiten borrado manual de roles, scopes, permisos por scope ni asignaciones.
- `PlatformSettingAdmin` muestra valores de plataforma solo redactados y no
  permite alta ni borrado manual de settings existentes.
- Compliance de datos sensibles trata exportaciones expiradas como terminales:
  no se descargan, no se revocan, una exportacion ya revocada no se revoca de
  nuevo y las exportaciones preparadas vencidas sin hold se normalizan a
  `expirada` antes de rechazar operaciones terminales incompatibles.
- Compliance no expone `evento_inicio` sensible heredado de politicas de
  retencion en API ni admin: nuevas escrituras siguen bloqueadas por dominio y
  los valores heredados se representan redactados. El admin de politicas y
  exportaciones sensibles mantiene cerrados el alta, edicion y borrado manual:
  las mutaciones deben pasar por API, servicios, dominio y auditoria.
- Compliance de datos sensibles permite a `RevisorFiscalExterno` preparar y
  descargar exportaciones sensibles solo dentro de un scope explicito asignado:
  el payload se renderiza con `ScopeAccess`, detalle/descarga/revocacion
  revalidan el scope actual, los intentos fuera de scope se rechazan y los
  usuarios no administradores solo ven/operan sus propias exportaciones.
- La preparacion y revocacion de exportaciones sensibles crean los eventos
  `compliance.exportacion_sensible.prepared` y
  `compliance.exportacion_sensible.revoked` desde el servicio y en la misma
  transaccion que persiste el estado, evitando exportaciones sensibles sin
  auditoria dedicada si falla la escritura del evento.
- CI deterministica verde.
- Savegames preservados read-only.
- Registro de evidencia inicial actualizado.

## Salida

Estado minimo: `resuelto_confirmado` para gobierno base. El PRD Mayo 2026 ya
esta promovido como rector; cualquier nueva decision de producto debe
registrarse como cambio al PRD vigente o bloqueo concreto.

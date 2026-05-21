# Bundles locales de migracion

Esta carpeta es solo una salida local para bundles, reportes y verificaciones
generados durante ejercicios de migracion. Los archivos `.json` no se
versionan porque pueden contener datos legacy, RUTs, cuentas, direcciones,
resultados de staging u otra informacion sensible.

Reglas:

- usa rutas explicitas al ejecutar importadores, runners, rehearsals o
  promociones;
- conserva bundles reales fuera del repo o en almacenamiento seguro autorizado;
- registra evidencia en `docs/product/EVIDENCE_REGISTER_MAYO_2026.md` sin
  incluir datos sensibles completos;
- si se necesita una fixture versionada, debe estar sanitizada y documentada
  como fixture, no como dump operativo.

Los artefactos historicos eliminados del root activo siguen recuperables desde
savegames o historial Git. No reintroducirlos al proyecto vivo.

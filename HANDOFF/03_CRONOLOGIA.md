# Cronologia

## Linea secuencial y lineal del trabajo relevante

| Fecha | Hito | Documento o soporte | Relevancia |
|---|---|---|---|
| 2026-03-15 | Se consolida el set activo del greenfield | [PRD_CANONICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md), ADRs activos | Base canonica de producto, dominio y stack |
| 2026-03-22 a 2026-03-24 | Se endurece el pipeline legacy -> canonical | [importers.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/importers.py), [transformers.py](/D:/Proyectos/LeaseManager/Produccion%201.0/migration/transformers.py) | Idempotencia, `ManualResolution`, resecuenciacion de periodos |
| 2026-04-05 a 2026-04-06 | Se cierra el diseno comunitario y se implementa en backend | [ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md), `backend/*` | El problema comunitario pasa de analisis a implementacion |
| 2026-04-08 a 2026-04-10 | Validacion local PostgreSQL, staging Supabase, rename a `LeaseManager` y separacion de repo | artefactos `v7`, `v9`, Supabase staging, commits `cadde62`, `c6add42` | Queda cerrado el tramo de migracion + naming + repo |
| 2026-04-10 | Commit `5732c78` | `feat: add patrimonio operations workspace and sanitize migration metadata` | Se corrige la exposicion de metadata sensible y se abre la primera superficie real del backoffice |
| 2026-04-11 | Commits `310bc03`, `8bd1eb0`, `302d4d9`, `ce395bb`, `a167a39`, `cb579f1`, `c4b4af9`, `ff89b30` | formularios y workspaces principales | El backoffice cubre `Patrimonio`, `Operacion`, `Contratos`, `Cobranza`, `Conciliacion`, `Contabilidad`, `SII` y `Reporting` |
| 2026-04-11 | Commits `c217219`, `fbe4da1`, `d9b4889`, `9bd8912`, `df44f1b` | navegacion, edicion, UI por rol, RBAC API | La app deja de depender del frontend para permisos |
| 2026-04-11 | Commit `550becf` | `feat: seed demo access profiles for rbac validation` | Se crea el seed reproducible de usuarios/roles/scopes demo |
| 2026-04-11 | Commits `811b8ff` y `bdde843` | scope read + write hardening | Se endurece lectura y escritura por scope para perfiles no-admin |
| 2026-04-11 | Commit `4d2a8dc` | `feat: add audit workspace to backoffice` | `Audit` se abre en frontend |
| 2026-04-12 | Commits `8032c5e`, `97fbe78`, `8c15aed` | `Documentos`, `Canales`, shared inicial | Se abren modulos secundarios y arranca la primera modularizacion real |
| 2026-04-12 | Commits `3a25e6c`, `b5bed98`, `979d5c2`, `0d3c4ec`, `c2d45e8`, `fd9f44a`, `13205cc` | extraccion adicional de workspaces y utilidades | `App.tsx` pasa a un rol mucho mas cercano a orquestador y se consolidan `api.ts`, `shell.tsx` y `view-config.ts` |
| 2026-04-12 | Commits `210579a`, `62dba54`, `64bcafe` | ajustes de UX/RBAC y mensaje explicito de backend faltante | Se cierran huecos finos entre UI visible, permisos y estado de entorno |
| 2026-04-12 | Commits `9e35e66`, `508bbc9`, `b7d68a4`, `b4a3c9b`, `283f6dc`, `abad587`, `01307ec`, `7539e6e` | Docker, Railway, rollout docs, helper Vercel | Se prepara el backend del greenfield para despliegue publico y se deja listo el wiring frontend/backend |
| 2026-04-12 | Runtime actions sobre Vercel y Railway | docs `DEPLOY_*`, `ROLL_OUT_*`, Railway/Vercel UI, health publico | Se conecta Git en ambos providers, Vercel queda con `Root Directory=frontend`, Railway queda con web+worker+Redis y backend publico funcional |
| 2026-04-12 | Commits `3850612` y `9068f7e` | triggers de rebuild conectado | Se fuerzan rebuilds desde `main` para que Vercel y Railway tomen la configuracion final conectada al repo |
| 2026-04-12 | Seed remoto + smoke publico por perfil | `seed_demo_access`, backend publico, frontend publico, Playwright | Se validan `demo-admin`, `demo-operador`, `demo-revisor` y `demo-socio` en el sitio publico con RBAC/UI coherentes |

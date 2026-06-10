# Deploy Frontend Vercel

Estado: activo para el greenfield del root limpio `D:/Proyectos/LeaseManager`.
No ejecutar deploy sin confirmacion explicita del usuario.

## Objetivo

Dejar explícito cómo se despliega el frontend del greenfield sin tocar el proyecto Vercel heredado que todavía arrastra configuración de la app antigua.

## Decisión operativa

- El proyecto Vercel heredado `leasemanager` **no** se reutiliza para el greenfield.
- El frontend React + Vite de `frontend/` se despliega en un proyecto separado:
  - `leasemanager-backoffice`
  - alias productivo actual: [https://leasemanager-backoffice.vercel.app](https://leasemanager-backoffice.vercel.app)

## Motivo

El proyecto `leasemanager` en Vercel sigue configurado con:

- `framework = nextjs`
- `outputDirectory = .next`
- `rootDirectory = null`
- cron jobs legacy en `/api/cron/*`

Eso no corresponde al greenfield activo, cuyo frontend vive en:

- [frontend/package.json](/D:/Proyectos/LeaseManager/frontend/package.json)
- stack `React + TypeScript + Vite`

Reapuntar ese proyecto heredado directamente al frontend habría mezclado dos topologías distintas.

## Flujo recomendado

Desde el root activo, primero ejecutar preflight local. Este comando no toca
Vercel, no lee tokens y no despliega:

```powershell
.\scripts\connect-frontend-to-backend.ps1 -BackendUrl "https://backend-web.example.app"
```

Para configurar `VITE_API_BASE_URL` en Vercel se requiere opt-in explicito:

```powershell
$env:VERCEL_TOKEN = "<token entregado fuera del repo>"
.\scripts\connect-frontend-to-backend.ps1 `
  -BackendUrl "https://backend-web.example.app" `
  -ProjectId "<project-id>" `
  -TeamId "<team-id>" `
  -AuthorizationRef "vercel-link-autorizado-YYYYMMDD" `
  -Apply
```

Para publicar una nueva revision despues del cambio de variable, agregar
`-Redeploy` de forma explicita:

```powershell
.\scripts\connect-frontend-to-backend.ps1 `
  -BackendUrl "https://backend-web.example.app" `
  -ProjectId "<project-id>" `
  -TeamId "<team-id>" `
  -AuthorizationRef "vercel-link-autorizado-YYYYMMDD" `
  -Apply `
  -Redeploy
```

El script no lee `deploy.bat`, `.env`, rutas legacy ni `Produccion 1.0`.
Tampoco ejecuta deploy por defecto.

## Requisitos locales

- Vercel CLI instalada
- sesión válida de Vercel CLI o variable de entorno `VERCEL_TOKEN`
- `frontend/` enlazado al proyecto `leasemanager-backoffice`

## Qué no hacer

- no volver a usar el proyecto `leasemanager` para el greenfield sin una migración explícita de cron jobs, framework y topología;
- no versionar tokens ni credenciales Vercel en scripts;
- no leer tokens desde `deploy.bat`, `.env` o savegames;
- no asumir que el frontend del greenfield comparte la misma forma de despliegue que el root legacy;
- no ejecutar deploy productivo sin `-Apply`, `-Redeploy` y autorización trazable.

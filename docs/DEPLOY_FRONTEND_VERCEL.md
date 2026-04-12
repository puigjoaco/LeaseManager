# Deploy Frontend Vercel

Estado: activo para el greenfield de `Produccion 1.0`

## Objetivo

Dejar explícito cómo se despliega el frontend del greenfield sin tocar el proyecto Vercel heredado que todavía arrastra configuración de la app antigua.

## Decisión operativa

- El proyecto Vercel heredado `leasemanager` **no** se reutiliza para el greenfield.
- El frontend React + Vite de `Produccion 1.0/frontend` se despliega en un proyecto separado:
  - `leasemanager-backoffice`
  - alias productivo actual: [https://leasemanager-backoffice.vercel.app](https://leasemanager-backoffice.vercel.app)

## Motivo

El proyecto `leasemanager` en Vercel sigue configurado con:

- `framework = nextjs`
- `outputDirectory = .next`
- `rootDirectory = null`
- cron jobs legacy en `/api/cron/*`

Eso no corresponde al greenfield activo, cuyo frontend vive en:

- [frontend/package.json](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/package.json)
- stack `React + TypeScript + Vite`

Reapuntar ese proyecto heredado directamente al frontend habría mezclado dos topologías distintas.

## Flujo recomendado

Desde el root activo:

```powershell
.\push-and-deploy.bat "mensaje de commit"
```

Ese script:

1. hace `git add` solo de lo que se le indique;
2. crea el commit;
3. hace `git push`;
4. entra a `frontend/` y ejecuta:

```powershell
vercel --prod --yes --scope joaquins-projects-72185699
```

## Requisitos locales

- Vercel CLI instalada
- sesión válida de Vercel CLI o variable de entorno `VERCEL_TOKEN`
- `frontend/` enlazado al proyecto `leasemanager-backoffice`

## Qué no hacer

- no volver a usar el proyecto `leasemanager` para el greenfield sin una migración explícita de cron jobs, framework y topología;
- no versionar tokens ni credenciales Vercel en scripts;
- no asumir que el frontend del greenfield comparte la misma forma de despliegue que el root legacy.

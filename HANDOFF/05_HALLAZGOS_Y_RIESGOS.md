# Hallazgos y Riesgos

## 1. Hallazgos firmes

### 1.1 Hallazgos de producto e implementación

- El greenfield ya no es un “backend con shell”; ya existe una primera capa usable de backoffice.
- El frontend actual concentra una parte material del estado del proyecto en [App.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/App.tsx).
- El backend ya no depende solo de `IsAuthenticated`; ahora existe una política RBAC explícita en [permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/permissions.py).
- El repo ya tiene seed reproducible de acceso demo en [seed_demo_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/seed_demo_access.py).
- El backend ya tiene una primera capa explícita de filtrado por scope en [scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/scope_access.py).
- Las pruebas nuevas de permisos confirman:
  - `operator` se normaliza a `OperadorDeCartera`;
  - el operador puede mutar módulos operativos;
  - el operador no puede mutar módulos de control;
  - el revisor puede leer control pero no escribir operativo;
  - el `Socio` no puede leer reporting ajeno por la ruta de resumen propio.

### 1.2 Hallazgos de entorno

- Docker local, PostgreSQL, Redis, backend y frontend se levantaron correctamente en el entorno de trabajo.
- El baseline local `v7` se pudo reconstruir sobre PostgreSQL real.
- El sistema local ya soportó pruebas end-to-end sobre:
  - contratos
  - cobranza
  - conciliación
  - contabilidad
  - SII
  - reporting

### 1.3 Hallazgos de seguridad

- La fuga de `DATABASE_URL` completa en artefactos versionados ya fue corregida en el árbol actual.
- La capa de permisos ahora existe tanto en UI como en backend.
- Ya no solo se endureció la lectura: también se cerró una primera tanda de writes/acciones con IDs directos para perfiles no-admin.

## 2. Hallazgos probables

- El siguiente foco de bugs ya no debería estar en crear nuevos módulos base, sino en:
  - validación manual de los perfiles demo ya sembrados;
  - coherencia de permisos por rol en recorridos reales;
  - y huecos residuales de scope en endpoints o formularios menos transitados.
- El README del root activo quedó funcionalmente atrasado respecto del estado real del frontend y del hardening RBAC/scope.
- La mayor parte del trabajo nuevo ya está en `frontend/src/App.tsx`, lo que probablemente vuelva más costoso seguir creciendo ahí sin futura modularización.

## 3. Riesgos técnicos

- El frontend concentra demasiada superficie en un solo archivo `App.tsx`; el riesgo de fricción de mantenimiento ya es real.
- La política RBAC backend ya tiene seed y filtrado inicial por scope, pero todavía puede haber huecos puntuales en módulos secundarios o acciones poco frecuentes.
- La validación de experiencia multiusuario sigue incompleta mientras no se haga la pasada manual completa con los perfiles demo ya sembrados.
- El MCP de Playwright sigue roto por permisos sobre `C:\\Windows\\System32\\.playwright-mcp`.

## 4. Riesgos procesales o de flujo

- Riesgo de que otro thread retome desde un handoff viejo y piense que “falta elegir el siguiente módulo”.
- Riesgo de que alguien asuma que los datos `TEST LOCAL` del entorno están versionados o forman parte del baseline canónico.
- Riesgo de que el dirty tree documental local se interprete como trabajo funcional pendiente del producto, cuando en realidad corresponde a continuidad.

## 5. Riesgos probatorios o de evidencia

- Las respuestas externas literales archivadas siguen siendo válidas para el tramo comunitario, pero no describen el estado actual del backoffice ni del hardening RBAC/scope.
- Las imágenes originales pegadas por el usuario no existen como archivos locales originales; solo quedó su absorción analítica.

## 6. Riesgos narrativos

- README y handoff viejo pueden subestimar el estado real de la UI y del backend.
- El historial reciente tiene varios commits pequeños y muy seguidos; si no se lee la cronología, es fácil perder el hilo de por qué el proyecto dejó de ser “siguiente módulo” y pasó a “hardening operativo”.

## 7. Riesgos estratégicos

- Si no se hace la pasada manual con los usuarios demo ya sembrados, la capa RBAC puede quedar técnicamente correcta pero operativamente poco probada.
- Si no se hace una pasada futura de modularización del frontend, el costo de cambio de `App.tsx` crecerá.
- Si no se publica luego el refresh del handoff/documentación que hoy sigue local, otro thread externo a este workspace puede retomar con una foto desfasada.

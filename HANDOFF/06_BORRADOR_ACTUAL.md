# Borrador Actual

## 1. Situacion actual del “borrador”

No existe un documento unico que reemplace al codigo como entregable principal del tramo actual.

El entregable vigente hoy es una combinacion de:

- set canonico (`PRD`, `ADR`, roadmap);
- implementacion real del backoffice;
- permisos RBAC efectivos en backend;
- seed demo y hardening real de scope;
- topologia publica ya operativa en `Vercel + Railway`;
- smoke publico validado por perfil.

Por eso, para esta etapa, “borrador actual” significa:

- **base de trabajo vigente para continuar el siguiente thread sin reabrir infraestructura ya cerrada**

## 2. Ranking de piezas vigentes hoy

### Ranking 1

[D:/Proyectos/LeaseManager/Produccion 1.0/01_Set_Vigente/PRD_CANONICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md)

Motivo:

- sigue siendo la fuente primaria de producto, dominio y permisos criticos;
- fija actores, restricciones, acceptance y boundary.

### Ranking 2

[D:/Proyectos/LeaseManager/Produccion 1.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md)  
[D:/Proyectos/LeaseManager/Produccion 1.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md)

Motivo:

- siguen siendo la mejor base para decidir continuidad de producto y dependencias.

### Ranking 3

[D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/App.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/App.tsx)  
[D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/api.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/api.ts)  
[D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/shell.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/shell.tsx)  
[D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/view-config.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/view-config.ts)

Motivo:

- hoy mandan si hay duda sobre que ya existe en UI, tabs visibles, wiring con API y comportamiento por rol;
- representan la forma actual del frontend, no la foto vieja del handoff.

### Ranking 4

[D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/AuditWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/AuditWorkspace.tsx)  
[D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/DocumentosWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/DocumentosWorkspace.tsx)  
[D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/CanalesWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/CanalesWorkspace.tsx)  
[D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/ReportingWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/ReportingWorkspace.tsx)  
[D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/ContabilidadWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/ContabilidadWorkspace.tsx)  
[D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/SiiWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/SiiWorkspace.tsx)

Motivo:

- representan la modularizacion efectiva ya conseguida;
- son la referencia practica de las superficies publicas y por rol.

### Ranking 5

[D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/permissions.py)  
[D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/scope_access.py)  
[D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/seed_demo_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/seed_demo_access.py)  
[D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/tests_permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/tests_permissions.py)  
[D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/tests_scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/tests_scope_access.py)

Motivo:

- definen, siembran y prueban el estado actual de RBAC + scope efectivo del backend;
- siguen siendo base obligatoria para cualquier trabajo nuevo sobre permisos finos o validacion por perfil.

### Ranking 6

[D:/Proyectos/LeaseManager/Produccion 1.0/docs/DEPLOY_FRONTEND_VERCEL.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/DEPLOY_FRONTEND_VERCEL.md)  
[D:/Proyectos/LeaseManager/Produccion 1.0/docs/DEPLOY_BACKEND_GREENFIELD.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/DEPLOY_BACKEND_GREENFIELD.md)  
[D:/Proyectos/LeaseManager/Produccion 1.0/docs/ROLL_OUT_BACKEND_FRONTEND.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ROLL_OUT_BACKEND_FRONTEND.md)  
[D:/Proyectos/LeaseManager/Produccion 1.0/backend/railway.web.json](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/railway.web.json)  
[D:/Proyectos/LeaseManager/Produccion 1.0/backend/railway.worker.json](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/railway.worker.json)

Motivo:

- ya no son docs marginales: hoy forman parte de la continuidad real del sistema;
- describen la topologia publica actualmente operativa.

### Ranking 7

[D:/Proyectos/LeaseManager/Produccion 1.0/frontend/src/backoffice/workspaces/ComplianceWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/ComplianceWorkspace.tsx)  
[D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/bootstrap_demo_operational_data.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/bootstrap_demo_operational_data.py)  
[D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/bootstrap_demo_control_baseline.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/bootstrap_demo_control_baseline.py)  
[D:/Proyectos/LeaseManager/Produccion 1.0/backend/core/management/commands/bootstrap_demo_compliance_exports.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/bootstrap_demo_compliance_exports.py)

Motivo:

- representan el ultimo tramo funcional real del proyecto;
- convierten el entorno remoto en algo reproducible y no solo “estado tocado a mano”.

### Ranking 8

[D:/Proyectos/LeaseManager/Produccion 1.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md)

Motivo:

- sigue siendo la base principal para el subdominio comunitario ya cerrado;
- no debe ser reemplazada para ese problema, aunque ya no sea el foco del siguiente paso.

## 3. Estado del borrador/entregable principal

Estado actual:

- no hay un solo documento nuevo pendiente de cierre para esta etapa;
- la base principal de continuidad ya es mayormente codigo + runtime publico;
- el proyecto esta en una fase de consolidacion del stack publico, permisos efectivos y proximo frente funcional.

## 4. Base a usar en el siguiente thread

Usar como base principal, en este orden:

1. [PRD_CANONICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/01_Set_Vigente/PRD_CANONICO.md)
2. [ROADMAP_TECNICO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/ROADMAP_TECNICO.md)
3. [MODULOS_Y_DEPENDENCIAS.md](/D:/Proyectos/LeaseManager/Produccion%201.0/03_Ejecucion_Tecnica/MODULOS_Y_DEPENDENCIAS.md)
4. [App.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/App.tsx)
5. [api.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/api.ts)
6. [shell.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/shell.tsx)
7. [view-config.ts](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/view-config.ts)
8. workspaces del backoffice ya extraidos
9. [permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/permissions.py)
10. [scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/scope_access.py)
11. [seed_demo_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/seed_demo_access.py)
12. [tests_permissions.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/tests_permissions.py)
13. [tests_scope_access.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/tests_scope_access.py)
14. [documentos/scope.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/documentos/scope.py)
15. [canales/scope.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/canales/scope.py)
16. [DEPLOY_FRONTEND_VERCEL.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/DEPLOY_FRONTEND_VERCEL.md)
17. [DEPLOY_BACKEND_GREENFIELD.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/DEPLOY_BACKEND_GREENFIELD.md)
18. [ROLL_OUT_BACKEND_FRONTEND.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ROLL_OUT_BACKEND_FRONTEND.md)
19. [ComplianceWorkspace.tsx](/D:/Proyectos/LeaseManager/Produccion%201.0/frontend/src/backoffice/workspaces/ComplianceWorkspace.tsx)
20. [bootstrap_demo_operational_data.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/bootstrap_demo_operational_data.py)
21. [bootstrap_demo_control_baseline.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/bootstrap_demo_control_baseline.py)
22. [bootstrap_demo_compliance_exports.py](/D:/Proyectos/LeaseManager/Produccion%201.0/backend/core/management/commands/bootstrap_demo_compliance_exports.py)
23. [01_CONTEXTO_MAESTRO.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/01_CONTEXTO_MAESTRO.md)
24. [04_DECISIONES_VIGENTES.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/04_DECISIONES_VIGENTES.md)
25. [03_CRONOLOGIA.md](/D:/Proyectos/LeaseManager/Produccion%201.0/HANDOFF/03_CRONOLOGIA.md)

Para cualquier consulta puntual sobre el dominio comunitario ya cerrado, reinyectar ademas:

26. [ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md](/D:/Proyectos/LeaseManager/Produccion%201.0/docs/ESPECIFICACION_TECNICA_FINAL_COMUNIDADES_RECAUDACION_Y_ATRIBUCION.md)

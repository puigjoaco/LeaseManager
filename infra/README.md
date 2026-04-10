# Infra local

Este directorio levanta la infraestructura aislada del greenfield:

- PostgreSQL en `localhost:5433`
- Redis en `localhost:6379`

Comando recomendado:

```powershell
docker compose -f infra/docker-compose.yml up -d
```

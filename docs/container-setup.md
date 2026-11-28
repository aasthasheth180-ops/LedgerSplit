# Local container smoke test
Run `docker compose --env-file .env.docker up --build -d` and `docker compose --env-file .env.docker ps -a`.
Open http://localhost:8080. Readiness: /api/health/ready. Metrics: /api/metrics.
The local stack uses development mode and HTTP; production requires HTTPS, a random JWT secret, HTTPS trusted origins, secure cookies and a private database. Do not expose metrics publicly in production. Configure Google OAuth client ID and authorized origin separately. Logs omit request bodies and tokens; metrics are per process and reset on restart. Use `docker compose --env-file .env.docker logs --tail=100 backend worker migrate` for diagnosis. Stop with `docker compose --env-file .env.docker down` (do not add -v unless intentionally deleting container data).

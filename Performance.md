# Performance

- Use pagination for list endpoints.
- Cache repeated AI requests where safe.
- Keep Qdrant and Redis reachable before worker startup.
- Avoid duplicate queries in analytics and dashboard code.

# API

- Base path: `/api/v1`
- Auth: `/auth`
- Users: `/users`
- Jobs: `/jobs`
- Learning: `/learning`
- Interviews: `/interviews`
- Notifications: `/notifications`
- Knowledge: `/knowledge`
- Analytics: `/analytics`
- AI: `/ai`
- Assessments: `/assessments`

## Common Responses

- `200`: successful request
- `400`: invalid input or duplicate content
- `401`: missing or invalid auth
- `403`: authenticated but not allowed
- `404`: missing resource
- `422`: validation error
- `429`: rate limited
- `500`: unexpected server failure

## Notes

- AI endpoints route through the central gateway.
- Knowledge uploads queue background work instead of blocking the request.
- Provider health and telemetry live under the AI API group.

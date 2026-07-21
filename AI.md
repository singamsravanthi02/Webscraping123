# AI

- All Gemini traffic goes through the centralized gateway.
- Structured outputs are validated with Pydantic models.
- Prompts live in `backend/app/domain/ai_orchestration/prompts.py`.
- Job, resume, interview, learning, and RAG features reuse the same gateway.

## Providers

- `GEMINI`: primary provider for most structured AI work.
- `NVIDIA`: fallback and fast generation provider.
- `OLLAMA`: local fallback for offline or emergency routing.

## Routing

- Resume, career, and interview analysis prefer Gemini first.
- Question and learning content can fall back to NVIDIA and Ollama.
- Embeddings use the configured embedding provider path in the gateway.

## Operational Notes

- Provider health and telemetry are exposed at `/api/v1/ai/providers`.
- Quota or timeout failures should fall through the gateway, not bubble to the frontend.
- Structured responses are validated before the application uses them.

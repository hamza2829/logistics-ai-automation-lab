from fastapi import FastAPI

from .triage import Decision, MockLLM, Triage, TriageRequest


def create_app(engine: Triage) -> FastAPI:
    app = FastAPI(title="Logistics Triage Lab", version="0.1.0")

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/triage", response_model=Decision)
    def triage(request: TriageRequest) -> Decision:
        return engine.classify(request)

    return app


app = create_app(Triage(MockLLM()))

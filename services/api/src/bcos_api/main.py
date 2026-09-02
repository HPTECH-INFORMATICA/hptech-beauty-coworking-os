from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="HPTECH Beauty Coworking OS API")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "bcos-api",
        }

    return app


app = create_app()

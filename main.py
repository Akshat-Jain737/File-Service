from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from scalar_fastapi import get_scalar_api_reference
from ROUTES.data import data

app = FastAPI(title="Storage Upload Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(data)


@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
        custom_css="""
        .dark-mode {
            --scalar-background-1: #000000 !important;
            --scalar-background-2: #0f0f0f !important;
            --scalar-background-3: #1a1a1a !important;
        }
        """,
    )

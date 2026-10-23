from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.routers.concepts import router as concepts_router
from api.vocab import load_graph

rootpath = os.environ.get("ROOTPATH") or ""
sitepath = os.environ.get("SITEPATH") or "site"

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_graph()
    yield


app = FastAPI(
    title="SoilVoc API",
    description="REST API for the SoilVoc SKOS vocabulary",
    version="0.0.2",
    lifespan=lifespan,
    root_path=rootpath
)

app.include_router(concepts_router, prefix="/api/v1/concepts", tags=["concepts"])


# Mount after the API/docs routes so bundled data and images use the same origin.
app.mount("/", StaticFiles(directory=sitepath, html=True), name="site")

"""FastAPI app for sortgs: Google Scholar search and export."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import search

app = FastAPI(
    title="Citatio / Scholar Export API",
    description="Search Google Scholar and export results as Excel or CSV.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router)


@app.get("/")
def root():
    return {"message": "Citatio API", "docs": "/docs"}

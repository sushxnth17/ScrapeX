"""Compatibility ASGI entrypoint for uvicorn api:app."""

try:
	from .app import app
except ImportError:
	from app import app

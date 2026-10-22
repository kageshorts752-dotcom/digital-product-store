"""Vercel serverless entry point for the Flask digital store.

Vercel turns files under api/ into serverless functions. This module
imports the Flask app from the project root so every route is served by
one function. On Vercel the app seeds SQLite to a writable /tmp copy
(see app.py), because the deployment filesystem is read-only.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import app  # noqa: E402

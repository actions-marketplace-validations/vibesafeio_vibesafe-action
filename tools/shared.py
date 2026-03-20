from __future__ import annotations
"""Shared constants used by multiple VibeSafe tools."""

# Framework conflict map: when key framework is detected, value rule prefixes are false positives
FRAMEWORK_CONFLICTS: dict[str, list[str]] = {
    "flask": ["python.django."],
    "django": ["python.flask."],
    "fastapi": ["python.django.", "python.flask."],
    "express": ["python.django.", "python.flask."],
    "nextjs": ["python.django.", "python.flask."],
    "react": ["python.django.", "python.flask."],
    "vue": ["python.django.", "python.flask."],
    "spring": ["python.flask.", "python.django."],
}

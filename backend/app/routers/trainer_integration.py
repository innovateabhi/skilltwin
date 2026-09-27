"""
Minimal integration instructions.

Your existing project should already have an authenticated-user dependency.
Typical names are `get_current_user` in app.core.dependencies or
app.core.security.

1. Import your existing dependency.
2. Import build_trainer_router.
3. Register the returned router in main.py.

Example:

from app.core.dependencies import get_current_user
from app.routers.trainer import build_trainer_router

trainer_router = build_trainer_router(get_current_user)
app.include_router(trainer_router)

IMPORTANT:
Do not use a second JWT secret or a second login system. Reuse the exact
authentication dependency already used by the Trainee Portal.
"""

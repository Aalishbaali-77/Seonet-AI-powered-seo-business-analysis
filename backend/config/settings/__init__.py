import os

_env = os.getenv("DJANGO_ENV", "development").lower()

if _env == "production":
    from .production import *  # noqa: F403
elif _env == "test":
    from .test import *  # noqa: F403
else:
    from .development import *  # noqa: F403

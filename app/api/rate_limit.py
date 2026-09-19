"""Shared rate-limiting setup (slowapi), used by app.main and any route that needs a limit."""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

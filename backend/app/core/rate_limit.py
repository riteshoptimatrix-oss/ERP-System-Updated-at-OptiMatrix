from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

class DynamicLimiter(Limiter):
    @property
    def enabled(self) -> bool:
        return not settings.is_testing

    @enabled.setter
    def enabled(self, value: bool) -> None:
        pass

# Rate limiter instance (enabled in production/dev, disabled during automated tests)
limiter = DynamicLimiter(
    key_func=get_remote_address,
)

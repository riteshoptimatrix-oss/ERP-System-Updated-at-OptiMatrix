import pytest
from app.core.config import Settings

def test_settings_default_values():
    """
    Test Settings defaults.
    """
    settings = Settings()
    assert settings.PROJECT_NAME == "RG Tech ERP"
    assert settings.PORT == 8000
    assert "http://localhost:3000" in settings.ALLOWED_CORS_ORIGINS


def test_cors_origins_parsing():
    """
    Test parsing CORS origins from comma-separated string or JSON string.
    """
    # From comma-separated string
    s1 = Settings(ALLOWED_CORS_ORIGINS="http://domain1.com, http://domain2.com")
    assert s1.ALLOWED_CORS_ORIGINS == ["http://domain1.com", "http://domain2.com"]

    # From JSON array string
    s2 = Settings(ALLOWED_CORS_ORIGINS='["http://domain3.com"]')
    assert s2.ALLOWED_CORS_ORIGINS == ["http://domain3.com"]

    # From list
    s3 = Settings(ALLOWED_CORS_ORIGINS=["http://domain4.com"])
    assert s3.ALLOWED_CORS_ORIGINS == ["http://domain4.com"]


def test_environment_helpers():
    """
    Test production and test flags.
    """
    s_prod = Settings(ENVIRONMENT="production")
    assert s_prod.is_production is True
    assert s_prod.is_testing is False

    s_test = Settings(ENVIRONMENT="test")
    assert s_test.is_testing is True
    assert s_test.is_production is False

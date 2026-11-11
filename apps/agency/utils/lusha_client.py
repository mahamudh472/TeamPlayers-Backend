import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class LushaError(Exception):
    """Raised for Lusha API failures."""


class LushaClient:
    """
    Minimal client for the Lusha v3 API (prospecting search + contact enrich).
    Search is cheap/free-ish; credits are charged when revealing emails/phones,
    so callers should enrich only the contacts they actually want.
    """
    BASE_URL = "https://api.lusha.com/v3"

    def __init__(self, api_key: str = None):
        key = api_key or getattr(settings, 'LUSHA_API_KEY', '')
        self.api_key = key.strip() if key else ''

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _post(self, path: str, body: dict) -> dict:
        try:
            res = requests.post(
                f"{self.BASE_URL}{path}",
                json=body,
                headers={"api_key": self.api_key, "Content-Type": "application/json"},
                timeout=45,
            )
        except requests.RequestException as e:
            raise LushaError(f"Lusha request failed: {e}")
        if not res.ok:
            raise LushaError(f"Lusha HTTP {res.status_code}: {res.text[:300]}")
        return res.json()

    def search_contacts(self, domain: str, job_titles: list[str], size: int = 10) -> list[dict]:
        """Returns contact previews at a company (by domain) matching any of the given titles."""
        body = {
            "pagination": {"page": 0, "size": max(10, size)},
            "filters": {
                "contacts": {"include": {
                    "jobTitles": job_titles,
                    "existingDataPoints": ["work_email"],
                }},
                "companies": {"include": {"domains": [domain]}},
            },
            "options": {"includePartialProfiles": False, "excludeDnc": True, "maxContactsPerCompany": 5},
        }
        return self._post("/contacts/prospecting", body).get("results", [])

    def enrich_contacts(self, contact_ids: list[str], reveal: tuple = ("emails", "phones")) -> list[dict]:
        if not contact_ids:
            return []
        body = {"ids": [str(i) for i in contact_ids[:100]], "reveal": list(reveal)}
        return self._post("/contacts/enrich", body).get("results", [])

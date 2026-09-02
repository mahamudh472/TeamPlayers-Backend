import time
import logging
import requests
from django.conf import settings
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)

class ApifyError(Exception):
    """Base exception for Apify integration errors."""
    pass

class ApifyClient:
    """
    Client for interacting with the Apify REST API.
    """
    BASE_URL = "https://api.apify.com/v2"

    def __init__(self, api_key: str = None):
        key = api_key or getattr(settings, 'APIFY_API_KEY', '')
        self.api_key = key.strip() if key else ''
        if not self.api_key:
            raise ValidationError({"detail": "Apify API key is not configured in settings."})

    def _get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

    def run_actor(self, actor_id: str, run_input: dict, timeout_secs: int = 300, poll_interval: int = 3) -> list[dict]:
        """
        Runs an Apify actor, polls until completion, and returns the dataset items.
        
        Args:
            actor_id: The ID or name of the actor (e.g. 'apify/google-search-scraper')
            run_input: The input dictionary payload for the actor.
            timeout_secs: Maximum time in seconds to wait for completion.
            poll_interval: Interval between polling checks.

        Returns:
            list[dict]: List of items from the actor's default dataset.
        """
        # Formulate start run URL
        formatted_actor_id = actor_id.replace('/', '~')
        start_url = f"{self.BASE_URL}/acts/{formatted_actor_id}/runs"

        try:
            logger.info(f"Starting Apify actor run: {actor_id}")
            response = requests.post(
                start_url,
                json=run_input,
                headers=self._get_headers(),
                timeout=30
            )
            if not response.ok:
                err_detail = response.text
                try:
                    err_json = response.json()
                    err_detail = err_json.get("error", {}).get("message") or err_detail
                except Exception:
                    pass
                raise ApifyError(f"Apify API returned HTTP {response.status_code}: {err_detail}")

            run_data = response.json().get("data", {})
            run_id = run_data.get("id")
            default_dataset_id = run_data.get("defaultDatasetId")

            if not run_id:
                raise ApifyError("Failed to obtain run ID from Apify response.")

            # Poll for completion
            status_url = f"{self.BASE_URL}/actor-runs/{run_id}"
            start_time = time.time()

            while time.time() - start_time < timeout_secs:
                time.sleep(poll_interval)
                status_res = requests.get(status_url, headers=self._get_headers(), timeout=15)
                if not status_res.ok:
                    continue
                current_run = status_res.json().get("data", {})
                run_status = current_run.get("status")
                dataset_id = current_run.get("defaultDatasetId") or default_dataset_id

                if run_status == "SUCCEEDED":
                    return self.get_dataset_items(dataset_id)
                elif run_status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    # Check if any items were saved before failure
                    if dataset_id:
                        items = self.get_dataset_items(dataset_id)
                        if items:
                            return items
                    raise ApifyError(f"Apify actor run ended with status: {run_status}")

                # If the run has been active for more than 20s and dataset already has items, return them
                if time.time() - start_time > 20 and dataset_id:
                    items = self.get_dataset_items(dataset_id)
                    if items and len(items) > 0:
                        has_data = any(
                            bool(it.get("organicResults")) or bool(it.get("title") or it.get("url") or it.get("name") or it.get("company"))
                            for it in items if isinstance(it, dict)
                        )
                        if has_data:
                            logger.info(f"Retrieved {len(items)} items from Apify dataset while run status is {run_status}.")
                            return items

            # Check if dataset items are available before timing out
            if default_dataset_id:
                items = self.get_dataset_items(default_dataset_id)
                if items:
                    return items

            raise ApifyError(f"Apify actor run timed out after {timeout_secs} seconds.")

        except ApifyError:
            raise
        except requests.RequestException as e:
            logger.exception(f"Apify request failed for actor {actor_id}: {e}")
            raise ApifyError(f"Apify API communication error: {str(e)}")

    def get_dataset_items(self, dataset_id: str, limit: int = 100) -> list[dict]:
        """
        Retrieves items from an Apify dataset.
        """
        dataset_url = f"{self.BASE_URL}/datasets/{dataset_id}/items?clean=true&limit={limit}"
        try:
            res = requests.get(dataset_url, headers=self._get_headers(), timeout=30)
            res.raise_for_status()
            items = res.json()
            if isinstance(items, list):
                return items
            return []
        except requests.RequestException as e:
            logger.exception(f"Failed to fetch Apify dataset items for {dataset_id}: {e}")
            raise ApifyError(f"Failed to fetch dataset items: {str(e)}")

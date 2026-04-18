"""
Shopify Ad Engine — Meta Marketing API Layer
=============================================
Production Meta Marketing API client (Graph API v20.0) for e-commerce ad
campaigns. Designed as the "Post" step of the Create → Edit → Post pipeline.

Credentials loaded from .env at the project root:
  META_ACCESS_TOKEN   — user or system-user access token
  META_AD_ACCOUNT_ID  — ad account ID (with or without "act_" prefix)
  META_PAGE_ID        — Facebook Page ID linked to your store

Optional (for token refresh):
  META_APP_ID
  META_APP_SECRET

Rate limiting: 2-second delay between every API call.
Retry policy:  3 attempts, exponential backoff (5 s, 10 s, 20 s) on
               transient errors (network failures, Meta codes 1/2/4/17/32/613).

CLI usage:
  python scripts/meta_ads_engine.py upload --video exports/product/ad.mp4
  python scripts/meta_ads_engine.py create-campaign --name "Product Launch" --budget 50
  python scripts/meta_ads_engine.py post --creative-id 123 --campaign-id 456
  python scripts/meta_ads_engine.py status
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("meta_ads_engine")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_VERSION = "v20.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

RATE_LIMIT_DELAY = 2          # seconds between every API call
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 5        # seconds; doubles each attempt (5, 10, 20)

# Meta API codes considered transient/retryable
_TRANSIENT_CODES = {1, 2, 4, 17, 32, 613}

# E-commerce campaign objectives supported by this engine
ECOMMERCE_OBJECTIVES = {
    "conversions": "OUTCOME_SALES",
    "traffic":     "OUTCOME_TRAFFIC",
    "awareness":   "OUTCOME_AWARENESS",
    "leads":       "OUTCOME_LEADS",
}

# Conversion events relevant to Shopify stores
SHOPIFY_CONVERSION_EVENTS = {
    "purchase":     "PURCHASE",
    "add_to_cart":  "ADD_TO_CART",
    "view_content": "VIEW_CONTENT",
    "initiate_checkout": "INITIATE_CHECKOUT",
}

# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------

def _load_env() -> dict[str, str]:
    """
    Parse KEY=VALUE pairs from .env at the project root.
    Skips blank lines and comment lines.
    Falls back to os.environ for any key not found in the file.
    """
    env_path = Path(__file__).resolve().parent.parent / ".env"
    creds: dict[str, str] = {}

    if env_path.exists():
        with env_path.open(encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                creds[key.strip()] = value.strip()

    # Overlay with any values already in the process environment
    for key in ("META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID", "META_PAGE_ID",
                "META_APP_ID", "META_APP_SECRET"):
        if key in os.environ and key not in creds:
            creds[key] = os.environ[key]

    return creds


def _require(creds: dict[str, str], key: str) -> str:
    """Return credential value or exit with a clear message."""
    val = creds.get(key, "")
    if not val or val.startswith("INSERT_"):
        log.error("Missing credential: %s — add it to .env", key)
        sys.exit(1)
    return val


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _api_call(
    method: str,
    endpoint: str,
    token: str,
    payload: Optional[dict] = None,
    params: Optional[dict] = None,
) -> dict:
    """
    Execute a Graph API call with retry logic.

    - Injects access_token into every request.
    - Retries on network failures and transient Meta error codes.
    - Raises RuntimeError on non-transient API errors.
    """
    url = f"{BASE_URL}/{endpoint}"
    base_params: dict[str, str] = {"access_token": token}
    if params:
        base_params.update(params)

    last_error: Optional[Exception] = None

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            if method.upper() == "GET":
                resp = requests.get(url, params=base_params, timeout=30)
            elif method.upper() == "POST":
                resp = requests.post(url, params=base_params, data=payload, timeout=30)
            elif method.upper() == "DELETE":
                resp = requests.delete(url, params=base_params, timeout=30)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            body: dict = resp.json()

            if "error" in body:
                err = body["error"]
                code = err.get("code", 0)
                msg = err.get("message", str(err))

                if resp.status_code >= 500 or code in _TRANSIENT_CODES:
                    log.warning(
                        "Transient error (attempt %d/%d) code=%s: %s",
                        attempt, RETRY_ATTEMPTS, code, msg,
                    )
                    last_error = RuntimeError(msg)
                    if attempt < RETRY_ATTEMPTS:
                        time.sleep(RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))
                    continue

                raise RuntimeError(
                    f"Meta API error {code}: {msg}\n"
                    f"Endpoint: {endpoint}\n"
                    f"Payload: {json.dumps(payload, indent=2) if payload else 'N/A'}"
                )

            return body

        except requests.RequestException as exc:
            log.warning("Network error (attempt %d/%d): %s", attempt, RETRY_ATTEMPTS, exc)
            last_error = exc
            if attempt < RETRY_ATTEMPTS:
                time.sleep(RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))

    raise RuntimeError(
        f"All {RETRY_ATTEMPTS} attempts failed for {method} {endpoint}. "
        f"Last error: {last_error}"
    )


# ---------------------------------------------------------------------------
# MetaAdsEngine
# ---------------------------------------------------------------------------

class MetaAdsEngine:
    """
    High-level client for the Meta Marketing API, tuned for Shopify e-commerce.

    All public methods:
      - Enforce a 2-second rate-limit delay before every API call.
      - Return clean Python dicts.
      - Raise RuntimeError with descriptive messages on failure.
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        ad_account_id: Optional[str] = None,
        page_id: Optional[str] = None,
        app_id: Optional[str] = None,
        app_secret: Optional[str] = None,
    ) -> None:
        creds = _load_env()

        self.token: str = access_token or _require(creds, "META_ACCESS_TOKEN")
        raw_account = ad_account_id or _require(creds, "META_AD_ACCOUNT_ID")
        self.ad_account_id: str = (
            raw_account if raw_account.startswith("act_") else f"act_{raw_account}"
        )
        self.page_id: str = page_id or _require(creds, "META_PAGE_ID")
        self.app_id: str = app_id or creds.get("META_APP_ID", "")
        self.app_secret: str = app_secret or creds.get("META_APP_SECRET", "")

        log.info("MetaAdsEngine ready — account: %s", self.ad_account_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _call(
        self,
        method: str,
        endpoint: str,
        payload: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """Rate-limited wrapper around _api_call."""
        time.sleep(RATE_LIMIT_DELAY)
        return _api_call(method, endpoint, self.token, payload=payload, params=params)

    def _paginate(self, endpoint: str, params: Optional[dict] = None) -> list[dict]:
        """
        Follow Meta's cursor-based pagination and collect all results.
        Enforces the rate-limit delay on each page request.
        """
        results: list[dict] = []
        next_url: Optional[str] = None

        while True:
            if next_url:
                time.sleep(RATE_LIMIT_DELAY)
                resp = requests.get(next_url, timeout=30)
                body: dict = resp.json()
            else:
                body = self._call("GET", endpoint, params=params)

            results.extend(body.get("data", []))
            paging = body.get("paging", {})
            next_url = paging.get("next")
            if not next_url:
                break

        return results

    # ------------------------------------------------------------------
    # Video upload
    # ------------------------------------------------------------------

    def upload_video(self, video_path: str, title: Optional[str] = None) -> dict:
        """
        Upload a local video file to the ad account using Meta's resumable
        upload API. Suitable for product demo videos from the exports/ directory.

        Args:
            video_path: Path to the video file (mp4 recommended).
            title: Optional display title for the video asset.

        Returns:
            dict with video_id.
        """
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(f"Video not found: {path}")

        file_size = path.stat().st_size
        display_title = title or path.stem
        log.info("Uploading video: %s (%d bytes)", path.name, file_size)

        # Step 1: Initialize upload session
        url = f"{BASE_URL}/{self.ad_account_id}/advideos"
        time.sleep(RATE_LIMIT_DELAY)

        init_resp = requests.post(
            url,
            params={"access_token": self.token},
            data={
                "upload_phase": "start",
                "file_size": file_size,
                "title": display_title,
            },
            timeout=30,
        )
        init_body: dict = init_resp.json()
        if "error" in init_body:
            err = init_body["error"]
            raise RuntimeError(
                f"Video upload init failed (code {err.get('code')}): {err.get('message')}"
            )

        video_id: str = init_body.get("video_id", "")
        upload_session_id: str = init_body.get("upload_session_id", "")
        start_offset: int = int(init_body.get("start_offset", 0))
        end_offset: int = int(init_body.get("end_offset", file_size))

        if not video_id or not upload_session_id:
            raise RuntimeError(
                f"Video upload init returned unexpected response: {init_body}"
            )

        log.info("Upload session %s initialized, video_id=%s", upload_session_id, video_id)

        # Step 2: Transfer file in chunks
        last_error: Optional[Exception] = None
        with open(path, "rb") as fh:
            while start_offset < file_size:
                chunk_size = end_offset - start_offset
                fh.seek(start_offset)
                chunk = fh.read(chunk_size)

                for attempt in range(1, RETRY_ATTEMPTS + 1):
                    try:
                        time.sleep(RATE_LIMIT_DELAY)
                        transfer_resp = requests.post(
                            url,
                            params={"access_token": self.token},
                            data={
                                "upload_phase": "transfer",
                                "upload_session_id": upload_session_id,
                                "start_offset": start_offset,
                                "video_file_chunk": chunk,
                            },
                            timeout=120,
                        )
                        transfer_body: dict = transfer_resp.json()

                        if "error" in transfer_body:
                            err = transfer_body["error"]
                            code = err.get("code", 0)
                            if transfer_resp.status_code >= 500 or code in _TRANSIENT_CODES:
                                last_error = RuntimeError(err.get("message", str(err)))
                                if attempt < RETRY_ATTEMPTS:
                                    time.sleep(RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))
                                continue
                            raise RuntimeError(
                                f"Video chunk upload failed (code {code}): {err.get('message')}"
                            )

                        start_offset = int(transfer_body.get("start_offset", file_size))
                        end_offset = int(transfer_body.get("end_offset", file_size))
                        log.info("Uploaded chunk, offset now %d/%d", start_offset, file_size)
                        break

                    except requests.RequestException as exc:
                        log.warning(
                            "Network error on chunk attempt %d/%d: %s",
                            attempt, RETRY_ATTEMPTS, exc,
                        )
                        last_error = exc
                        if attempt < RETRY_ATTEMPTS:
                            time.sleep(RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))
                else:
                    raise RuntimeError(
                        f"Video chunk upload failed after {RETRY_ATTEMPTS} attempts. "
                        f"Last error: {last_error}"
                    )

        # Step 3: Finalize
        time.sleep(RATE_LIMIT_DELAY)
        finish_resp = requests.post(
            url,
            params={"access_token": self.token},
            data={
                "upload_phase": "finish",
                "upload_session_id": upload_session_id,
                "title": display_title,
            },
            timeout=30,
        )
        finish_body: dict = finish_resp.json()
        if "error" in finish_body:
            err = finish_body["error"]
            raise RuntimeError(
                f"Video upload finalize failed (code {err.get('code')}): {err.get('message')}"
            )

        log.info("Video upload complete — video_id: %s", video_id)
        return {"video_id": video_id, "title": display_title, "file_size_bytes": file_size}

    # ------------------------------------------------------------------
    # Image upload
    # ------------------------------------------------------------------

    def upload_image(self, image_path: str) -> dict:
        """
        Upload a local image file and return its hash for use in creatives.

        Args:
            image_path: Path to the image file (jpg or png).

        Returns:
            dict with hash, url.
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")

        log.info("Uploading image: %s", path.name)
        url = f"{BASE_URL}/{self.ad_account_id}/adimages"
        time.sleep(RATE_LIMIT_DELAY)

        last_error: Optional[Exception] = None
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                with open(path, "rb") as fh:
                    resp = requests.post(
                        url,
                        params={"access_token": self.token},
                        files={"filename": (path.name, fh, "image/jpeg")},
                        timeout=60,
                    )
                body: dict = resp.json()

                if "error" in body:
                    err = body["error"]
                    code = err.get("code", 0)
                    msg = err.get("message", str(err))
                    if resp.status_code >= 500 or code in _TRANSIENT_CODES:
                        last_error = RuntimeError(msg)
                        if attempt < RETRY_ATTEMPTS:
                            time.sleep(RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))
                        continue
                    raise RuntimeError(f"Image upload failed (code {code}): {msg}")

                images_map: dict = body.get("images", {})
                image_data = next(iter(images_map.values()), {})
                img_hash = image_data.get("hash", "")
                img_url = image_data.get("url", "")
                log.info("Image uploaded — hash: %s", img_hash)
                return {"hash": img_hash, "url": img_url}

            except requests.RequestException as exc:
                log.warning("Network error on upload attempt %d/%d: %s", attempt, RETRY_ATTEMPTS, exc)
                last_error = exc
                if attempt < RETRY_ATTEMPTS:
                    time.sleep(RETRY_BACKOFF_BASE * (2 ** (attempt - 1)))

        raise RuntimeError(
            f"Image upload failed after {RETRY_ATTEMPTS} attempts. Last error: {last_error}"
        )

    # ------------------------------------------------------------------
    # Campaign operations
    # ------------------------------------------------------------------

    def create_campaign(
        self,
        name: str,
        objective: str = "OUTCOME_SALES",
        status: str = "PAUSED",
    ) -> dict:
        """
        Create an e-commerce campaign. Defaults to PAUSED for review before launch.

        Args:
            name: Campaign display name.
            objective: Meta campaign objective. Use one of:
                       OUTCOME_SALES, OUTCOME_TRAFFIC, OUTCOME_AWARENESS, OUTCOME_LEADS.
                       Defaults to OUTCOME_SALES (optimized for Shopify purchases).
            status: ACTIVE or PAUSED.

        Returns:
            dict with id, name, status, objective.
        """
        payload = {
            "name": name,
            "objective": objective,
            "status": status,
            "special_ad_categories": json.dumps([]),  # No special categories for e-commerce
        }
        log.info("Creating campaign: %s (objective=%s)", name, objective)
        body = self._call("POST", f"{self.ad_account_id}/campaigns", payload=payload)
        log.info("Campaign created: %s", body["id"])
        return {"id": body["id"], "name": name, "status": status, "objective": objective}

    def pause_campaign(self, campaign_id: str) -> dict:
        """Set campaign status to PAUSED."""
        log.info("Pausing campaign: %s", campaign_id)
        self._call("POST", campaign_id, payload={"status": "PAUSED"})
        return {"id": campaign_id, "status": "PAUSED"}

    def resume_campaign(self, campaign_id: str) -> dict:
        """Set campaign status to ACTIVE."""
        log.info("Resuming campaign: %s", campaign_id)
        self._call("POST", campaign_id, payload={"status": "ACTIVE"})
        return {"id": campaign_id, "status": "ACTIVE"}

    def get_all_campaigns(self) -> list[dict]:
        """
        Return all campaigns on the ad account with budget and status.

        Returns:
            List of dicts with id, name, status, objective, daily_budget_usd,
            lifetime_budget_usd.
        """
        log.info("Fetching all campaigns for %s ...", self.ad_account_id)
        rows = self._paginate(
            f"{self.ad_account_id}/campaigns",
            params={"fields": "id,name,status,objective,daily_budget,lifetime_budget"},
        )
        campaigns = []
        for row in rows:
            daily_raw = row.get("daily_budget")
            lifetime_raw = row.get("lifetime_budget")
            campaigns.append({
                "id": row["id"],
                "name": row.get("name", ""),
                "status": row.get("status", ""),
                "objective": row.get("objective", ""),
                "daily_budget_usd": (
                    round(int(daily_raw) / 100, 2) if daily_raw else None
                ),
                "lifetime_budget_usd": (
                    round(int(lifetime_raw) / 100, 2) if lifetime_raw else None
                ),
            })
        log.info("Found %d campaigns.", len(campaigns))
        return campaigns

    def duplicate_campaign(self, campaign_id: str, new_name: str) -> dict:
        """
        Duplicate a campaign for A/B testing or scaling.

        Args:
            campaign_id: ID of the source campaign.
            new_name: Name for the copy.

        Returns:
            dict with id, name, source_campaign_id.
        """
        log.info("Duplicating campaign %s as '%s' ...", campaign_id, new_name)
        body = self._call(
            "POST",
            f"{self.ad_account_id}/campaigns/copies",
            payload={"campaign_id": campaign_id, "name": new_name, "status": "PAUSED"},
        )
        new_id = body.get("copied_campaign_id") or body.get("id", "")
        log.info("Duplicated campaign: %s", new_id)
        return {"id": new_id, "name": new_name, "status": "PAUSED", "source_campaign_id": campaign_id}

    # ------------------------------------------------------------------
    # Ad Set operations
    # ------------------------------------------------------------------

    def create_adset(
        self,
        campaign_id: str,
        name: str,
        budget: int,
        destination_url: str,
        conversion_event: str = "PURCHASE",
        product_category: Optional[str] = None,
        targeting: Optional[dict] = None,
        bid_strategy: str = "LOWEST_COST_WITHOUT_CAP",
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        budget_type: str = "lifetime",
    ) -> dict:
        """
        Create an ad set optimized for Shopify conversions.

        Args:
            campaign_id: Parent campaign ID.
            name: Ad set display name.
            budget: Budget in USD (converted to cents internally).
            destination_url: Your Shopify store URL or product page URL.
            conversion_event: Shopify pixel event to optimize for.
                              One of: PURCHASE, ADD_TO_CART, VIEW_CONTENT,
                              INITIATE_CHECKOUT. Defaults to PURCHASE.
            product_category: Optional category tag for targeting (e.g.
                              "apparel", "electronics", "home_goods"). Used to
                              build interest-based targeting when no custom
                              targeting dict is provided.
            targeting: Full targeting spec dict. When omitted, builds a sensible
                       default for the given product_category.
            bid_strategy: Meta bid strategy constant.
            start_time: ISO 8601 string, e.g. "2025-01-01T00:00:00+0000".
            end_time: ISO 8601 string. Required for lifetime budgets.
            budget_type: "lifetime" or "daily".

        Returns:
            dict with id, name, campaign_id, status, budget_usd, conversion_event.
        """
        resolved_targeting = targeting or self._build_ecommerce_targeting(product_category)

        budget_cents = budget * 100
        payload: dict[str, str] = {
            "name": name,
            "campaign_id": campaign_id,
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "OFFSITE_CONVERSIONS",
            "bid_strategy": bid_strategy,
            "targeting": json.dumps(resolved_targeting),
            "promoted_object": json.dumps({
                "pixel_id": "",           # Populated at runtime if META_PIXEL_ID set
                "custom_event_type": conversion_event,
            }),
            "status": "PAUSED",
        }

        # Inject pixel ID if available
        creds = _load_env()
        pixel_id = creds.get("META_PIXEL_ID", "")
        if pixel_id:
            payload["promoted_object"] = json.dumps({
                "pixel_id": pixel_id,
                "custom_event_type": conversion_event,
            })

        if budget_type == "lifetime":
            payload["lifetime_budget"] = str(budget_cents)
        else:
            payload["daily_budget"] = str(budget_cents)

        if start_time:
            payload["start_time"] = start_time
        if end_time:
            payload["end_time"] = end_time

        log.info(
            "Creating ad set: %s (campaign=%s, event=%s)",
            name, campaign_id, conversion_event,
        )
        body = self._call("POST", f"{self.ad_account_id}/adsets", payload=payload)
        log.info("Ad set created: %s", body["id"])
        return {
            "id": body["id"],
            "name": name,
            "campaign_id": campaign_id,
            "status": "PAUSED",
            "budget_usd": budget,
            "budget_type": budget_type,
            "conversion_event": conversion_event,
        }

    def _build_ecommerce_targeting(self, product_category: Optional[str] = None) -> dict:
        """
        Build a sensible default targeting spec for e-commerce campaigns.
        Broad interest groups are added when a product_category hint is given.

        Args:
            product_category: Optional hint — "apparel", "electronics",
                              "home_goods", "beauty", "sports", "food".

        Returns:
            Meta targeting spec dict.
        """
        base: dict = {
            "geo_locations": {"countries": ["US", "CA", "GB", "AU"]},
            "age_min": 18,
            "age_max": 65,
            "publisher_platforms": ["facebook", "instagram"],
            "facebook_positions": ["feed", "reels"],
            "instagram_positions": ["stream", "reels"],
        }

        # Map product categories to broad interest IDs
        # These are stable Meta interest IDs for broad e-commerce audiences
        category_interests: dict[str, list[dict]] = {
            "apparel":     [{"id": "6003107902433", "name": "Fashion"}],
            "electronics": [{"id": "6004854517462", "name": "Consumer Electronics"}],
            "home_goods":  [{"id": "6003020834693", "name": "Home & Garden"}],
            "beauty":      [{"id": "6003397425735", "name": "Beauty"}],
            "sports":      [{"id": "6003483915459", "name": "Sports & Outdoors"}],
            "food":        [{"id": "6003142296148", "name": "Food & Grocery"}],
        }

        if product_category and product_category in category_interests:
            base["interests"] = category_interests[product_category]
            log.info("Applied interest targeting for category: %s", product_category)

        return base

    def get_all_adsets(self, campaign_id: Optional[str] = None) -> list[dict]:
        """
        Return all ad sets, optionally filtered to a single campaign.

        Returns:
            List of dicts with id, name, campaign_id, status, daily_budget_usd,
            lifetime_budget_usd.
        """
        if campaign_id:
            endpoint = f"{campaign_id}/adsets"
            log.info("Fetching ad sets for campaign %s ...", campaign_id)
        else:
            endpoint = f"{self.ad_account_id}/adsets"
            log.info("Fetching all ad sets for account %s ...", self.ad_account_id)

        rows = self._paginate(
            endpoint,
            params={"fields": "id,name,campaign_id,status,daily_budget,lifetime_budget"},
        )
        adsets = []
        for row in rows:
            daily_raw = row.get("daily_budget")
            lifetime_raw = row.get("lifetime_budget")
            adsets.append({
                "id": row["id"],
                "name": row.get("name", ""),
                "campaign_id": row.get("campaign_id", ""),
                "status": row.get("status", ""),
                "daily_budget_usd": (
                    round(int(daily_raw) / 100, 2) if daily_raw else None
                ),
                "lifetime_budget_usd": (
                    round(int(lifetime_raw) / 100, 2) if lifetime_raw else None
                ),
            })
        log.info("Found %d ad sets.", len(adsets))
        return adsets

    # ------------------------------------------------------------------
    # Creative operations
    # ------------------------------------------------------------------

    def create_video_creative(
        self,
        name: str,
        video_id: str,
        destination_url: str,
        message: str = "",
        headline: str = "",
        description: str = "",
        cta_type: str = "SHOP_NOW",
        page_id: Optional[str] = None,
    ) -> dict:
        """
        Create a video ad creative from a previously uploaded video.
        Suited for product demo reels going to a Shopify product or collection page.

        Args:
            name: Creative display name.
            video_id: ID returned by upload_video().
            destination_url: Shopify store or product page URL.
            message: Primary ad copy (body text shown above the video).
            headline: Bold text shown below the video.
            description: Smaller subtext.
            cta_type: Meta CTA constant. Common e-commerce values:
                      SHOP_NOW, LEARN_MORE, GET_OFFER, ORDER_NOW, BUY_NOW.
            page_id: Facebook Page ID. Defaults to engine's page_id.

        Returns:
            dict with id, name.
        """
        resolved_page_id = page_id or self.page_id

        video_data: dict = {
            "video_id": video_id,
            "message": message,
            "title": headline,
            "link_description": description,
            "call_to_action": {
                "type": cta_type,
                "value": {"link": destination_url},
            },
        }

        object_story_spec = {
            "page_id": resolved_page_id,
            "video_data": video_data,
        }

        payload = {
            "name": name,
            "object_story_spec": json.dumps(object_story_spec),
        }

        log.info("Creating video creative: %s", name)
        body = self._call("POST", f"{self.ad_account_id}/adcreatives", payload=payload)
        log.info("Creative created: %s", body["id"])
        return {"id": body["id"], "name": name, "video_id": video_id}

    def create_image_creative(
        self,
        name: str,
        image_hash: str,
        destination_url: str,
        message: str = "",
        headline: str = "",
        description: str = "",
        cta_type: str = "SHOP_NOW",
        page_id: Optional[str] = None,
    ) -> dict:
        """
        Create an image ad creative from a previously uploaded image.

        Args:
            name: Creative display name.
            image_hash: Hash returned by upload_image().
            destination_url: Shopify store or product page URL.
            message: Primary ad copy.
            headline: Bold headline.
            description: Smaller description.
            cta_type: Meta CTA constant (SHOP_NOW, BUY_NOW, LEARN_MORE, etc.).
            page_id: Facebook Page ID. Defaults to engine's page_id.

        Returns:
            dict with id, name.
        """
        resolved_page_id = page_id or self.page_id

        link_data: dict = {
            "link": destination_url,
            "message": message,
            "name": headline,
            "description": description,
            "image_hash": image_hash,
            "call_to_action": {
                "type": cta_type,
                "value": {"link": destination_url},
            },
        }

        object_story_spec = {
            "page_id": resolved_page_id,
            "link_data": link_data,
        }

        payload = {
            "name": name,
            "object_story_spec": json.dumps(object_story_spec),
        }

        log.info("Creating image creative: %s", name)
        body = self._call("POST", f"{self.ad_account_id}/adcreatives", payload=payload)
        log.info("Creative created: %s", body["id"])
        return {"id": body["id"], "name": name, "image_hash": image_hash}

    def create_catalog_creative(
        self,
        name: str,
        catalog_id: str,
        destination_url: str,
        message: str = "",
        cta_type: str = "SHOP_NOW",
        page_id: Optional[str] = None,
    ) -> dict:
        """
        Create a dynamic product catalog ad creative. Meta will automatically
        pull product images, names, and prices from your connected Shopify catalog.

        Args:
            name: Creative display name.
            catalog_id: Meta product catalog ID (from Commerce Manager).
            destination_url: Base store URL; Meta appends product deep links.
            message: Primary ad copy shown above the product carousel.
            cta_type: CTA for each product card (SHOP_NOW, BUY_NOW, etc.).
            page_id: Facebook Page ID. Defaults to engine's page_id.

        Returns:
            dict with id, name, catalog_id.
        """
        resolved_page_id = page_id or self.page_id

        template_data: dict = {
            "message": message or "{{product.name}}",
            "link": destination_url,
            "call_to_action": {
                "type": cta_type,
                "value": {"link": destination_url},
            },
            "format": "CAROUSEL",
        }

        object_story_spec = {
            "page_id": resolved_page_id,
            "template_data": template_data,
        }

        payload = {
            "name": name,
            "object_story_spec": json.dumps(object_story_spec),
            "product_set_id": catalog_id,
        }

        log.info("Creating catalog creative: %s (catalog=%s)", name, catalog_id)
        body = self._call("POST", f"{self.ad_account_id}/adcreatives", payload=payload)
        log.info("Catalog creative created: %s", body["id"])
        return {"id": body["id"], "name": name, "catalog_id": catalog_id}

    # ------------------------------------------------------------------
    # Ad operations
    # ------------------------------------------------------------------

    def create_ad(
        self,
        adset_id: str,
        creative_id: str,
        name: str,
        status: str = "PAUSED",
    ) -> dict:
        """
        Create an ad linking a creative to an ad set.

        Args:
            adset_id: Parent ad set ID.
            creative_id: Creative ID to attach.
            name: Ad display name.
            status: ACTIVE or PAUSED.

        Returns:
            dict with id, name, adset_id, status.
        """
        payload = {
            "name": name,
            "adset_id": adset_id,
            "creative": json.dumps({"creative_id": creative_id}),
            "status": status,
        }
        log.info("Creating ad: %s (adset=%s)", name, adset_id)
        body = self._call("POST", f"{self.ad_account_id}/ads", payload=payload)
        log.info("Ad created: %s", body["id"])
        return {"id": body["id"], "name": name, "adset_id": adset_id, "status": status}

    def get_all_ads(self, adset_id: Optional[str] = None) -> list[dict]:
        """
        Return all ads, optionally filtered to a single ad set.

        Returns:
            List of dicts with id, name, adset_id, status, effective_status.
        """
        if adset_id:
            endpoint = f"{adset_id}/ads"
            log.info("Fetching ads for ad set %s ...", adset_id)
        else:
            endpoint = f"{self.ad_account_id}/ads"
            log.info("Fetching all ads for account %s ...", self.ad_account_id)

        rows = self._paginate(
            endpoint,
            params={"fields": "id,name,adset_id,status,effective_status"},
        )
        ads = [
            {
                "id": row["id"],
                "name": row.get("name", ""),
                "adset_id": row.get("adset_id", ""),
                "status": row.get("status", ""),
                "effective_status": row.get("effective_status", ""),
            }
            for row in rows
        ]
        log.info("Found %d ads.", len(ads))
        return ads

    # ------------------------------------------------------------------
    # Insights / reporting
    # ------------------------------------------------------------------

    def get_insights(
        self,
        object_id: str,
        date_preset: str = "last_7d",
        fields: Optional[list[str]] = None,
    ) -> list[dict]:
        """
        Fetch performance insights for a campaign, ad set, or ad.

        Args:
            object_id: Campaign, ad set, or ad ID.
            date_preset: Meta date preset — today, yesterday, last_7d, last_30d.
            fields: List of insight field names. Defaults to e-commerce KPIs.

        Returns:
            List of insight dicts.
        """
        default_fields = [
            "impressions", "reach", "frequency",
            "clicks", "ctr", "cpc", "cpm",
            "spend", "actions", "cost_per_action_type",
            "purchase_roas",           # Return on ad spend — key Shopify metric
            "website_purchase_roas",   # Specifically for pixel-tracked purchases
        ]
        resolved_fields = fields or default_fields

        rows = self._paginate(
            f"{object_id}/insights",
            params={
                "fields": ",".join(resolved_fields),
                "date_preset": date_preset,
            },
        )
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def refresh_token(self) -> dict:
        """
        Exchange the current short-lived token for a long-lived token (60-day expiry).
        Writes the new token back to META_ACCESS_TOKEN in .env.

        Requires META_APP_ID and META_APP_SECRET to be set.

        Returns:
            dict with access_token, token_type, expires_in.
        """
        if not self.app_id or not self.app_secret:
            raise RuntimeError(
                "META_APP_ID and META_APP_SECRET must be set in .env "
                "to exchange for a long-lived token."
            )

        log.info("Exchanging token for long-lived version ...")
        time.sleep(RATE_LIMIT_DELAY)
        resp = requests.get(
            f"{BASE_URL}/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": self.token,
            },
            timeout=30,
        )
        body: dict = resp.json()

        if "error" in body:
            err = body["error"]
            raise RuntimeError(
                f"Token exchange failed (code {err.get('code')}): {err.get('message')}"
            )

        new_token: str = body.get("access_token", "")
        if not new_token:
            raise RuntimeError("Token exchange returned no access_token.")

        # Update .env in place
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            original = env_path.read_text(encoding="utf-8")
            lines = []
            replaced = False
            for line in original.splitlines():
                if line.startswith("META_ACCESS_TOKEN="):
                    lines.append(f"META_ACCESS_TOKEN={new_token}")
                    replaced = True
                else:
                    lines.append(line)
            if not replaced:
                lines.append(f"META_ACCESS_TOKEN={new_token}")
            env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            log.info("Updated META_ACCESS_TOKEN in .env")

        self.token = new_token
        return {
            "access_token": new_token,
            "token_type": body.get("token_type", "bearer"),
            "expires_in": body.get("expires_in"),
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cmd_upload(args: argparse.Namespace) -> None:
    engine = MetaAdsEngine()
    result = engine.upload_video(args.video, title=args.title)
    print()
    print("=" * 50)
    print("  Video Upload Complete")
    print("=" * 50)
    print(f"  Video ID  : {result['video_id']}")
    print(f"  Title     : {result['title']}")
    print(f"  Size      : {result['file_size_bytes']:,} bytes")
    print()
    print("  Next step: create a creative with this video_id")
    print(f"  python scripts/meta_ads_engine.py create-campaign --name \"My Campaign\" --budget 50")
    print("=" * 50)
    print()


def _cmd_create_campaign(args: argparse.Namespace) -> None:
    engine = MetaAdsEngine()

    # Resolve friendly objective name to Meta constant
    objective = ECOMMERCE_OBJECTIVES.get(args.objective, args.objective)

    campaign = engine.create_campaign(
        name=args.name,
        objective=objective,
        status="PAUSED",
    )

    budget_int = int(args.budget)
    adset = engine.create_adset(
        campaign_id=campaign["id"],
        name=f"{args.name} — Ad Set",
        budget=budget_int,
        destination_url=args.url or "https://your-store.myshopify.com",
        conversion_event=SHOPIFY_CONVERSION_EVENTS.get(
            args.conversion_event, args.conversion_event
        ),
        product_category=args.category,
        budget_type="daily" if args.daily_budget else "lifetime",
    )

    print()
    print("=" * 50)
    print("  Campaign Created (PAUSED)")
    print("=" * 50)
    print(f"  Campaign  : {campaign['name']}")
    print(f"  ID        : {campaign['id']}")
    print(f"  Objective : {campaign['objective']}")
    print(f"  Ad Set    : {adset['name']}")
    print(f"  Ad Set ID : {adset['id']}")
    print(f"  Budget    : ${budget_int} ({'daily' if args.daily_budget else 'lifetime'})")
    print(f"  Optimizing for: {adset['conversion_event']}")
    print()
    print("  Next step: post an ad to this campaign")
    print(f"  python scripts/meta_ads_engine.py post --creative-id <id> --campaign-id {campaign['id']}")
    print("=" * 50)
    print()


def _cmd_post(args: argparse.Namespace) -> None:
    engine = MetaAdsEngine()

    # Get ad sets for this campaign so we can attach the ad
    adsets = engine.get_all_adsets(campaign_id=args.campaign_id)
    if not adsets:
        print(f"No ad sets found for campaign {args.campaign_id}.")
        print("Create one first or use --adset-id to specify an existing ad set.")
        sys.exit(1)

    adset_id = args.adset_id or adsets[0]["id"]

    ad = engine.create_ad(
        adset_id=adset_id,
        creative_id=args.creative_id,
        name=args.name or f"Ad — Creative {args.creative_id}",
        status="PAUSED",
    )

    print()
    print("=" * 50)
    print("  Ad Posted (PAUSED — review before activating)")
    print("=" * 50)
    print(f"  Ad Name   : {ad['name']}")
    print(f"  Ad ID     : {ad['id']}")
    print(f"  Ad Set    : {adset_id}")
    print(f"  Creative  : {args.creative_id}")
    print(f"  Status    : {ad['status']}")
    print()
    print("  To activate: set the campaign and ad set to ACTIVE in Ads Manager.")
    print("=" * 50)
    print()


def _cmd_status(args: argparse.Namespace) -> None:  # noqa: ARG001 — args unused but required by CLI
    engine = MetaAdsEngine()
    campaigns = engine.get_all_campaigns()

    print()
    print("=" * 60)
    print(f"  Shopify Ad Engine — Account {engine.ad_account_id}")
    print(f"  {len(campaigns)} campaign(s)")
    print("=" * 60)

    if not campaigns:
        print("  No campaigns found.")
    else:
        for c in campaigns:
            budget = (
                f"${c['daily_budget_usd']:.2f}/day"
                if c.get("daily_budget_usd")
                else f"${c['lifetime_budget_usd']:.2f} lifetime"
                if c.get("lifetime_budget_usd")
                else "no budget set"
            )
            status_marker = "LIVE" if c["status"] == "ACTIVE" else c["status"]
            print(f"  [{status_marker:<8}] {c['name']}")
            print(f"             ID: {c['id']}  |  {c['objective']}  |  {budget}")

            if args.verbose:
                insights = engine.get_insights(c["id"], date_preset="last_7d")
                if insights:
                    row = insights[0]
                    spend = row.get("spend", "0")
                    impressions = row.get("impressions", "0")
                    clicks = row.get("clicks", "0")
                    ctr = row.get("ctr", "0")
                    print(f"             Last 7d — spend: ${spend}  impressions: {impressions}  clicks: {clicks}  CTR: {ctr}%")

    print("=" * 60)
    print()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="meta_ads_engine",
        description="Shopify Ad Engine — Meta Marketing API layer",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- upload ---
    upload_p = sub.add_parser("upload", help="Upload a video creative from exports/")
    upload_p.add_argument("--video", required=True, help="Path to the video file (e.g. exports/product/ad.mp4)")
    upload_p.add_argument("--title", default=None, help="Optional display title for the video asset")

    # --- create-campaign ---
    create_p = sub.add_parser("create-campaign", help="Create a campaign and ad set")
    create_p.add_argument("--name", required=True, help="Campaign display name")
    create_p.add_argument("--budget", required=True, type=float, help="Budget in USD")
    create_p.add_argument("--url", default=None, help="Shopify store or product page URL")
    create_p.add_argument(
        "--objective",
        default="conversions",
        choices=list(ECOMMERCE_OBJECTIVES.keys()),
        help="Campaign objective (default: conversions)",
    )
    create_p.add_argument(
        "--conversion-event",
        default="purchase",
        choices=list(SHOPIFY_CONVERSION_EVENTS.keys()),
        help="Shopify pixel event to optimize for (default: purchase)",
    )
    create_p.add_argument(
        "--category",
        default=None,
        choices=["apparel", "electronics", "home_goods", "beauty", "sports", "food"],
        help="Product category for interest-based targeting",
    )
    create_p.add_argument(
        "--daily-budget",
        action="store_true",
        help="Treat --budget as a daily budget (default: lifetime)",
    )

    # --- post ---
    post_p = sub.add_parser("post", help="Post an ad creative to a campaign")
    post_p.add_argument("--creative-id", required=True, help="Creative ID to post")
    post_p.add_argument("--campaign-id", required=True, help="Target campaign ID")
    post_p.add_argument("--adset-id", default=None, help="Specific ad set ID (uses first ad set if omitted)")
    post_p.add_argument("--name", default=None, help="Ad display name")

    # --- status ---
    status_p = sub.add_parser("status", help="Show active campaigns and performance")
    status_p.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Include last-7-day performance metrics",
    )

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    handlers = {
        "upload":          _cmd_upload,
        "create-campaign": _cmd_create_campaign,
        "post":            _cmd_post,
        "status":          _cmd_status,
    }

    handler = handlers.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(1)

    try:
        handler(args)
    except FileNotFoundError as exc:
        log.error("%s", exc)
        sys.exit(1)
    except RuntimeError as exc:
        log.error("%s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)


if __name__ == "__main__":
    main()

"""
PostHog client for querying analytics events.

For the daily digest, we query PostHog to get:
- outfit_generated events (with occasion/anchor context)
- outfit_saved events
- outfit_disliked events
- User activity/sessions

Requires POSTHOG_PERSONAL_API_KEY and POSTHOG_PROJECT_ID in .env
Get Personal API Key from: PostHog → Settings → Personal API Keys
Get Project ID from: PostHog → Project Settings
"""

import os
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class PostHogClient:
    """Client for querying PostHog analytics via HogQL API."""

    def __init__(self):
        self.api_key = os.getenv("POSTHOG_PERSONAL_API_KEY")
        self.project_id = os.getenv("POSTHOG_PROJECT_ID")
        self.host = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com")

        if not self.api_key or not self.project_id:
            logger.warning(
                "PostHog not configured. Set POSTHOG_PERSONAL_API_KEY and POSTHOG_PROJECT_ID in .env"
            )

    def is_configured(self) -> bool:
        """Check if PostHog credentials are configured."""
        return bool(self.api_key and self.project_id)

    def _query(self, hogql: str) -> Optional[Dict]:
        """Execute a HogQL query against PostHog."""
        if not self.is_configured():
            logger.error("PostHog not configured - cannot execute query")
            return None

        url = f"{self.host}/api/projects/{self.project_id}/query/"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "query": {
                "kind": "HogQLQuery",
                "query": hogql
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"PostHog query failed: {e}")
            return None

    def get_outfit_events(
        self,
        start_date: datetime,
        end_date: datetime,
        exclude_distinct_ids: List[str] = None
    ) -> Dict[str, List[Dict]]:
        """
        Get all outfit-related events for a date range.

        Returns dict with keys: 'generated', 'saved', 'disliked'
        """
        result = {
            'generated': [],
            'saved': [],
            'disliked': []
        }

        if not self.is_configured():
            return result

        # Format dates for HogQL
        start_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

        # Build exclusion clause
        exclude_clause = ""
        if exclude_distinct_ids:
            ids_str = ", ".join(f"'{id}'" for id in exclude_distinct_ids)
            exclude_clause = f"AND distinct_id NOT IN ({ids_str})"

        # Query outfit_generated events
        generated_query = f"""
        SELECT
            timestamp,
            distinct_id,
            properties.user as user_id,
            properties.mode as mode,
            properties.occasions as occasion,
            properties.anchor_item_ids as anchor_item_ids,
            properties.anchor_item_names as anchor_item_names,
            properties.anchor_count as anchor_count
        FROM events
        WHERE event = 'outfit_generated'
            AND timestamp >= '{start_str}'
            AND timestamp < '{end_str}'
            {exclude_clause}
        ORDER BY timestamp
        """

        generated_result = self._query(generated_query)
        if generated_result and 'results' in generated_result:
            columns = generated_result.get('columns', [])
            for row in generated_result['results']:
                result['generated'].append(dict(zip(columns, row)))

        # Query outfit_saved events
        saved_query = f"""
        SELECT
            timestamp,
            distinct_id,
            properties.user as user_id,
            properties.outfit_id as outfit_id,
            properties.feedback as feedback
        FROM events
        WHERE event = 'outfit_saved'
            AND timestamp >= '{start_str}'
            AND timestamp < '{end_str}'
            {exclude_clause}
        ORDER BY timestamp
        """

        saved_result = self._query(saved_query)
        if saved_result and 'results' in saved_result:
            columns = saved_result.get('columns', [])
            for row in saved_result['results']:
                result['saved'].append(dict(zip(columns, row)))

        # Query outfit_disliked events
        disliked_query = f"""
        SELECT
            timestamp,
            distinct_id,
            properties.user as user_id,
            properties.reason as reason
        FROM events
        WHERE event = 'outfit_disliked'
            AND timestamp >= '{start_str}'
            AND timestamp < '{end_str}'
            {exclude_clause}
        ORDER BY timestamp
        """

        disliked_result = self._query(disliked_query)
        if disliked_result and 'results' in disliked_result:
            columns = disliked_result.get('columns', [])
            for row in disliked_result['results']:
                result['disliked'].append(dict(zip(columns, row)))

        return result

    def get_distinct_ids_for_user(self, user_id: str, limit: int = 5) -> List[str]:
        """
        Get distinct_ids associated with a user.
        Useful for finding your own device IDs to exclude.
        """
        if not self.is_configured():
            return []

        query = f"""
        SELECT DISTINCT distinct_id
        FROM events
        WHERE properties.user = '{user_id}'
        LIMIT {limit}
        """

        result = self._query(query)
        if result and 'results' in result:
            return [row[0] for row in result['results']]
        return []

    def get_active_users(
        self,
        start_date: datetime,
        end_date: datetime,
        exclude_distinct_ids: List[str] = None
    ) -> List[str]:
        """Get list of active users in date range."""
        if not self.is_configured():
            return []

        start_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_date.strftime("%Y-%m-%d %H:%M:%S")

        exclude_clause = ""
        if exclude_distinct_ids:
            ids_str = ", ".join(f"'{id}'" for id in exclude_distinct_ids)
            exclude_clause = f"AND distinct_id NOT IN ({ids_str})"

        query = f"""
        SELECT DISTINCT properties.user as user_id
        FROM events
        WHERE event = 'outfit_generated'
            AND timestamp >= '{start_str}'
            AND timestamp < '{end_str}'
            AND properties.user IS NOT NULL
            AND properties.user != 'default'
            {exclude_clause}
        """

        result = self._query(query)
        if result and 'results' in result:
            return [row[0] for row in result['results'] if row[0]]
        return []

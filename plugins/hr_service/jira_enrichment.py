"""
Jira enrichment: fetch user key (jira_worker_id) from Jira REST API for employees with empty jira_worker_id.
SPEC_HR_SERVICE section 5. GET /rest/api/2/user?username={username}; response key -> jira_worker_id.
"""
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


def enrich_new_employees_jira(employee_ids: List[int]) -> Tuple[int, List[str]]:
    """
    For each employee id, if jira_worker_id is empty, get username from email (part before @),
    call Jira GET /rest/api/2/user?username=..., write key to jira_worker_id.
    Returns (count_enriched, list of error messages).
    """
    if not employee_ids:
        return (0, [])
    try:
        from tools.base import get_plugin_setting
        jira_url = get_plugin_setting("hr_service", "jira_url")
        api_token = get_plugin_setting("hr_service", "api_token")
        if not jira_url or not api_token:
            return (0, ["Jira not configured (jira_url, api_token). Skip enrichment."])
    except Exception as e:
        return (0, [f"Settings error: {e!s}"])
    from api.employees_repository import get_employee_by_id, set_employee_jira_worker_id
    enriched = 0
    errors: List[str] = []
    for eid in employee_ids:
        emp = get_employee_by_id(eid)
        if not emp or emp.get("jira_worker_id"):
            continue
        email = (emp.get("email") or "").strip()
        if not email or "@" not in email:
            errors.append(f"Employee id {eid}: no email, skip Jira lookup")
            continue
        username = email.split("@")[0]
        key = _jira_get_user_key(jira_url.strip().rstrip("/"), api_token, username)
        if key:
            if set_employee_jira_worker_id(eid, key):
                enriched += 1
        else:
            errors.append(f"Employee id {eid} ({email}): Jira user not found or API error")
    return (enriched, errors)


def _jira_get_user_key(base_url: str, api_token: str, username: str) -> str:
    """GET /rest/api/2/user?username=... Return key (JIRAUSER...) or empty string."""
    import httpx
    url = f"{base_url}/rest/api/2/user"
    params = {"username": username}
    try:
        headers = {"Accept": "application/json", "Authorization": f"Bearer {api_token}"}
        with httpx.Client(timeout=15.0) as client:
            r = client.get(url, params=params, headers=headers)
        if r.status_code != 200:
            logger.debug("Jira user lookup %s: %s %s", username, r.status_code, r.text[:200])
            return ""
        data = r.json()
        return (data.get("key") or "").strip()
    except Exception as e:
        logger.warning("Jira user lookup %s: %s", username, e)
        return ""

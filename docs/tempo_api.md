# Tempo Timesheets API Integration Specification

## Overview

This document describes the integration with Tempo Timesheets API for retrieving employee worklogs (time tracking data) from Jira Data Center.

| Parameter | Value |
|-----------|-------|
| **API Version** | Tempo Timesheets REST API v4 |
| **Base URL** | `https://jira.lenta.com` |
| **Authentication** | Bearer Token (Jira Personal Access Token) |
| **SSL** | Self-signed certificate (verification must be disabled) |

---

## Authentication

All requests require the following headers:

```
Authorization: Bearer <JIRA_PERSONAL_ACCESS_TOKEN>
Content-Type: application/json
```

### Token Requirements

- Token must have read access to Tempo worklogs
- Token must have permission to view other users' worklogs (for team reporting)
- Token is created in Jira: **Profile → Personal Access Tokens**

---

## Key Concepts

### Worker ID (userKey)

Tempo API uses Jira's internal user identifier called `userKey` (format: `JIRAUSER*`).

**Important**: Tempo API does NOT accept email or username directly. To retrieve worklogs, you must first obtain the `userKey` via Jira API.

| Field | Example | Description |
|-------|---------|-------------|
| `userKey` | `JIRAUSER94289` | Internal ID for Tempo API |
| `username` | `vladimir.lensky` | Jira login |
| `emailAddress` | `vladimir.lensky@lenta.com` | Employee email |

### Conversion Flow

```
Email → Username → Worker ID (userKey) → Worklogs

Example:
vladimir.lensky@lenta.com → vladimir.lensky → JIRAUSER80735 → [worklogs]
```

---

## API Endpoints

### 1. Get Worker ID by Email/Username

**API**: Jira REST API v2 (not Tempo)

**Purpose**: Convert username (extracted from email) to Worker ID

**Endpoint**: 
```
GET /rest/api/2/user?username={username}
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `username` | string | Yes | User login (email prefix before @) |

**Example Request**:
```bash
curl -k -X GET "https://jira.lenta.com/rest/api/2/user?username=vladimir.lensky" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json"
```

**Example Response**:
```json
{
  "self": "https://jira.lenta.com/rest/api/2/user?username=vladimir.lensky",
  "key": "JIRAUSER80735",
  "name": "vladimir.lensky",
  "emailAddress": "vladimir.lensky@lenta.com",
  "displayName": "Lensky Vladimir",
  "active": true,
  "deleted": false,
  "timeZone": "Europe/Moscow",
  "locale": "ru_RU"
}
```

**Response Field Mapping**:
| Field | Type | Description |
|-------|------|-------------|
| `key` | string | **Worker ID for Tempo API** |
| `name` | string | Username (login) |
| `emailAddress` | string | Employee email |
| `displayName` | string | Full name |
| `active` | boolean | Is account active |
| `deleted` | boolean | Is account deleted |

---

### 2. Get Worklogs by Worker ID

**API**: Tempo Timesheets REST API v4

**Purpose**: Retrieve time tracking records for specified employees and period

**Endpoint**: 
```
POST /rest/tempo-timesheets/4/worklogs/search
```

**Request Body**:
```json
{
  "from": "YYYY-MM-DD",
  "to": "YYYY-MM-DD",
  "worker": ["JIRAUSER*"]
}
```

**Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `from` | string | Yes | Period start date (format: `YYYY-MM-DD`) |
| `to` | string | Yes | Period end date (format: `YYYY-MM-DD`) |
| `worker` | array | No | Array of Worker IDs. If omitted, returns all worklogs |

**Example Request** (single employee):
```bash
curl -k -X POST "https://jira.lenta.com/rest/tempo-timesheets/4/worklogs/search" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "from": "2026-01-12",
    "to": "2026-01-23",
    "worker": ["JIRAUSER80735"]
  }'
```

**Example Request** (multiple employees):
```bash
curl -k -X POST "https://jira.lenta.com/rest/tempo-timesheets/4/worklogs/search" \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "from": "2026-01-01",
    "to": "2026-01-31",
    "worker": ["JIRAUSER80735", "JIRAUSER94289", "JIRAUSER86683"]
  }'
```

**Example Response** (single worklog entry):
```json
{
  "tempoWorklogId": 1678061,
  "worker": "JIRAUSER80735",
  "updater": "JIRAUSER80735",
  "started": "2026-01-12 00:00:00.000",
  "timeSpent": "2h",
  "timeSpentSeconds": 7200,
  "billableSeconds": 7200,
  "comment": "Working on issue DT-9846",
  "issue": {
    "key": "DT-9846",
    "id": 489713,
    "summary": "confluence",
    "projectKey": "DT",
    "projectId": 12228,
    "issueType": "Task",
    "issueStatus": "Analysis",
    "internalIssue": false,
    "iconUrl": "/secure/viewavatar?size=xsmall&avatarId=10318&avatarType=issuetype",
    "reporterKey": "JIRAUSER87790"
  },
  "location": {
    "name": "Default Location",
    "id": 1
  },
  "attributes": {},
  "originTaskId": 489713,
  "originId": 1678061,
  "dateCreated": "2026-01-26 18:33:40.000",
  "dateUpdated": "2026-01-26 18:33:40.000"
}
```

**Response Field Reference**:
| Field | Type | Description |
|-------|------|-------------|
| `tempoWorklogId` | int | Unique worklog entry ID |
| `worker` | string | Worker ID of the employee |
| `updater` | string | Worker ID of last updater |
| `started` | string | Date the time was logged for |
| `timeSpent` | string | Human-readable time (e.g., `2h 30m`) |
| `timeSpentSeconds` | int | Logged time in seconds |
| `billableSeconds` | int | Billable time in seconds |
| `comment` | string | Worklog comment/description |
| `issue.key` | string | Jira issue key |
| `issue.summary` | string | Issue title |
| `issue.projectKey` | string | Project key |
| `issue.issueType` | string | Issue type (Task, Bug, etc.) |
| `issue.issueStatus` | string | Current issue status |
| `dateCreated` | string | Worklog creation timestamp |
| `dateUpdated` | string | Worklog last update timestamp |

---

## Complete Workflow: Email to Worklogs

### Algorithm

```
INPUT: Employee email (e.g., vladimir.lensky@lenta.com)
       Period: date_from, date_to

STEP 1: Extract username from email
        username = email.split("@")[0]
        Result: vladimir.lensky

STEP 2: Get Worker ID from Jira API
        GET /rest/api/2/user?username=vladimir.lensky
        Extract field: response.key
        Result: JIRAUSER80735

STEP 3: Get worklogs from Tempo API
        POST /rest/tempo-timesheets/4/worklogs/search
        Body: { "from": "...", "to": "...", "worker": ["JIRAUSER80735"] }
        Result: Array of worklog entries

STEP 4: Aggregate results
        totalSeconds = SUM(worklog.timeSpentSeconds)
        totalHours = totalSeconds / 3600

OUTPUT: Total hours worked in period
```

### Pseudocode Implementation

```python
def get_worklogs_by_email(email: str, date_from: str, date_to: str) -> dict:
    """
    Get worklogs for employee by email address.
    
    Args:
        email: Employee email (e.g., 'vladimir.lensky@lenta.com')
        date_from: Period start date (YYYY-MM-DD)
        date_to: Period end date (YYYY-MM-DD)
    
    Returns:
        Dictionary with total time and worklog details
    """
    
    # Step 1: Extract username
    username = email.split("@")[0]
    
    # Step 2: Get Worker ID
    jira_response = http.get(
        f"{JIRA_BASE_URL}/rest/api/2/user?username={username}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        },
        verify_ssl=False  # Self-signed certificate
    )
    
    if jira_response.status_code != 200:
        raise Exception(f"User not found: {username}")
    
    worker_id = jira_response.json()["key"]
    
    # Step 3: Get worklogs
    tempo_response = http.post(
        f"{JIRA_BASE_URL}/rest/tempo-timesheets/4/worklogs/search",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "from": date_from,
            "to": date_to,
            "worker": [worker_id]
        },
        verify_ssl=False
    )
    
    worklogs = tempo_response.json()
    
    # Step 4: Aggregate
    total_seconds = sum(wl["timeSpentSeconds"] for wl in worklogs)
    
    return {
        "email": email,
        "worker_id": worker_id,
        "period": {"from": date_from, "to": date_to},
        "total_seconds": total_seconds,
        "total_hours": round(total_seconds / 3600, 2),
        "worklog_count": len(worklogs),
        "worklogs": worklogs
    }
```

---

## Batch Processing: Multiple Employees

### Optimized Approach

For large teams, batch Worker IDs in a single Tempo request:

```python
def get_worklogs_batch(emails: list, date_from: str, date_to: str) -> dict:
    """
    Get worklogs for multiple employees in optimized batch.
    """
    
    # Step 1: Get all Worker IDs
    worker_map = {}  # worker_id -> email
    
    for email in emails:
        username = email.split("@")[0]
        response = http.get(
            f"{JIRA_BASE_URL}/rest/api/2/user?username={username}",
            headers={"Authorization": f"Bearer {TOKEN}"}
        )
        if response.status_code == 200:
            worker_id = response.json()["key"]
            worker_map[worker_id] = email
    
    # Step 2: Single batch request to Tempo
    worker_ids = list(worker_map.keys())
    
    tempo_response = http.post(
        f"{JIRA_BASE_URL}/rest/tempo-timesheets/4/worklogs/search",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "from": date_from,
            "to": date_to,
            "worker": worker_ids  # All workers in one request
        }
    )
    
    worklogs = tempo_response.json()
    
    # Step 3: Aggregate by employee
    results = {email: {"total_seconds": 0, "worklogs": []} for email in emails}
    
    for wl in worklogs:
        worker_id = wl["worker"]
        email = worker_map.get(worker_id)
        if email:
            results[email]["total_seconds"] += wl["timeSpentSeconds"]
            results[email]["worklogs"].append(wl)
    
    # Calculate hours
    for email in results:
        results[email]["total_hours"] = round(
            results[email]["total_seconds"] / 3600, 2
        )
    
    return results
```

### Batch Size Recommendations

| Team Size | Approach |
|-----------|----------|
| 1-20 | Single request with all Worker IDs |
| 21-100 | Batch requests, 20 Worker IDs each |
| 100+ | Batch requests with rate limiting (1 req/sec) |

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Resolution |
|------|---------|------------|
| 200 + `[]` | No worklogs for period or invalid Worker ID | Verify Worker ID and date range |
| 400 | Bad request (invalid JSON or parameters) | Check request body format |
| 401 | Invalid or expired token | Refresh/recreate token |
| 403 | No permission to view worklogs | Request Tempo admin access |
| 404 | Endpoint not found | Verify URL path |
| 405 | Wrong HTTP method | Use POST for `/worklogs/search` |
| 500 | Server error | Retry with exponential backoff |

### Error Response Example

```json
{
  "errorMessages": ["User does not exist: unknown.user"],
  "errors": {}
}
```

### Retry Strategy

```python
def api_request_with_retry(method, url, max_retries=3, **kwargs):
    """Make API request with exponential backoff retry."""
    
    for attempt in range(max_retries):
        try:
            response = http.request(method, url, **kwargs)
            
            if response.status_code == 200:
                return response
            
            if response.status_code in [500, 502, 503, 504]:
                # Server error - retry
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait_time)
                continue
            
            # Client error - don't retry
            response.raise_for_status()
            
        except ConnectionError:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    
    raise Exception(f"Max retries exceeded for {url}")
```

---

## Limitations and Considerations

### Technical Limitations

1. **SSL Certificate**: Self-signed certificate requires disabling verification
   - curl: `-k` flag
   - Python requests: `verify=False`
   - Node.js: `rejectUnauthorized: false`

2. **Worker ID Required**: Tempo API does not accept email/username directly

3. **Date Format**: Strictly `YYYY-MM-DD` (ISO 8601 date only)

4. **Timezone**: All timestamps in response are in `Europe/Moscow`

5. **Response Size**: Large date ranges may return thousands of records

### Permission Requirements

| Action | Required Permission |
|--------|---------------------|
| Get own worklogs | Basic Tempo access |
| Get team worklogs | Team Lead role or Tempo Admin |
| Get all worklogs | Tempo Administrator |

### Rate Limits

- No official rate limits documented
- Recommended: Max 10 requests/second
- For large datasets: Use batch requests with all Worker IDs

---

## Security Considerations

1. **Token Storage**: Never commit tokens to version control
2. **Token Rotation**: Rotate tokens periodically (recommended: 90 days)
3. **Minimum Permissions**: Use tokens with minimum required permissions
4. **Audit Logging**: Log all API access for security audit

---

## Appendix: Quick Reference

### Get Worker ID
```bash
curl -k -X GET \
  "https://jira.lenta.com/rest/api/2/user?username={USERNAME}" \
  -H "Authorization: Bearer {TOKEN}"
```

### Get Worklogs
```bash
curl -k -X POST \
  "https://jira.lenta.com/rest/tempo-timesheets/4/worklogs/search" \
  -H "Authorization: Bearer {TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"from": "YYYY-MM-DD", "to": "YYYY-MM-DD", "worker": ["JIRAUSER*"]}'
```

### Time Conversion
```
seconds → hours: seconds / 3600
seconds → days (8h): seconds / 28800
```

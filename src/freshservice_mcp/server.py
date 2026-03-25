import base64
import logging
import os
import re
import urllib.parse
from enum import Enum, IntEnum
from functools import partial
from typing import Any, Dict, List, Optional, Union

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ValidationError

load_dotenv()


# Set up logging
logging.basicConfig(level=logging.INFO)


# Create MCP INSTANCE
mcp = FastMCP("freshservice_mcp")


# API CREDENTIALS
FRESHSERVICE_DOMAIN = os.getenv("FRESHSERVICE_DOMAIN")
FRESHSERVICE_APIKEY = os.getenv("FRESHSERVICE_APIKEY")

# Configure a safe default AsyncClient factory to ensure timeouts and TLS verification
try:
    _original_async_client = httpx.AsyncClient
    httpx.AsyncClient = partial(
        _original_async_client,
        timeout=httpx.Timeout(10.0, connect=5.0),
        verify=True,
        follow_redirects=False,
    )
except Exception as exc:
    # If httpx internals change, fall back to default behaviour and log at debug level
    logging.debug("httpx AsyncClient monkeypatch failed: %s", exc)


def _sanitize_httpx_error(e: Exception) -> Dict[str, Any]:
    """Return a non-sensitive, minimal error structure for upstream HTTP errors."""
    # Safely extract status_code without swallowing unexpected errors
    resp = getattr(e, "response", None)
    status = getattr(resp, "status_code", None) if resp is not None else None
    return {"error": "Upstream request failed", "status_code": status}


class TicketSource(IntEnum):
    EMAIL = 1
    PORTAL = 2
    PHONE = 3
    CHAT = 7
    YAMMER = 6
    PAGERDUTY = 8
    AWS_CLOUDWATCH = 7
    WALK_UP = 9
    SLACK = 10
    WORKPLACE = 12
    EMPLOYEE_ONBOARDING = 13
    ALERTS = 14
    MS_TEAMS = 15
    EMPLOYEE_OFFBOARDING = 18


class TicketStatus(IntEnum):
    OPEN = 2
    PENDING = 3
    RESOLVED = 4
    CLOSED = 5


class TicketPriority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class ChangeStatus(IntEnum):
    OPEN = 1
    PLANNING = 2
    AWAITING_APPROVAL = 3
    PENDING_RELEASE = 4
    PENDING_REVIEW = 5
    CLOSED = 6


class ChangePriority(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class ChangeImpact(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class ChangeType(IntEnum):
    MINOR = 1
    STANDARD = 2
    MAJOR = 3
    EMERGENCY = 4


class ChangeRisk(IntEnum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4


class UnassignedForOptions(str, Enum):
    FIFTEEN_MIN = "FIFTEEN_MIN"
    THIRTY_MIN = "THIRTY_MIN"
    ONE_HOUR = "ONE_HOUR"
    TWO_HOURS = "TWO_HOURS"
    FOUR_HOURS = "FOUR_HOURS"
    EIGHT_HOURS = "EIGHT_HOURS"
    ONE_DAY = "ONE_DAY"
    TWO_DAYS = "TWO_DAYS"
    THREE_DAYS = "THREE_DAYS"


class FilterTicketsSchema(BaseModel):
    query: str = Field(..., description="Filter query string")
    page: int = Field(1, ge=1, description="Page number")
    workspace_id: Optional[int] = Field(None, description="Workspace ID")


class FilterRequestersSchema(BaseModel):
    query: str = Field(..., description="Filter query string")
    include_agents: bool = Field(False, description="Include agents in results")


class AgentInput(BaseModel):
    first_name: str = Field(..., description="Agent's first name")
    email: Optional[str] = Field(None, description="Agent's email")
    last_name: Optional[str] = Field(None, description="Agent's last name")
    occasional: Optional[bool] = Field(False, description="Is occasional agent")
    job_title: Optional[str] = Field(None, description="Job title")
    work_phone_number: Optional[int] = Field(None, description="Work phone number")
    mobile_phone_number: Optional[int] = Field(None, description="Mobile phone number")


class GroupCreate(BaseModel):
    name: str = Field(..., description="Group name")
    description: Optional[str] = Field(None, description="Group description")
    agent_ids: Optional[List[int]] = Field(None, description="Agent IDs")
    auto_ticket_assign: Optional[bool] = Field(False, description="Auto ticket assign")
    escalate_to: Optional[int] = Field(None, description="Escalate to agent ID")
    unassigned_for: Optional[str] = Field(None, description="Unassigned time frame")


# Pydantic models for key create endpoints
class TicketCreateModel(BaseModel):
    subject: str
    description: str
    source: Union[int, str]
    priority: Union[int, str]
    status: Union[int, str]
    email: Optional[str] = None
    requester_id: Optional[int] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ChangeCreateModel(BaseModel):
    requester_id: int
    subject: str
    description: str
    priority: Union[int, str]
    impact: Union[int, str]
    status: Union[int, str] = 1
    risk: Union[int, str] = 1
    change_type: Union[int, str] = 2
    custom_fields: Optional[Dict[str, Any]] = None
    planning_fields: Optional[Dict[str, Any]] = None


class RequesterCreateModel(BaseModel):
    first_name: str
    primary_email: Optional[str] = None
    secondary_emails: Optional[List[str]] = None
    work_phone_number: Optional[int] = None
    mobile_phone_number: Optional[int] = None
    department_ids: Optional[List[int]] = None
    can_see_all_tickets_from_associated_departments: Optional[bool] = False
    reporting_manager_id: Optional[int] = None
    address: Optional[str] = None
    time_zone: Optional[str] = None
    time_format: Optional[str] = None
    language: Optional[str] = None
    location_id: Optional[int] = None
    background_information: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class AgentCreateModel(BaseModel):
    first_name: str
    email: Optional[str] = None
    last_name: Optional[str] = None
    occasional: Optional[bool] = False
    job_title: Optional[str] = None
    work_phone_number: Optional[int] = None
    mobile_phone_number: Optional[int] = None


def parse_link_header(link_header: str) -> Dict[str, Optional[int]]:
    """Parse Link header from Freshservice API response."""
    pagination_info = {"next": None, "prev": None, "last": None, "per_page": None}

    if not link_header:
        return pagination_info

    # Parse Link header format: <url>; rel="next"
    links = re.findall(r'<([^>]+)>;\s*rel="(\w+)"', link_header)

    for url, rel in links:
        if rel == "next":
            # Extract page number from URL
            page_match = re.search(r"page=(\d+)", url)
            if page_match:
                pagination_info["next"] = int(page_match.group(1))
        elif rel == "prev":
            page_match = re.search(r"page=(\d+)", url)
            if page_match:
                pagination_info["prev"] = int(page_match.group(1))
        elif rel == "last":
            page_match = re.search(r"page=(\d+)", url)
            if page_match:
                pagination_info["last"] = int(page_match.group(1))

    # Extract per_page from current URL
    per_page_match = re.search(r"per_page=(\d+)", link_header)
    if per_page_match:
        pagination_info["per_page"] = int(per_page_match.group(1))

    return pagination_info


# GET TICKET FIELDS
@mcp.tool()
async def get_ticket_fields() -> Dict[str, Any]:
    """Get ticket fields from Freshservice."""
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/tickets/fields"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in get_ticket_fields: %s", e)
            return {"error": "An unexpected error occurred"}


# GET TICKETS
@mcp.tool()
async def get_tickets(
    page: Optional[int] = 1, per_page: Optional[int] = 30
) -> Dict[str, Any]:
    """Get tickets from Freshservice with pagination support."""

    if page < 1:
        return {"error": "Page number must be greater than 0"}

    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/tickets"
    headers = get_auth_headers()

    params = {"page": page, "per_page": per_page}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

            link_header = response.headers.get("Link", "")
            pagination_info = parse_link_header(link_header)

            tickets = response.json()

            return {
                "tickets": tickets,
                "pagination": {
                    "current_page": page,
                    "next_page": pagination_info.get("next"),
                    "prev_page": pagination_info.get("prev"),
                    "per_page": per_page,
                },
            }

        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in get_tickets: %s", e)
            return {"error": "An unexpected error occurred"}


# CREATE TICKET
@mcp.tool()
async def create_ticket(
    subject: str,
    description: str,
    source: Union[int, str],
    priority: Union[int, str],
    status: Union[int, str],
    email: Optional[str] = None,
    requester_id: Optional[int] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a ticket in Freshservice."""

    # Validate input with Pydantic
    try:
        ticket_payload = TicketCreateModel(
            subject=subject,
            description=description,
            source=source,
            priority=priority,
            status=status,
            email=email,
            requester_id=requester_id,
            custom_fields=custom_fields,
        )
    except ValidationError as ve:
        return {"error": "Validation Error", "details": ve.errors()}

    if not ticket_payload.email and not ticket_payload.requester_id:
        return {"error": "Either email or requester_id must be provided"}

    try:
        source_val = int(ticket_payload.source)
        priority_val = int(ticket_payload.priority)
        status_val = int(ticket_payload.status)
    except (ValueError, TypeError):
        return {"error": "Invalid value for source, priority, or status"}

    if (
        source_val not in [e.value for e in TicketSource]
        or priority_val not in [e.value for e in TicketPriority]
        or status_val not in [e.value for e in TicketStatus]
    ):
        return {"error": "Invalid value for source, priority, or status"}

    data = {
        "subject": subject,
        "description": description,
        "source": source_val,
        "priority": priority_val,
        "status": status_val,
    }

    if ticket_payload.email:
        data["email"] = ticket_payload.email
    if ticket_payload.requester_id:
        data["requester_id"] = ticket_payload.requester_id

    if ticket_payload.custom_fields:
        data["custom_fields"] = ticket_payload.custom_fields

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/tickets"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()

            response_data = response.json()
            return f"Ticket created successfully: {response_data}"

        except httpx.HTTPStatusError as e:
            # Return a sanitized error; include a minimal validation summary for 400 responses
            resp = getattr(e, "response", None)
            if resp is not None and getattr(resp, "status_code", None) == 400:
                try:
                    err_json = resp.json()
                except ValueError:
                    return _sanitize_httpx_error(e)

                if isinstance(err_json, dict) and "errors" in err_json:
                    errors = err_json.get("errors")
                    if isinstance(errors, dict):
                        details = {"fields": list(errors.keys())}
                    elif isinstance(errors, list):
                        details = {"count": len(errors)}
                    else:
                        details = {"type": type(errors).__name__}
                    base = _sanitize_httpx_error(e)
                    base.update({"validation": details})
                    return base

            return _sanitize_httpx_error(e)
        except Exception as exc:
            logging.debug("Unexpected error creating ticket: %s", exc)
            return {"error": "An unexpected error occurred"}


# FILTER TICKETS
@mcp.tool()
async def filter_tickets(
    query: str, page: int = 1, workspace_id: Optional[int] = None
) -> Dict[str, Any]:
    """Filter the tickets in Freshservice.

    Args:
        query: Filter query string (e.g., "status:2 AND priority:1")
               Note: Some Freshservice endpoints may require queries to be wrapped in double quotes.
               If you get 500 errors, try wrapping your query in double quotes: "your_query_here"
        page: Page number (default: 1)
        workspace_id: Optional workspace ID filter
    """
    # Freshservice API requires the query to be wrapped in double quotes
    encoded_query = urllib.parse.quote(f'"{query}"')
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/tickets/filter?query={encoded_query}&page={page}"

    if workspace_id is not None:
        url += f"&workspace_id={workspace_id}"

    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in filter_tickets: %s", e)
            return {"error": "An unexpected error occurred"}


# UPDATE TICKET
@mcp.tool()
async def update_ticket(ticket_id: int, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing ticket in Freshservice."""

    if not updates:
        return {"error": "No updates provided"}

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/tickets/{ticket_id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=updates)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in update_ticket: %s", e)
            return {"error": "An unexpected error occurred"}


# DELETE TICKET
@mcp.tool()
async def delete_ticket(ticket_id: int) -> Dict[str, Any]:
    """Delete a ticket in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/tickets/{ticket_id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()

            return {
                "success": True,
                "message": f"Ticket {ticket_id} deleted successfully",
            }
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in delete_ticket: %s", e)
            return {"error": "An unexpected error occurred"}


# GET TICKET BY ID
@mcp.tool()
async def get_ticket_by_id(ticket_id: int) -> Dict[str, Any]:
    """Get a ticket by its ID in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/tickets/{ticket_id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in get_ticket_by_id: %s", e)
            return {"error": "An unexpected error occurred"}


# GET CHANGES
@mcp.tool()
async def get_changes(
    page: Optional[int] = 1,
    per_page: Optional[int] = 30,
    query: Optional[str] = None,
    view: Optional[str] = None,
    sort: Optional[str] = None,
    order_by: Optional[str] = None,
    updated_since: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Get all changes from Freshservice with pagination and filtering support.

    Args:
        page: Page number (default: 1)
        per_page: Number of items per page (1-100, default: 30)
        query: Filter query string (e.g., "priority:4 OR priority:3", "status:2 AND priority:1")
               **IMPORTANT**: Query must be wrapped in double quotes for filtering to work!
               Examples: "status:3", "approval_status:1 AND status:<6", "planned_start_date:>'2025-07-14'"
        view: Accepts the name or ID of views (e.g., 'my_open', 'unassigned')
        sort: Field to sort by (e.g., 'priority', 'created_at')
        order_by: Sort order ('asc' or 'desc', default: 'desc')
        updated_since: Changes updated since date (ISO format: '2024-10-19T02:00:00Z')
        workspace_id: Filter by workspace ID (0 for all workspaces)

    Query examples:
        - "priority:4 OR priority:3" - Urgent and High priority changes
        - "status:2 AND priority:1" - Planning changes with low priority
        - "approval_status:1" - Approved changes
        - "planned_end_date:<'2025-01-14'" - Changes with end date before specified date

    Note: Query and view parameters cannot be used together
    """

    if page < 1:
        return {"error": "Page number must be greater than 0"}

    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/changes"

    params = {"page": page, "per_page": per_page}

    if query:
        params["query"] = query
    if view:
        params["view"] = view
    if sort:
        params["sort"] = sort
    if order_by:
        params["order_by"] = order_by
    if updated_since:
        params["updated_since"] = updated_since
    if workspace_id is not None:
        params["workspace_id"] = workspace_id

    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

            link_header = response.headers.get("Link", "")
            pagination_info = parse_link_header(link_header)

            changes = response.json()

            return {
                "changes": changes,
                "pagination": {
                    "current_page": page,
                    "next_page": pagination_info.get("next"),
                    "prev_page": pagination_info.get("prev"),
                    "per_page": per_page,
                },
            }
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in get_changes: %s", e)
            return {"error": "An unexpected error occurred"}


# FILTER CHANGES
@mcp.tool()
async def filter_changes(
    query: str,
    page: int = 1,
    per_page: int = 30,
    sort: Optional[str] = None,
    order_by: Optional[str] = None,
    workspace_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Filter changes in Freshservice based on a query.

    Args:
        query: Filter query string (e.g., "status:2 AND priority:1" or "approval_status:1 AND planned_end_date:<'2025-01-14' AND status:<6")
               **CRITICAL**: Query must be wrapped in double quotes for filtering to work!
               Without quotes: status:3 → 500 Internal Server Error
               With quotes: "status:3" → Works perfectly
        page: Page number (default: 1)
        per_page: Number of items per page (1-100, default: 30)
        sort: Field to sort by
        order_by: Sort order ('asc' or 'desc')
        workspace_id: Optional workspace ID filter
    """

    # Use the main get_changes function with query parameter
    # This is the correct approach since /api/v2/changes/filter doesn't exist
    return await get_changes(
        page=page,
        per_page=per_page,
        query=query,
        sort=sort,
        order_by=order_by,
        workspace_id=workspace_id,
    )


# GET CHANGE BY ID
@mcp.tool()
async def get_change_by_id(change_id: int) -> Dict[str, Any]:
    """Get a change by its ID in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/changes/{change_id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in get_requested_items: %s", e)
            return {"error": "An unexpected error occurred"}


# CREATE CHANGE
@mcp.tool()
async def create_change(
    requester_id: int,
    subject: str,
    description: str,
    priority: Union[int, str],
    impact: Union[int, str],
    status: Union[int, str] = 1,
    risk: Union[int, str] = 1,
    change_type: Union[int, str] = 2,
    custom_fields: Optional[Dict[str, Any]] = None,
    planning_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a new change in Freshservice."""

    # Validate input with Pydantic
    try:
        change_payload = ChangeCreateModel(
            requester_id=requester_id,
            subject=subject,
            description=description,
            priority=priority,
            impact=impact,
            status=status,
            risk=risk,
            change_type=change_type,
            custom_fields=custom_fields,
            planning_fields=planning_fields,
        )
    except ValidationError as ve:
        return {"error": "Validation Error", "details": ve.errors()}

    try:
        priority_val = int(change_payload.priority)
        impact_val = int(change_payload.impact)
        status_val = int(change_payload.status)
        risk_val = int(change_payload.risk)
        change_type_val = int(change_payload.change_type)
    except (ValueError, TypeError):
        return {
            "error": "Invalid value for priority, impact, status, risk, or change_type"
        }

    if (
        priority_val not in [e.value for e in ChangePriority]
        or impact_val not in [e.value for e in ChangeImpact]
        or status_val not in [e.value for e in ChangeStatus]
        or risk_val not in [e.value for e in ChangeRisk]
        or change_type_val not in [e.value for e in ChangeType]
    ):
        return {
            "error": "Invalid value for priority, impact, status, risk, or change_type"
        }

    data = {
        "requester_id": change_payload.requester_id,
        "subject": change_payload.subject,
        "description": change_payload.description,
        "priority": priority_val,
        "impact": impact_val,
        "status": status_val,
        "risk": risk_val,
        "change_type": change_type_val,
    }

    if change_payload.custom_fields:
        data["custom_fields"] = change_payload.custom_fields

    if change_payload.planning_fields:
        data["planning_fields"] = change_payload.planning_fields

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/changes"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in create_service_request: %s", e)
            return {"error": "An unexpected error occurred"}


# UPDATE CHANGE
@mcp.tool()
async def update_change(
    change_id: int, change_fields: Dict[str, Any]
) -> Dict[str, Any]:
    """Update an existing change in Freshservice.

    To update the change result explanation when closing a change:
    change_fields = {
        "status": 6,  # Closed
        "custom_fields": {
            "change_result_explanation": "Your explanation here"
        }
    }
    """
    if not change_fields:
        return {"error": "No fields provided for update"}

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/changes/{change_id}"
    headers = get_auth_headers()

    # Extract special fields
    custom_fields = change_fields.pop("custom_fields", {})
    planning_fields = change_fields.pop("planning_fields", {})

    update_data = {}

    # Add regular fields
    for field, value in change_fields.items():
        update_data[field] = value

    # Add custom fields if present
    if custom_fields:
        update_data["custom_fields"] = custom_fields

    # Add planning fields if present
    if planning_fields:
        update_data["planning_fields"] = planning_fields

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=update_data)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in get_all_products: %s", e)
            return {"error": "An unexpected error occurred"}


# CLOSE CHANGE
@mcp.tool()
async def close_change(
    change_id: int,
    change_result_explanation: str,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Close a change and provide the result explanation.
    This is a convenience function that updates status to Closed and sets the result explanation."""

    update_data = {
        "status": ChangeStatus.CLOSED.value,
        "custom_fields": {"change_result_explanation": change_result_explanation},
    }

    # Merge additional custom fields if provided
    if custom_fields:
        update_data["custom_fields"].update(custom_fields)

    return await update_change(change_id, update_data)


# DELETE CHANGE
@mcp.tool()
async def delete_change(change_id: int) -> Dict[str, Any]:
    """Delete a change in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/changes/{change_id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=headers)
            response.raise_for_status()

            return {
                "success": True,
                "message": f"Change {change_id} deleted successfully",
            }
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in get_products_by_id: %s", e)
            return {"error": "An unexpected error occurred"}


# MOVE CHANGE
@mcp.tool()
async def move_change(change_id: int, workspace_id: int) -> Dict[str, Any]:
    """Move a change to another workspace."""
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/changes/{change_id}/move_workspace"
    headers = get_auth_headers()
    data = {"workspace_id": workspace_id}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# LIST CHANGE APPROVALS
@mcp.tool()
async def list_change_approvals(change_id: int) -> Dict[str, Any]:
    """List all change approvals."""
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/changes/{change_id}/approvals"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET CHANGE TASKS
@mcp.tool()
async def get_change_tasks(change_id: int) -> Dict[str, Any]:
    """Get tasks for a change."""
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/changes/{change_id}/tasks"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# CREATE CHANGE NOTE
@mcp.tool()
async def create_change_note(change_id: int, body: str) -> Dict[str, Any]:
    """Add a note to a change."""
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/changes/{change_id}/notes"
    headers = get_auth_headers()
    data = {"body": body}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# CREATE TICKET NOTE
@mcp.tool()
async def create_ticket_note(ticket_id: int, body: str) -> Dict[str, Any]:
    """Add a note to a ticket."""
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/tickets/{ticket_id}/notes"
    headers = get_auth_headers()
    data = {"body": body}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# SEND TICKET REPLY
@mcp.tool()
async def send_ticket_reply(
    ticket_id: int,
    body: str,
    from_email: Optional[str] = None,
    user_id: Optional[int] = None,
    cc_emails: Optional[Union[str, List[str]]] = None,
    private: bool = False,
) -> Dict[str, Any]:
    """Send a reply to a ticket."""
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/tickets/{ticket_id}/conversations"
    headers = get_auth_headers()

    data = {"body": body, "private": private}

    if from_email:
        data["from_email"] = from_email
    if user_id:
        data["user_id"] = user_id
    if cc_emails:
        data["cc_emails"] = cc_emails if isinstance(cc_emails, list) else [cc_emails]

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# LIST ALL TICKET CONVERSATION
@mcp.tool()
async def list_all_ticket_conversation(ticket_id: int) -> Dict[str, Any]:
    """List all conversations for a ticket."""
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/tickets/{ticket_id}/conversations"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# UPDATE TICKET CONVERSATION
@mcp.tool()
async def update_ticket_conversation(
    conversation_id: int, updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Update a ticket conversation."""
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/conversations/{conversation_id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=updates)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# LIST SERVICE ITEMS
@mcp.tool()
async def list_service_items(
    page: Optional[int] = 1, per_page: Optional[int] = 30
) -> Dict[str, Any]:
    """Get list of service items from Freshservice."""

    if page < 1:
        return {"error": "Page number must be greater than 0"}

    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/service_items"
    headers = get_auth_headers()

    params = {"page": page, "per_page": per_page}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

            link_header = response.headers.get("Link", "")
            pagination_info = parse_link_header(link_header)

            service_items = response.json()

            return {
                "service_items": service_items,
                "pagination": {
                    "current_page": page,
                    "next_page": pagination_info.get("next"),
                    "prev_page": pagination_info.get("prev"),
                    "per_page": per_page,
                },
            }

        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in update_product: %s", e)
            return {"error": "An unexpected error occurred"}


# GET REQUESTED ITEMS
@mcp.tool()
async def get_requested_items(ticket_id: int) -> dict:
    """Fetch requested items for a specific ticket if the ticket is a service request."""

    async def get_ticket(ticket_id: int) -> dict:
        """Fetch ticket details by ticket ID to check the ticket type."""
        url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/tickets/{ticket_id}"
        headers = get_auth_headers()

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                return _sanitize_httpx_error(e)

    # Step 1: Check if the ticket is a service request
    ticket_check = await get_ticket(ticket_id)

    if not ticket_check.get("success", False):
        return ticket_check  # If ticket fetching or type check failed, return the error message

    # Step 2: If the ticket is a service request, fetch the requested items
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/tickets/{ticket_id}/requested_items"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# CREATE SERVICE REQUEST
@mcp.tool()
async def create_service_request(
    display_id: int, email: str, requested_for: Optional[str] = None, quantity: int = 1
) -> dict:
    """Create a service request in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/service_requests"
    headers = get_auth_headers()

    payload = {"display_id": display_id, "email": email, "quantity": quantity}

    if requested_for:
        payload["requested_for"] = requested_for

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET ALL PRODUCTS
@mcp.tool()
async def get_all_products(
    page: Optional[int] = 1, per_page: Optional[int] = 30
) -> Dict[str, Any]:
    """Get all products from Freshservice."""

    if page < 1:
        return {"error": "Page number must be greater than 0"}

    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/products"
    headers = get_auth_headers()

    params = {"page": page, "per_page": per_page}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

            link_header = response.headers.get("Link", "")
            pagination_info = parse_link_header(link_header)

            products = response.json()

            return {
                "products": products,
                "pagination": {
                    "current_page": page,
                    "next_page": pagination_info.get("next"),
                    "prev_page": pagination_info.get("prev"),
                    "per_page": per_page,
                },
            }

        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in get_all_products: %s", e)
            return {"error": "An unexpected error occurred"}


# GET PRODUCTS BY ID
@mcp.tool()
async def get_products_by_id(id: int) -> Dict[str, Any]:
    """Get a product by its ID in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/products/{id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# CREATE PRODUCT
@mcp.tool()
async def create_product(
    name: str,
    asset_type_id: int,
    manufacturer: Optional[str] = None,
    status: Union[int, str] = 1,
    mode_of_procurement: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a product in Freshservice."""

    try:
        status_val = int(status)
    except ValueError:
        return {"error": "Invalid value for status"}

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/products"
    headers = get_auth_headers()

    payload = {"name": name, "asset_type_id": asset_type_id, "status": status_val}

    if manufacturer:
        payload["manufacturer"] = manufacturer
    if mode_of_procurement:
        payload["mode_of_procurement"] = mode_of_procurement
    if description:
        payload["description"] = description

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# UPDATE PRODUCT
@mcp.tool()
async def update_product(
    id: int,
    name: Optional[str] = None,
    asset_type_id: Optional[int] = None,
    manufacturer: Optional[str] = None,
    status: Union[int, str] = 1,
    mode_of_procurement: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Update a product in Freshservice."""

    try:
        status_val = int(status)
    except ValueError:
        return {"error": "Invalid value for status"}

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/products/{id}"
    headers = get_auth_headers()

    payload = {"name": name, "asset_type_id": asset_type_id, "status": status_val}

    if manufacturer:
        payload["manufacturer"] = manufacturer
    if mode_of_procurement:
        payload["mode_of_procurement"] = mode_of_procurement
    if description:
        payload["description"] = description

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=payload)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# CREATE REQUESTER
@mcp.tool()
async def create_requester(
    first_name: str,
    primary_email: Optional[str] = None,
    secondary_emails: Optional[List[str]] = None,
    work_phone_number: Optional[int] = None,
    mobile_phone_number: Optional[int] = None,
    department_ids: Optional[List[int]] = None,
    can_see_all_tickets_from_associated_departments: Optional[bool] = False,
    reporting_manager_id: Optional[int] = None,
    address: Optional[str] = None,
    time_zone: Optional[str] = None,
    time_format: Optional[str] = None,
    language: Optional[str] = None,
    location_id: Optional[int] = None,
    background_information: Optional[str] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a requester in Freshservice."""

    # Validate input with Pydantic
    try:
        requester_payload = RequesterCreateModel(
            first_name=first_name,
            primary_email=primary_email,
            secondary_emails=secondary_emails,
            work_phone_number=work_phone_number,
            mobile_phone_number=mobile_phone_number,
            department_ids=department_ids,
            can_see_all_tickets_from_associated_departments=can_see_all_tickets_from_associated_departments,
            reporting_manager_id=reporting_manager_id,
            address=address,
            time_zone=time_zone,
            time_format=time_format,
            language=language,
            location_id=location_id,
            background_information=background_information,
            custom_fields=custom_fields,
        )
    except ValidationError as ve:
        return {"error": "Validation Error", "details": ve.errors()}

    if not (
        requester_payload.primary_email
        or requester_payload.work_phone_number
        or requester_payload.mobile_phone_number
    ):
        return {
            "error": "At least one of 'primary_email', 'work_phone_number', or 'mobile_phone_number' is required."
        }

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/requesters"
    headers = get_auth_headers()

    payload: Dict[str, Any] = requester_payload.dict(exclude_none=True)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET REQUESTER ID
@mcp.tool()
async def get_requester_id(id: int) -> Dict[str, Any]:
    """Get a requester by its ID in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/requesters/{id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# UPDATE REQUESTER
@mcp.tool()
async def update_requester(
    requester_id: int,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    job_title: Optional[str] = None,
    primary_email: Optional[str] = None,
    secondary_emails: Optional[List[str]] = None,
    work_phone_number: Optional[int] = None,
    mobile_phone_number: Optional[int] = None,
    department_ids: Optional[List[int]] = None,
    can_see_all_tickets_from_associated_departments: Optional[bool] = False,
    reporting_manager_id: Optional[int] = None,
    address: Optional[str] = None,
    time_zone: Optional[str] = None,
    time_format: Optional[str] = None,
    language: Optional[str] = None,
    location_id: Optional[int] = None,
    background_information: Optional[str] = None,
    custom_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Update a requester in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/requesters/{requester_id}"
    headers = get_auth_headers()

    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "job_title": job_title,
        "primary_email": primary_email,
        "secondary_emails": secondary_emails,
        "work_phone_number": work_phone_number,
        "mobile_phone_number": mobile_phone_number,
        "department_ids": department_ids,
        "can_see_all_tickets_from_associated_departments": can_see_all_tickets_from_associated_departments,
        "reporting_manager_id": reporting_manager_id,
        "address": address,
        "time_zone": time_zone,
        "time_format": time_format,
        "language": language,
        "location_id": location_id,
        "background_information": background_information,
        "custom_fields": custom_fields,
    }

    data = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=data)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# LIST ALL REQUESTER FIELDS
@mcp.tool()
async def list_all_requester_fields() -> Dict[str, Any]:
    """Get all requester fields from Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/requesters/fields"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# FILTER REQUESTERS
@mcp.tool()
async def filter_requesters(query: str, include_agents: bool = False) -> Dict[str, Any]:
    """Filter requesters in Freshservice."""

    # Freshservice API requires the query to be wrapped in double quotes
    encoded_query = urllib.parse.quote(f'"{query}"')
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/requesters/filter?query={encoded_query}&include_agents={str(include_agents).lower()}"

    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# CREATE AGENT
@mcp.tool()
async def create_agent(
    first_name: str,
    email: str = None,
    last_name: Optional[str] = None,
    occasional: Optional[bool] = False,
    job_title: Optional[str] = None,
    work_phone_number: Optional[int] = None,
    mobile_phone_number: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a new agent in Freshservice."""

    # Validate input with Pydantic
    try:
        agent_payload = AgentCreateModel(
            first_name=first_name,
            email=email,
            last_name=last_name,
            occasional=occasional,
            job_title=job_title,
            work_phone_number=work_phone_number,
            mobile_phone_number=mobile_phone_number,
        )
    except ValidationError as ve:
        return {"error": "Validation Error", "details": ve.errors()}

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/agents"
    headers = get_auth_headers()

    payload: Dict[str, Any] = agent_payload.dict(exclude_none=True)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET AGENT
@mcp.tool()
async def get_agent(agent_id: int) -> Dict[str, Any]:
    """Get agent by id in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/agents/{agent_id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET ALL AGENTS
@mcp.tool()
async def get_all_agents(page: int = 1, per_page: int = 30) -> Dict[str, Any]:
    """Fetch agents from Freshservice."""

    if page < 1:
        return {"error": "Page number must be greater than 0"}

    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/agents"
    headers = get_auth_headers()

    params = {"page": page, "per_page": per_page}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

            link_header = response.headers.get("Link", "")
            pagination_info = parse_link_header(link_header)

            agents = response.json()

            return {
                "agents": agents,
                "pagination": {
                    "current_page": page,
                    "next_page": pagination_info.get("next"),
                    "prev_page": pagination_info.get("prev"),
                    "per_page": per_page,
                },
            }

        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)
        except Exception as e:
            logging.debug("Unexpected error in list_agents: %s", e)
            return {"error": "An unexpected error occurred"}


# FILTER AGENTS
@mcp.tool()
async def filter_agents(query: str) -> List[Dict[str, Any]]:
    """Filter Freshservice agents based on a query."""

    # Freshservice API requires the query to be wrapped in double quotes
    encoded_query = urllib.parse.quote(f'"{query}"')
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/agents/filter?query={encoded_query}"

    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# UPDATE AGENT
@mcp.tool()
async def update_agent(
    agent_id,
    occasional=None,
    email=None,
    department_ids=None,
    can_see_all_tickets_from_associated_departments=None,
    reporting_manager_id=None,
    address=None,
    time_zone=None,
    time_format=None,
    language=None,
    location_id=None,
    background_information=None,
    scoreboard_level_id=None,
):
    """Update the agent details in the Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/agents/{agent_id}"
    headers = get_auth_headers()

    payload = {
        "occasional": occasional,
        "email": email,
        "department_ids": department_ids,
        "can_see_all_tickets_from_associated_departments": can_see_all_tickets_from_associated_departments,
        "reporting_manager_id": reporting_manager_id,
        "address": address,
        "time_zone": time_zone,
        "time_format": time_format,
        "language": language,
        "location_id": location_id,
        "background_information": background_information,
        "scoreboard_level_id": scoreboard_level_id,
    }

    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient() as client:
        response = await client.put(url, headers=headers, json=payload)
        status_code = response.status_code
        if status_code == 200:
            return response.json()
        else:
            return f"Cannot fetch agents from the freshservice ${response.json()}"


# GET AGENT FIELDS
@mcp.tool()
async def get_agent_fields() -> Dict[str, Any]:
    """Get agent fields from Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/agents/fields"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET ALL AGENT GROUPS
@mcp.tool()
async def get_all_agent_groups() -> Dict[str, Any]:
    """Get all agent groups from Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/agent_groups"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET AGENT GROUP BY ID
@mcp.tool()
async def get_agent_group_by_id(group_id: int) -> Dict[str, Any]:
    """Get agent group by id in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/agent_groups/{group_id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# CREATE GROUP
@mcp.tool()
async def create_group(group_fields: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new agent group in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/agent_groups"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=group_fields)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# UPDATE GROUP
@mcp.tool()
async def update_group(group_id: int, group_fields: Dict[str, Any]) -> Dict[str, Any]:
    """Update an agent group in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/agent_groups/{group_id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=group_fields)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# CREATE REQUESTER GROUP
@mcp.tool()
async def create_requester_group(
    name: str, description: Optional[str] = None
) -> Dict[str, Any]:
    """Create a requester group in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/requester_groups"
    headers = get_auth_headers()

    payload = {"name": name, "description": description}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# UPDATE REQUESTER GROUP
@mcp.tool()
async def update_requester_group(
    id: int, name: Optional[str] = None, description: Optional[str] = None
) -> Dict[str, Any]:
    """Update an requester group in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/requester_groups/{id}"
    headers = get_auth_headers()

    payload = {"name": name, "description": description}

    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=payload)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# LIST REQUESTER GROUPS
@mcp.tool()
async def list_requester_groups(page: int = 1, per_page: int = 30) -> Dict[str, Any]:
    """List all requester groups in Freshservice."""

    if page < 1:
        return {"error": "Page number must be greater than 0"}

    if per_page < 1 or per_page > 100:
        return {"error": "Page size must be between 1 and 100"}

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/requester_groups"
    headers = get_auth_headers()

    params = {"page": page, "per_page": per_page}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

            link_header = response.headers.get("Link", "")
            pagination_info = parse_link_header(link_header)

            groups = response.json()

            return {
                "groups": groups,
                "pagination": {
                    "current_page": page,
                    "next_page": pagination_info.get("next"),
                    "prev_page": pagination_info.get("prev"),
                    "per_page": per_page,
                },
            }

        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET REQUESTER GROUPS BY ID
@mcp.tool()
async def get_requester_groups_by_id(id: int) -> Dict[str, Any]:
    """Get requester group by id in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/requester_groups/{id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# LIST REQUESTER GROUP MEMBERS
@mcp.tool()
async def list_requester_group_members(group_id: int) -> Dict[str, Any]:
    """List all members of a requester group in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/requester_groups/{group_id}/members"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# ADD REQUESTER TO GROUP
@mcp.tool()
async def add_requester_to_group(group_id: int, requester_id: int) -> Dict[str, Any]:
    """Add a requester to a group in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/requester_groups/{group_id}/members"
    headers = get_auth_headers()

    payload = {"requester_ids": [requester_id]}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET ALL CANNED RESPONSES
@mcp.tool()
async def get_all_canned_response() -> Dict[str, Any]:
    """List all canned response in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/canned_responses"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET CANNED RESPONSE BY ID
@mcp.tool()
async def get_canned_response(id: int) -> Dict[str, Any]:
    """Get a canned response in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/canned_responses/{id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# LIST ALL CANNED RESPONSE FOLDER
@mcp.tool()
async def list_all_canned_response_folder() -> Dict[str, Any]:
    """List all canned response of a folder in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/canned_response_folders"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# LIST CANNED RESPONSE FOLDER
@mcp.tool()
async def list_canned_response_folder(id: int) -> Dict[str, Any]:
    """List canned response folder in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/canned_response_folders/{id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET ALL WORKSPACES
@mcp.tool()
async def list_all_workspaces() -> Dict[str, Any]:
    """List all workspaces in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/workspaces"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET WORKSPACE
@mcp.tool()
async def get_workspace(id: int) -> Dict[str, Any]:
    """Get a workspace by its ID in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/workspaces/{id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET ALL SOLUTION CATEGORY
@mcp.tool()
async def get_all_solution_category() -> Dict[str, Any]:
    """Get all solution category in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/solutions/categories"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# GET SOLUTION CATEGORY
@mcp.tool()
async def get_solution_category(id: int) -> Dict[str, Any]:
    """Get solution category by its ID in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/solutions/categories/{id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return _sanitize_httpx_error(e)


# CREATE SOLUTION CATEGORY
@mcp.tool()
async def create_solution_category(
    name: str,
    description: str = None,
    workspace_id: int = None,
) -> Dict[str, Any]:
    """Create a new solution category in Freshservice."""
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/solutions/categories"
    headers = get_auth_headers()

    category_data = {
        "name": name,
        "description": description,
        "workspace_id": workspace_id,
    }

    category_data = {
        key: value for key, value in category_data.items() if value is not None
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=category_data)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return {"success": False, **_sanitize_httpx_error(e)}


# UPDATE SOLUTION CATEGORY
@mcp.tool()
async def update_solution_category(
    category_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    visibility: Optional[int] = None,  # Allowed values: 1, 2, 3, 4, 5, 6, 7
) -> Dict[str, Any]:
    """Update an existing solution category's details in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/solutions/categories/{category_id}"
    headers = get_auth_headers()

    category_data = {"name": name, "description": description, "visibility": visibility}

    category_data = {
        key: value for key, value in category_data.items() if value is not None
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=category_data)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return {"success": False, **_sanitize_httpx_error(e)}


# GET LIST OF SOLUTION FOLDER
@mcp.tool()
async def get_list_of_solution_folder(category_id: int) -> Dict[str, Any]:
    """Get list of solution folders under a category in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/solutions/categories/{category_id}/folders"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return {"success": False, **_sanitize_httpx_error(e)}


# CREATE SOLUTION FOLDER
@mcp.tool()
async def create_solution_folder(
    name: str,
    category_id: int,
    department_ids: List[int],
    visibility: int = 4,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new folder under a solution category in Freshservice."""

    if not department_ids:
        return {"error": "department_ids must be provided and cannot be empty."}

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/solutions/folders"
    headers = get_auth_headers()

    payload = {
        "name": name,
        "category_id": category_id,
        "visibility": visibility,  # Allowed values: 1, 2, 3, 4, 5, 6, 7
        "description": description,
        "department_ids": department_ids,
    }

    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return {"success": False, **_sanitize_httpx_error(e)}


# UPDATE SOLUTION FOLDER
@mcp.tool()
async def update_solution_folder(
    id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    visibility: Optional[int] = None,  # Allowed values: 1, 2, 3, 4, 5, 6, 7
) -> Dict[str, Any]:
    """Update an existing solution folder's details in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/solutions/folders/{id}"
    headers = get_auth_headers()

    payload = {"name": name, "description": description, "visibility": visibility}

    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=payload)
            response.raise_for_status()

            return response.json()
        except httpx.HTTPStatusError as e:
            return {"success": False, **_sanitize_httpx_error(e)}


# CREATE SOLUTION ARTICLE
@mcp.tool()
async def create_solution_article(
    title: str,
    description: str,
    folder_id: int,
    article_type: Optional[int] = 1,  # 1 - permanent, 2 - workaround
    status: Optional[int] = 1,  # 1 - draft, 2 - published
    tags: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    review_date: Optional[str] = None,  # Format: YYYY-MM-DD
) -> Dict[str, Any]:
    """Create a new solution article in Freshservice."""
    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/solutions/articles"
    headers = get_auth_headers()

    article_data = {
        "title": title,
        "description": description,
        "folder_id": folder_id,
        "article_type": article_type,
        "status": status,
        "tags": tags,
        "keywords": keywords,
        "review_date": review_date,
    }

    article_data = {
        key: value for key, value in article_data.items() if value is not None
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=article_data)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"success": False, **_sanitize_httpx_error(e)}


# UPDATE SOLUTION ARTICLE
@mcp.tool()
async def update_solution_article(
    article_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[int] = None,
    tags: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    review_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Update an existing solution article in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/solutions/articles/{article_id}"
    headers = get_auth_headers()

    payload = {
        "title": title,
        "description": description,
        "status": status,
        "tags": tags,
        "keywords": keywords,
        "review_date": review_date,
    }

    payload = {k: v for k, v in payload.items() if v is not None}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"success": False, **_sanitize_httpx_error(e)}


# GET LIST OF SOLUTION ARTICLE
@mcp.tool()
async def get_list_of_solution_article(folder_id: int) -> Dict[str, Any]:
    """Get list of solution articles in a folder in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/solutions/folders/{folder_id}/articles"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"success": False, **_sanitize_httpx_error(e)}


# GET SOLUTION ARTICLE
@mcp.tool()
async def get_solution_article(id: int) -> Dict[str, Any]:
    """Get solution article by its ID in Freshservice."""

    url = f"https://{FRESHSERVICE_DOMAIN}/api/v2/solutions/articles/{id}"
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"success": False, **_sanitize_httpx_error(e)}


# PUBLISH SOLUTION ARTICLE
@mcp.tool()
async def publish_solution_article(article_id: int) -> Dict[str, Any]:
    """Publish a solution article in Freshservice."""

    url = (
        f"https://{FRESHSERVICE_DOMAIN}/api/v2/solutions/articles/{article_id}/publish"
    )
    headers = get_auth_headers()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"success": False, **_sanitize_httpx_error(e)}


# GET AUTH HEADERS
def get_auth_headers():
    """Get authentication headers for Freshservice API."""
    if not FRESHSERVICE_APIKEY:
        raise ValueError("FRESHSERVICE_APIKEY environment variable is not set")
    if not FRESHSERVICE_DOMAIN:
        raise ValueError("FRESHSERVICE_DOMAIN environment variable is not set")

    return {
        "Authorization": f"Basic {base64.b64encode(f'{FRESHSERVICE_APIKEY}:X'.encode()).decode()}",
        "Content-Type": "application/json",
    }


def main():
    """Main entry point for the MCP server."""
    logging.info("Starting Freshservice MCP server")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

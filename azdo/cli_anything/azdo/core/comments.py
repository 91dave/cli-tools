"""Work item comments — list and add comments on Azure DevOps work items.

Uses the Comments API (7.1-preview.4) which is separate from work item
discussion history.
"""

from html.parser import HTMLParser
from typing import Optional

from cli_anything.azdo.utils.azdo_backend import api_get, api_post


# Comments API requires preview version
COMMENTS_API_VERSION = "7.1-preview.4"


class _HTMLStripper(HTMLParser):
    """Strip HTML tags, convert <br> to newlines, decode entities."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("br",):
            self._parts.append("\n")

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        self._parts.append(data)

    def get_text(self) -> str:
        return "".join(self._parts).strip()


def _strip_html(html: Optional[str]) -> str:
    """Strip HTML tags from text, converting <br> to newlines.

    Args:
        html: HTML string (or None).

    Returns:
        Plain text string.
    """
    if not html:
        return ""
    stripper = _HTMLStripper()
    stripper.feed(html)
    return stripper.get_text()


def _format_comment(raw: dict) -> dict:
    """Flatten a raw API comment into a consistent shape.

    Args:
        raw: Raw comment dict from the Azure DevOps API.

    Returns:
        Formatted comment dict with id, author, author_email, date, text, text_plain.
    """
    created_by = raw.get("createdBy", {})
    text = raw.get("text", "")
    return {
        "id": raw.get("id"),
        "author": created_by.get("displayName", ""),
        "author_email": created_by.get("uniqueName", ""),
        "date": raw.get("createdDate", ""),
        "text": text,
        "text_plain": _strip_html(text),
    }


def list_comments(work_item_id: int) -> dict:
    """List all comments on a work item.

    Args:
        work_item_id: The work item ID.

    Returns:
        Dict with 'count' and 'comments' list of formatted comment dicts.
    """
    result = api_get(
        f"/wit/workitems/{work_item_id}/comments",
        api_version=COMMENTS_API_VERSION,
    )
    comments = [_format_comment(c) for c in result.get("comments", [])]
    return {
        "count": len(comments),
        "comments": comments,
    }


def add_comment(work_item_id: int, text: str) -> dict:
    """Add a comment to a work item.

    The text is treated as markdown. The API's ``format=markdown`` query
    parameter tells Azure DevOps to render it natively — no client-side
    conversion is needed.

    Args:
        work_item_id: The work item ID.
        text: Comment text in markdown format.

    Returns:
        Formatted comment dict of the created comment.
    """
    result = api_post(
        f"/wit/workitems/{work_item_id}/comments",
        {"text": text},
        params={"format": "markdown"},
        api_version=COMMENTS_API_VERSION,
    )
    return _format_comment(result)

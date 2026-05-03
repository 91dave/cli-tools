"""Tests for comments module — list, add, and HTML stripping."""

import json
from unittest.mock import patch, MagicMock, call

import pytest

from cli_anything.azdo.core.comments import (
    list_comments,
    add_comment,
    _format_comment,
    _strip_html,
)


# ── Sample API responses ──────────────────────────────────────────

SAMPLE_COMMENT = {
    "id": 15065983,
    "workItemId": 12345,
    "version": 1,
    "text": "<p>Hello <strong>world</strong></p>",
    "createdBy": {
        "displayName": "Dave Arthur",
        "uniqueName": "dave@amdigital.co.uk",
    },
    "createdDate": "2023-11-20T10:45:37.827Z",
    "modifiedDate": "2023-11-20T10:45:37.827Z",
}

SAMPLE_COMMENT_2 = {
    "id": 15065984,
    "workItemId": 12345,
    "version": 1,
    "text": "<p>Another comment</p>",
    "createdBy": {
        "displayName": "Jane Smith",
        "uniqueName": "jane@amdigital.co.uk",
    },
    "createdDate": "2023-11-21T09:00:00.000Z",
    "modifiedDate": "2023-11-21T09:00:00.000Z",
}


# ══════════════════════════════════════════════════════════════════
# TestListComments
# ══════════════════════════════════════════════════════════════════

class TestListComments:

    @patch("cli_anything.azdo.core.comments.api_get")
    def test_list_comments_returns_formatted(self, mock_get):
        mock_get.return_value = {
            "totalCount": 2,
            "count": 2,
            "comments": [SAMPLE_COMMENT, SAMPLE_COMMENT_2],
        }
        result = list_comments(12345)
        assert result["count"] == 2
        assert len(result["comments"]) == 2
        c = result["comments"][0]
        assert c["id"] == 15065983
        assert c["author"] == "Dave Arthur"
        assert c["author_email"] == "dave@amdigital.co.uk"
        assert c["date"] == "2023-11-20T10:45:37.827Z"
        assert c["text"] == "<p>Hello <strong>world</strong></p>"
        assert c["text_plain"] == "Hello world"

    @patch("cli_anything.azdo.core.comments.api_get")
    def test_list_comments_strips_html(self, mock_get):
        mock_get.return_value = {
            "totalCount": 1,
            "count": 1,
            "comments": [SAMPLE_COMMENT],
        }
        result = list_comments(12345)
        assert result["comments"][0]["text_plain"] == "Hello world"

    @patch("cli_anything.azdo.core.comments.api_get")
    def test_list_comments_empty(self, mock_get):
        mock_get.return_value = {
            "totalCount": 0,
            "count": 0,
            "comments": [],
        }
        result = list_comments(12345)
        assert result["count"] == 0
        assert result["comments"] == []

    @patch("cli_anything.azdo.core.comments.api_get")
    def test_list_comments_uses_preview_api(self, mock_get):
        mock_get.return_value = {"totalCount": 0, "count": 0, "comments": []}
        list_comments(12345)
        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        assert kwargs.get("api_version") == "7.1-preview.4"


# ══════════════════════════════════════════════════════════════════
# TestAddComment
# ══════════════════════════════════════════════════════════════════

class TestAddComment:

    @patch("cli_anything.azdo.core.comments.api_post")
    def test_add_comment_posts_raw_markdown(self, mock_post):
        """add_comment sends raw markdown text without conversion."""
        mock_post.return_value = {
            **SAMPLE_COMMENT,
            "text": "my **bold** comment",
        }
        add_comment(12345, "my **bold** comment")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "12345" in args[0]
        body = args[1] if len(args) > 1 else kwargs.get("data")
        assert body == {"text": "my **bold** comment"}

    @patch("cli_anything.azdo.core.comments.api_post")
    def test_add_comment_sends_format_markdown_param(self, mock_post):
        """add_comment passes format=markdown as a query parameter."""
        mock_post.return_value = SAMPLE_COMMENT
        add_comment(12345, "test")
        _, kwargs = mock_post.call_args
        assert kwargs.get("params") == {"format": "markdown"}

    @patch("cli_anything.azdo.core.comments.api_post")
    def test_add_comment_returns_created(self, mock_post):
        mock_post.return_value = SAMPLE_COMMENT
        result = add_comment(12345, "Hello world")
        assert result["id"] == 15065983
        assert result["text"] == "<p>Hello <strong>world</strong></p>"

    @patch("cli_anything.azdo.core.comments.api_post")
    def test_add_comment_uses_preview_api(self, mock_post):
        mock_post.return_value = SAMPLE_COMMENT
        add_comment(12345, "test")
        _, kwargs = mock_post.call_args
        assert kwargs.get("api_version") == "7.1-preview.4"


# ══════════════════════════════════════════════════════════════════
# TestHtmlStripping
# ══════════════════════════════════════════════════════════════════

class TestHtmlStripping:

    def test_strip_simple_tags(self):
        assert _strip_html("<p>text</p>") == "text"

    def test_strip_nested_tags(self):
        assert _strip_html("<div><p>Hello <em>world</em></p></div>") == "Hello world"

    def test_strip_br_to_newline(self):
        assert _strip_html("line1<br>line2") == "line1\nline2"
        assert _strip_html("line1<br/>line2") == "line1\nline2"
        assert _strip_html("line1<br />line2") == "line1\nline2"

    def test_strip_handles_entities(self):
        assert _strip_html("&amp;") == "&"
        assert _strip_html("&lt;") == "<"
        assert _strip_html("&gt;") == ">"

    def test_strip_plain_text_passthrough(self):
        assert _strip_html("plain text with no tags") == "plain text with no tags"

    def test_strip_none_input(self):
        assert _strip_html(None) == ""

    def test_strip_empty_string(self):
        assert _strip_html("") == ""

"""Tests for comments module — list, add, markdown conversion, and HTML stripping."""

import json
import os
import tempfile
from unittest.mock import patch, MagicMock, call

import pytest

from cli_anything.azdo.core.comments import (
    list_comments,
    add_comment,
    _format_comment,
    _strip_html,
    _markdown_to_html,
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

class TestMarkdownToHtml:
    """Tests for markdown-to-HTML conversion."""

    def test_simple_paragraph(self):
        result = _markdown_to_html("Hello world")
        assert "<p>Hello world</p>" in result

    def test_bold_text(self):
        result = _markdown_to_html("**bold**")
        assert "<strong>bold</strong>" in result

    def test_italic_text(self):
        result = _markdown_to_html("*italic*")
        assert "<em>italic</em>" in result

    def test_multiline_preserves_paragraphs(self):
        md = "First paragraph\n\nSecond paragraph"
        result = _markdown_to_html(md)
        assert "<p>First paragraph</p>" in result
        assert "<p>Second paragraph</p>" in result

    def test_bullet_list(self):
        md = "- item one\n- item two"
        result = _markdown_to_html(md)
        assert "<li>item one</li>" in result
        assert "<li>item two</li>" in result

    def test_heading(self):
        result = _markdown_to_html("# Title")
        assert "<h1>Title</h1>" in result

    def test_code_block(self):
        md = "```\ncode here\n```"
        result = _markdown_to_html(md)
        assert "<code>" in result
        assert "code here" in result

    def test_inline_code(self):
        result = _markdown_to_html("`inline`")
        assert "<code>inline</code>" in result

    def test_link(self):
        result = _markdown_to_html("[text](https://example.com)")
        assert 'href="https://example.com"' in result
        assert ">text</a>" in result


class TestAddComment:

    @patch("cli_anything.azdo.core.comments.api_post")
    def test_add_comment_converts_markdown_to_html(self, mock_post):
        mock_post.return_value = {
            **SAMPLE_COMMENT,
            "text": "<p>my comment</p>",
        }
        add_comment(12345, "my comment")
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "12345" in args[0]
        body = args[1] if len(args) > 1 else kwargs.get("data")
        # The text should be HTML-converted markdown
        assert "<p>my comment</p>" in body["text"]

    @patch("cli_anything.azdo.core.comments.api_post")
    def test_add_comment_with_rich_markdown(self, mock_post):
        mock_post.return_value = SAMPLE_COMMENT
        md = "**bold** and *italic*\n\n- item"
        add_comment(12345, md)
        args, _ = mock_post.call_args
        body = args[1]
        assert "<strong>bold</strong>" in body["text"]
        assert "<em>italic</em>" in body["text"]
        assert "<li>item</li>" in body["text"]

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

"""Tests for the outreach visibility-fix bugs in dispatcher, send, and connect."""
import sys
import os
import types
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ── Stub playwright so the modules can be imported without the real package ──
def _stub_playwright():
    pw = types.ModuleType("playwright")
    pw_async = types.ModuleType("playwright.async_api")
    pw_async.Page = object  # type hint only — not called at runtime
    pw_async.async_playwright = MagicMock()
    sys.modules.setdefault("playwright", pw)
    sys.modules.setdefault("playwright.async_api", pw_async)

_stub_playwright()

# ── Helpers ──────────────────────────────────────────────────────────────────

def _visible_btn():
    btn = AsyncMock()
    btn.is_visible = AsyncMock(return_value=True)
    return btn


def _hidden_btn():
    btn = AsyncMock()
    btn.is_visible = AsyncMock(return_value=False)
    return btn


def _make_page(url="https://www.linkedin.com/in/test-user/"):
    page = AsyncMock()
    page.url = url
    return page


PROFILE_URL = "https://www.linkedin.com/in/test-user/"

# ── dispatcher._find_button ───────────────────────────────────────────────────

class TestFindButton:
    """_find_button must skip hidden elements and return the first visible one."""

    @pytest.mark.asyncio
    async def test_returns_none_when_all_hidden(self):
        from outreach.dispatcher import _find_button
        page = _make_page()
        page.query_selector = AsyncMock(return_value=_hidden_btn())

        result = await _find_button(page, ["button[aria-label*='Message']"])
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_element_missing(self):
        from outreach.dispatcher import _find_button
        page = _make_page()
        page.query_selector = AsyncMock(return_value=None)

        result = await _find_button(page, ["button[aria-label*='Message']"])
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_first_visible_button(self):
        from outreach.dispatcher import _find_button
        page = _make_page()
        visible = _visible_btn()
        page.query_selector = AsyncMock(side_effect=[_hidden_btn(), visible])

        result = await _find_button(page, ["sel-a", "sel-b"])
        assert result is visible

    @pytest.mark.asyncio
    async def test_skips_hidden_returns_visible_later_in_list(self):
        from outreach.dispatcher import _find_button
        page = _make_page()
        visible = _visible_btn()
        page.query_selector = AsyncMock(side_effect=[_hidden_btn(), _hidden_btn(), visible])

        result = await _find_button(page, ["a", "b", "c"])
        assert result is visible


# ── dispatcher._has_message_button ───────────────────────────────────────────

class TestHasMessageButton:
    """_has_message_button must return False when button exists but is hidden."""

    @pytest.mark.asyncio
    async def test_false_when_button_hidden(self):
        from outreach.dispatcher import _has_message_button
        page = _make_page()
        page.query_selector = AsyncMock(return_value=_hidden_btn())

        assert await _has_message_button(page) is False

    @pytest.mark.asyncio
    async def test_true_when_button_visible(self):
        from outreach.dispatcher import _has_message_button
        page = _make_page()
        page.query_selector = AsyncMock(return_value=_visible_btn())

        assert await _has_message_button(page) is True

    @pytest.mark.asyncio
    async def test_false_when_no_button(self):
        from outreach.dispatcher import _has_message_button
        page = _make_page()
        page.query_selector = AsyncMock(return_value=None)

        assert await _has_message_button(page) is False


# ── dispatcher.dispatch: flow selection ──────────────────────────────────────

class TestDispatchFlowSelection:
    """dispatch() must route to connect flow when message button is hidden."""

    @pytest.mark.asyncio
    async def test_uses_connect_flow_when_message_btn_hidden(self):
        import outreach.dispatcher as mod
        page = _make_page()
        page.query_selector = AsyncMock(return_value=_hidden_btn())

        mock_connect = AsyncMock(return_value=True)
        mock_msg = AsyncMock(return_value=True)
        mock_repo = MagicMock()

        with (
            patch.object(mod, "check_message_cap"),
            patch.object(mod, "human_delay", new=AsyncMock()),
            patch.object(mod, "send_connect_with_note", mock_connect),
            patch.object(mod, "send_message", mock_msg),
            patch.object(mod, "repo", mock_repo),
        ):
            await mod.dispatch(page, 1, PROFILE_URL, "hi", 10, dry_run=True)

        mock_connect.assert_called_once()
        mock_msg.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_message_flow_when_message_btn_visible(self):
        import outreach.dispatcher as mod
        page = _make_page()
        page.query_selector = AsyncMock(return_value=_visible_btn())

        mock_msg = AsyncMock(return_value=True)
        mock_connect = AsyncMock(return_value=True)
        mock_repo = MagicMock()

        with (
            patch.object(mod, "check_message_cap"),
            patch.object(mod, "human_delay", new=AsyncMock()),
            patch.object(mod, "send_message", mock_msg),
            patch.object(mod, "send_connect_with_note", mock_connect),
            patch.object(mod, "repo", mock_repo),
        ):
            await mod.dispatch(page, 1, PROFILE_URL, "hi", 10, dry_run=True)

        mock_msg.assert_called_once()
        mock_connect.assert_not_called()


# ── send_message: navigation dedup + visibility ───────────────────────────────

class TestSendMessageNavigation:
    """send_message must skip goto() when already on the profile page."""

    @pytest.mark.asyncio
    async def test_no_navigate_when_already_on_page(self):
        import outreach.send as mod
        page = _make_page(url=PROFILE_URL)
        page.query_selector = AsyncMock(return_value=None)

        with patch.object(mod, "human_delay", new=AsyncMock()):
            await mod.send_message(page, PROFILE_URL, "hello", dry_run=True)

        page.goto.assert_not_called()

    @pytest.mark.asyncio
    async def test_navigates_when_on_different_page(self):
        import outreach.send as mod
        page = _make_page(url="https://www.linkedin.com/feed/")
        page.query_selector = AsyncMock(return_value=None)

        with patch.object(mod, "human_delay", new=AsyncMock()):
            await mod.send_message(page, PROFILE_URL, "hello", dry_run=True)

        page.goto.assert_called_once_with(PROFILE_URL, wait_until="domcontentloaded")

    @pytest.mark.asyncio
    async def test_skips_hidden_message_button(self):
        """Must not click a hidden Message button — returns False."""
        import outreach.send as mod
        page = _make_page(url=PROFILE_URL)
        hidden = _hidden_btn()
        page.query_selector = AsyncMock(return_value=hidden)

        with patch.object(mod, "human_delay", new=AsyncMock()):
            result = await mod.send_message(page, PROFILE_URL, "hello", dry_run=True)

        assert result is False
        hidden.click.assert_not_called()

    @pytest.mark.asyncio
    async def test_clicks_visible_message_button(self):
        """Must click the visible Message button and open compose box."""
        import outreach.send as mod
        page = _make_page(url=PROFILE_URL)
        visible = _visible_btn()
        compose = AsyncMock()
        # First query_selector → Message btn; second (close btn in dry_run) → None
        page.query_selector = AsyncMock(side_effect=[visible, None])
        page.wait_for_selector = AsyncMock(return_value=compose)

        with patch.object(mod, "human_delay", new=AsyncMock()):
            result = await mod.send_message(page, PROFILE_URL, "hello", dry_run=True)

        assert result is True
        visible.click.assert_called_once()


# ── send_connect_with_note: navigation dedup + visibility ─────────────────────

class TestConnectNavigation:
    """send_connect_with_note must skip goto() when already on the profile page."""

    @pytest.mark.asyncio
    async def test_no_navigate_when_already_on_page(self):
        import outreach.connect as mod
        page = _make_page(url=PROFILE_URL)
        page.query_selector = AsyncMock(return_value=None)

        with patch.object(mod, "human_delay", new=AsyncMock()):
            await mod.send_connect_with_note(page, PROFILE_URL, "hello", dry_run=True)

        page.goto.assert_not_called()

    @pytest.mark.asyncio
    async def test_navigates_when_on_different_page(self):
        import outreach.connect as mod
        page = _make_page(url="https://www.linkedin.com/feed/")
        page.query_selector = AsyncMock(return_value=None)

        with patch.object(mod, "human_delay", new=AsyncMock()):
            await mod.send_connect_with_note(page, PROFILE_URL, "hello", dry_run=True)

        page.goto.assert_called_once_with(PROFILE_URL, wait_until="domcontentloaded")

    @pytest.mark.asyncio
    async def test_skips_hidden_connect_button(self):
        """Must not click a hidden Connect button — returns False."""
        import outreach.connect as mod
        page = _make_page(url=PROFILE_URL)
        hidden = _hidden_btn()
        page.query_selector = AsyncMock(return_value=hidden)

        with patch.object(mod, "human_delay", new=AsyncMock()):
            result = await mod.send_connect_with_note(page, PROFILE_URL, "hello", dry_run=True)

        assert result is False
        hidden.click.assert_not_called()

    @pytest.mark.asyncio
    async def test_clicks_visible_connect_button_dry_run(self):
        """Must click Connect, open Add-a-note dialog, then return True (dry run)."""
        import outreach.connect as mod
        page = _make_page(url=PROFILE_URL)
        connect_btn = _visible_btn()
        add_note_btn = AsyncMock()
        textarea = AsyncMock()

        # First query_selector → Connect btn; second (Dismiss in dry_run) → None
        page.query_selector = AsyncMock(side_effect=[connect_btn, None])
        page.wait_for_selector = AsyncMock(side_effect=[add_note_btn, textarea])

        with patch.object(mod, "human_delay", new=AsyncMock()):
            result = await mod.send_connect_with_note(
                page, PROFILE_URL, "hello", dry_run=True
            )

        assert result is True
        connect_btn.click.assert_called_once()
        add_note_btn.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_more_dropdown(self):
        """When direct Connect not visible, must click More and find Connect in dropdown."""
        import outreach.connect as mod
        page = _make_page(url=PROFILE_URL)

        more_btn = _visible_btn()
        connect_in_dropdown = _visible_btn()
        add_note_btn = AsyncMock()
        textarea = AsyncMock()

        direct_connect_selectors = {
            "button[aria-label*='Connect']",
            "button[aria-label*='Invite']",
            "button[aria-label*='連結']",
            "button[aria-label*='邀請']",
            "button.artdeco-button:has-text('Connect')",
            "button.artdeco-button:has-text('連結')",
        }
        more_selectors = {
            "button[aria-label*='More actions']",
            "button.artdeco-button:has-text('More')",
            "button.artdeco-button:has-text('更多')",
        }
        dropdown_selectors = {
            "div.artdeco-dropdown__content li:has-text('Connect')",
            "div.artdeco-dropdown__content li:has-text('連結')",
            "[aria-label*='Connect']",
        }

        async def mock_query(sel):
            if sel in direct_connect_selectors:
                return _hidden_btn()
            if sel in more_selectors:
                return more_btn
            if sel in dropdown_selectors:
                return connect_in_dropdown
            return None

        page.query_selector = mock_query
        page.wait_for_selector = AsyncMock(side_effect=[add_note_btn, textarea])

        with patch.object(mod, "human_delay", new=AsyncMock()):
            result = await mod.send_connect_with_note(
                page, PROFILE_URL, "hello", dry_run=True
            )

        assert result is True
        more_btn.click.assert_called_once()
        connect_in_dropdown.click.assert_called_once()

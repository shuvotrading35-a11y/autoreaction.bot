"""
AutoReactionBot - Keyboards Module
Centralised factory for every InlineKeyboardMarkup used in the bot.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram._utils.types import JSONDict
from typing import Optional

from config import ADD_TO_GROUP_LINK, ADD_TO_CHANNEL_LINK, MORE_BOTS_LINK


# ─── Styled Button ────────────────────────────────────────────────────────────

class StyledButton(InlineKeyboardButton):
    """Bot API 9.4 style parameter support (primary / success / danger)."""

    def __init__(self, text: str, style: Optional[str] = None, **kwargs):
        super().__init__(text=text, **kwargs)
        self._style = style

    def to_dict(self, recursive: bool = True) -> JSONDict:
        data = super().to_dict(recursive=recursive)
        if self._style:
            data["style"] = self._style
        return data


# ─── Main Menu ────────────────────────────────────────────────────────────────

def main_menu_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """
    Return the main menu keyboard shown on /start.
    Deep links for adding the bot are built from the bot username at runtime.
    """
    add_channel = f"https://t.me/{bot_username}?startchannel=true&admin=post_messages+edit_messages+delete_messages"
    add_group = f"https://t.me/{bot_username}?startgroup=true&admin=post_messages+edit_messages+delete_messages+manage_chat"

    buttons = [
        [
            StyledButton("🩵 Add To Channel", style="primary", url=add_channel),
            StyledButton("🩵 Add To Group",   style="primary", url=add_group),
        ],
        [
            StyledButton("🟢 How To Use", style="success", callback_data="how_to_use"),
            StyledButton("🟢 More Bots",  style="success", url=MORE_BOTS_LINK),
        ],
        [
            StyledButton("🟠 Admin Panel", style="danger", callback_data="admin_panel"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Single back button that returns to the main menu."""
    return InlineKeyboardMarkup(
        [[StyledButton("🏠 Main Menu", style="primary", callback_data="main_menu")]]
    )


# ─── Admin Panel ──────────────────────────────────────────────────────────────

def admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Full admin panel with all management options."""
    buttons = [
        [
            StyledButton("📊 Dashboard",    style="primary", callback_data="admin_dashboard"),
            StyledButton("⚙️ Settings",     style="primary", callback_data="admin_settings"),
        ],
        [
            StyledButton("😀 Emoji Manager", style="success", callback_data="emoji_manager"),
            StyledButton("📢 Broadcast",     style="success", callback_data="broadcast_menu"),
        ],
        [
            StyledButton("📈 Statistics",    style="primary", callback_data="statistics"),
            StyledButton("🏘 Groups",         style="primary", callback_data="admin_groups"),
        ],
        [
            StyledButton("📡 Channels",      style="primary", callback_data="admin_channels"),
            StyledButton("🚫 Banned Chats",  style="danger",  callback_data="banned_chats"),
        ],
        [
            StyledButton("📋 Logs",          style="primary", callback_data="admin_logs"),
            StyledButton("🔧 Maintenance",   style="success", callback_data="maintenance_toggle"),
        ],
        [
            StyledButton("🔄 Restart",       style="danger",  callback_data="admin_restart"),
            StyledButton("❌ Close",          style="danger",  callback_data="close_menu"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def admin_back_keyboard() -> InlineKeyboardMarkup:
    """Back button that returns to the admin panel."""
    return InlineKeyboardMarkup(
        [[StyledButton("◀️ Admin Panel", style="primary", callback_data="admin_panel")]]
    )


# ─── Settings Panel ───────────────────────────────────────────────────────────

def settings_keyboard(settings: dict[str, str]) -> InlineKeyboardMarkup:
    """
    Build settings panel buttons with live toggle indicators.
    Each setting shows ✅ or ❌ depending on its current value.
    """

    def _icon(key: str) -> str:
        return "✅" if settings.get(key) == "1" else "❌"

    def _style(key: str) -> str:
        return "success" if settings.get(key) == "1" else "danger"

    buttons = [
        [
            StyledButton(
                f"⚡ Auto Reaction {_icon('auto_reaction')}",
                style=_style("auto_reaction"),
                callback_data="toggle_auto_reaction",
            )
        ],
        [
            StyledButton(
                f"🎲 Random Emoji {_icon('random_emoji')}",
                style=_style("random_emoji"),
                callback_data="toggle_random_emoji",
            )
        ],
        [
            StyledButton(
                f"💥 Big Reaction {_icon('big_reaction')}",
                style=_style("big_reaction"),
                callback_data="toggle_big_reaction",
            )
        ],
        [
            StyledButton(
                f"⏱ Reaction Delay {_icon('reaction_delay')} (set via /setdelay)",
                style="primary",
                callback_data="noop_delay",
            )
        ],
        [
            StyledButton(
                f"🔧 Maintenance {_icon('maintenance')}",
                style=_style("maintenance"),
                callback_data="toggle_maintenance",
            )
        ],
        [
            StyledButton(
                f"🔗 Force Join {_icon('force_join')}",
                style=_style("force_join"),
                callback_data="toggle_force_join",
            )
        ],
        [
            StyledButton(
                f"📝 Logging {_icon('logging_enabled')}",
                style=_style("logging_enabled"),
                callback_data="toggle_logging",
            )
        ],
        [
            StyledButton("◀️ Back", style="primary", callback_data="admin_panel"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


# ─── Emoji Manager ────────────────────────────────────────────────────────────

def emoji_manager_keyboard() -> InlineKeyboardMarkup:
    """Emoji management sub-menu."""
    buttons = [
        [
            StyledButton("➕ Add Emoji",    style="success", callback_data="emoji_add"),
            StyledButton("🗑 Remove Emoji", style="danger",  callback_data="emoji_remove"),
        ],
        [
            StyledButton("📋 List Emojis",  style="primary", callback_data="emoji_list"),
            StyledButton("🔀 Toggle Emoji", style="primary", callback_data="emoji_toggle"),
        ],
        [
            StyledButton("⚖️ Set Weight",   style="success", callback_data="emoji_weight"),
        ],
        [StyledButton("◀️ Back", style="primary", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(buttons)


def emoji_list_keyboard(emojis: list[dict], page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """
    Paginated list of emojis with status indicator.
    Each row shows: <emoji> id:<N> [✅/❌]
    """
    start = page * per_page
    end = start + per_page
    page_emojis = emojis[start:end]

    buttons = []
    for emoji in page_emojis:
        is_enabled = emoji.get("is_enabled")
        state = "✅" if is_enabled else "❌"
        style = "success" if is_enabled else "danger"
        label = f"{emoji['emoji']}  #{emoji['id']}  {state}  w:{emoji.get('weight', 1)}"
        buttons.append(
            [StyledButton(label, style=style, callback_data=f"emoji_detail_{emoji['id']}")]
        )

    # Pagination row
    nav = []
    if page > 0:
        nav.append(StyledButton("◀️ Prev", style="primary", callback_data=f"emoji_page_{page - 1}"))
    total_pages = (len(emojis) + per_page - 1) // per_page
    nav.append(StyledButton(f"{page + 1}/{total_pages}", style="primary", callback_data="noop_page"))
    if end < len(emojis):
        nav.append(StyledButton("Next ▶️", style="primary", callback_data=f"emoji_page_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([StyledButton("◀️ Back", style="primary", callback_data="emoji_manager")])
    return InlineKeyboardMarkup(buttons)


# ─── Broadcast ────────────────────────────────────────────────────────────────

def broadcast_menu_keyboard() -> InlineKeyboardMarkup:
    """Broadcast target selection."""
    buttons = [
        [
            StyledButton("👥 Broadcast to Users",    style="primary", callback_data="broadcast_users"),
            StyledButton("🏘 Broadcast to Groups",   style="primary", callback_data="broadcast_groups"),
        ],
        [
            StyledButton("📡 Broadcast to Channels", style="primary", callback_data="broadcast_channels"),
            StyledButton("🌍 Broadcast to All",      style="success", callback_data="broadcast_all"),
        ],
        [StyledButton("◀️ Back", style="primary", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(buttons)


def broadcast_confirm_keyboard(target: str) -> InlineKeyboardMarkup:
    """Confirmation before sending a broadcast."""
    buttons = [
        [
            StyledButton("✅ Confirm Send", style="success", callback_data=f"broadcast_confirm_{target}"),
            StyledButton("❌ Cancel",       style="danger",  callback_data="broadcast_menu"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


# ─── Force Join ───────────────────────────────────────────────────────────────

def force_join_keyboard(channels: list[dict]) -> InlineKeyboardMarkup:
    """
    Build a keyboard that links to each required channel/group,
    plus a 'Done / Verify' button.
    """
    buttons = []
    for ch in channels:
        label = ch.get("channel_username") or f"Channel {ch['channel_id']}"
        link = ch.get("invite_link") or f"https://t.me/{label.lstrip('@')}"
        buttons.append([InlineKeyboardButton(f"📢 {label}", url=link)])
    buttons.append(
        [StyledButton("✅ I've Joined — Verify", style="success", callback_data="fj_verify")]
    )
    return InlineKeyboardMarkup(buttons)


# ─── Confirm / Cancel generic ─────────────────────────────────────────────────

def confirm_cancel_keyboard(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
    """Generic confirm / cancel pair."""
    return InlineKeyboardMarkup(
        [
            [
                StyledButton("✅ Confirm", style="success", callback_data=confirm_data),
                StyledButton("❌ Cancel",  style="danger",  callback_data=cancel_data),
            ]
        ]
    )


# ─── Close button ─────────────────────────────────────────────────────────────

def close_keyboard() -> InlineKeyboardMarkup:
    """Single close button to delete an interactive message."""
    return InlineKeyboardMarkup(
        [[StyledButton("❌ Close", style="danger", callback_data="close_menu")]]
    )


# ─── Banned chats ─────────────────────────────────────────────────────────────

def banned_chats_keyboard() -> InlineKeyboardMarkup:
    """Banned chats management."""
    buttons = [
        [
            StyledButton("➕ Ban Chat",   style="danger",  callback_data="ban_chat"),
            StyledButton("➖ Unban Chat", style="success", callback_data="unban_chat"),
        ],
        [StyledButton("◀️ Back", style="primary", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(buttons)


# ─── Statistics ───────────────────────────────────────────────────────────────

def statistics_keyboard() -> InlineKeyboardMarkup:
    """Statistics time-range selector."""
    buttons = [
        [
            StyledButton("📅 Today",    style="primary", callback_data="stats_today"),
            StyledButton("📆 Weekly",   style="primary", callback_data="stats_weekly"),
            StyledButton("🗓 Monthly",  style="primary", callback_data="stats_monthly"),
        ],
        [StyledButton("◀️ Back", style="primary", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(buttons)

"""
AutoReactionBot - Keyboards Module
Centralised factory for every InlineKeyboardMarkup used in the bot.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import ADD_TO_GROUP_LINK, ADD_TO_CHANNEL_LINK, MORE_BOTS_LINK


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
            InlineKeyboardButton("🩵 Add To Channel", url=add_channel),
            InlineKeyboardButton("🩵 Add To Group", url=add_group),
        ],
        [
            InlineKeyboardButton("🟢 How To Use", callback_data="how_to_use"),
            InlineKeyboardButton("🟢 More Bots", url=MORE_BOTS_LINK),
        ],
        [
            InlineKeyboardButton("🟠 Admin Panel", callback_data="admin_panel"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    """Single back button that returns to the main menu."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
    )


# ─── Admin Panel ──────────────────────────────────────────────────────────────

def admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Full admin panel with all management options."""
    buttons = [
        [
            InlineKeyboardButton("📊 Dashboard", callback_data="admin_dashboard"),
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
        ],
        [
            InlineKeyboardButton("😀 Emoji Manager", callback_data="emoji_manager"),
            InlineKeyboardButton("📢 Broadcast", callback_data="broadcast_menu"),
        ],
        [
            InlineKeyboardButton("📈 Statistics", callback_data="statistics"),
            InlineKeyboardButton("🏘 Groups", callback_data="admin_groups"),
        ],
        [
            InlineKeyboardButton("📡 Channels", callback_data="admin_channels"),
            InlineKeyboardButton("🚫 Banned Chats", callback_data="banned_chats"),
        ],
        [
            InlineKeyboardButton("📋 Logs", callback_data="admin_logs"),
            InlineKeyboardButton("🔧 Maintenance", callback_data="maintenance_toggle"),
        ],
        [
            InlineKeyboardButton("🔄 Restart", callback_data="admin_restart"),
            InlineKeyboardButton("❌ Close", callback_data="close_menu"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


def admin_back_keyboard() -> InlineKeyboardMarkup:
    """Back button that returns to the admin panel."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_panel")]]
    )


# ─── Settings Panel ───────────────────────────────────────────────────────────

def settings_keyboard(settings: dict[str, str]) -> InlineKeyboardMarkup:
    """
    Build settings panel buttons with live toggle indicators.
    Each setting shows ✅ or ❌ depending on its current value.
    """

    def _icon(key: str) -> str:
        return "✅" if settings.get(key) == "1" else "❌"

    buttons = [
        [
            InlineKeyboardButton(
                f"⚡ Auto Reaction {_icon('auto_reaction')}",
                callback_data="toggle_auto_reaction",
            )
        ],
        [
            InlineKeyboardButton(
                f"🎲 Random Emoji {_icon('random_emoji')}",
                callback_data="toggle_random_emoji",
            )
        ],
        [
            InlineKeyboardButton(
                f"💥 Big Reaction {_icon('big_reaction')}",
                callback_data="toggle_big_reaction",
            )
        ],
        [
            InlineKeyboardButton(
                f"⏱ Reaction Delay {_icon('reaction_delay')} (set via /setdelay)",
                callback_data="noop_delay",
            )
        ],
        [
            InlineKeyboardButton(
                f"🔧 Maintenance {_icon('maintenance')}",
                callback_data="toggle_maintenance",
            )
        ],
        [
            InlineKeyboardButton(
                f"🔗 Force Join {_icon('force_join')}",
                callback_data="toggle_force_join",
            )
        ],
        [
            InlineKeyboardButton(
                f"📝 Logging {_icon('logging_enabled')}",
                callback_data="toggle_logging",
            )
        ],
        [
            InlineKeyboardButton("◀️ Back", callback_data="admin_panel"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


# ─── Emoji Manager ────────────────────────────────────────────────────────────

def emoji_manager_keyboard() -> InlineKeyboardMarkup:
    """Emoji management sub-menu."""
    buttons = [
        [
            InlineKeyboardButton("➕ Add Emoji", callback_data="emoji_add"),
            InlineKeyboardButton("🗑 Remove Emoji", callback_data="emoji_remove"),
        ],
        [
            InlineKeyboardButton("📋 List Emojis", callback_data="emoji_list"),
            InlineKeyboardButton("🔀 Toggle Emoji", callback_data="emoji_toggle"),
        ],
        [
            InlineKeyboardButton("⚖️ Set Weight", callback_data="emoji_weight"),
        ],
        [InlineKeyboardButton("◀️ Back", callback_data="admin_panel")],
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
        state = "✅" if emoji.get("is_enabled") else "❌"
        label = f"{emoji['emoji']}  #{emoji['id']}  {state}  w:{emoji.get('weight', 1)}"
        buttons.append(
            [InlineKeyboardButton(label, callback_data=f"emoji_detail_{emoji['id']}")]
        )

    # Pagination row
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"emoji_page_{page - 1}"))
    total_pages = (len(emojis) + per_page - 1) // per_page
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="noop_page"))
    if end < len(emojis):
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"emoji_page_{page + 1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("◀️ Back", callback_data="emoji_manager")])
    return InlineKeyboardMarkup(buttons)


# ─── Broadcast ────────────────────────────────────────────────────────────────

def broadcast_menu_keyboard() -> InlineKeyboardMarkup:
    """Broadcast target selection."""
    buttons = [
        [
            InlineKeyboardButton("👥 Broadcast to Users", callback_data="broadcast_users"),
            InlineKeyboardButton("🏘 Broadcast to Groups", callback_data="broadcast_groups"),
        ],
        [
            InlineKeyboardButton("📡 Broadcast to Channels", callback_data="broadcast_channels"),
            InlineKeyboardButton("🌍 Broadcast to All", callback_data="broadcast_all"),
        ],
        [InlineKeyboardButton("◀️ Back", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(buttons)


def broadcast_confirm_keyboard(target: str) -> InlineKeyboardMarkup:
    """Confirmation before sending a broadcast."""
    buttons = [
        [
            InlineKeyboardButton("✅ Confirm Send", callback_data=f"broadcast_confirm_{target}"),
            InlineKeyboardButton("❌ Cancel", callback_data="broadcast_menu"),
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
        [InlineKeyboardButton("✅ I've Joined — Verify", callback_data="fj_verify")]
    )
    return InlineKeyboardMarkup(buttons)


# ─── Confirm / Cancel generic ─────────────────────────────────────────────────

def confirm_cancel_keyboard(confirm_data: str, cancel_data: str) -> InlineKeyboardMarkup:
    """Generic confirm / cancel pair."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=confirm_data),
                InlineKeyboardButton("❌ Cancel", callback_data=cancel_data),
            ]
        ]
    )


# ─── Close button ─────────────────────────────────────────────────────────────

def close_keyboard() -> InlineKeyboardMarkup:
    """Single close button to delete an interactive message."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Close", callback_data="close_menu")]]
    )


# ─── Banned chats ─────────────────────────────────────────────────────────────

def banned_chats_keyboard() -> InlineKeyboardMarkup:
    """Banned chats management."""
    buttons = [
        [
            InlineKeyboardButton("➕ Ban Chat", callback_data="ban_chat"),
            InlineKeyboardButton("➖ Unban Chat", callback_data="unban_chat"),
        ],
        [InlineKeyboardButton("◀️ Back", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(buttons)


# ─── Statistics ───────────────────────────────────────────────────────────────

def statistics_keyboard() -> InlineKeyboardMarkup:
    """Statistics time-range selector."""
    buttons = [
        [
            InlineKeyboardButton("📅 Today", callback_data="stats_today"),
            InlineKeyboardButton("📆 Weekly", callback_data="stats_weekly"),
            InlineKeyboardButton("🗓 Monthly", callback_data="stats_monthly"),
        ],
        [InlineKeyboardButton("◀️ Back", callback_data="admin_panel")],
    ]
    return InlineKeyboardMarkup(buttons)

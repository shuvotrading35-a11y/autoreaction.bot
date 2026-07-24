# 🤖 AutoReactionBot

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12+-blue?logo=python)
![PTB](https://img.shields.io/badge/python--telegram--bot-22.x-blue?logo=telegram)
![SQLite](https://img.shields.io/badge/Database-SQLite-green?logo=sqlite)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)

**A production-grade Telegram bot that automatically reacts to every message in your groups and channels.**

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| ⚡ **Auto Reaction** | Instantly reacts to every supported message type |
| 🎲 **Random Emoji** | Weighted random emoji selection from your pool |
| 💥 **Big Reactions** | Optional animated big-reaction mode |
| ⏱ **Reaction Delay** | Configurable delay between reactions (0–30s) |
| 🛡 **Flood Protection** | Global + per-chat rate limiter with sliding window |
| 🔁 **Auto Retry** | Up to 3 retries with backoff on API errors |
| 📊 **Dashboard** | Live CPU, RAM, uptime, user/group/channel stats |
| 😀 **Emoji Manager** | Add, remove, toggle, weight emojis per category |
| 📢 **Broadcast** | Send text/photo/video/document to users/groups/channels |
| 🔗 **Force Join** | Require users to join channels before using the bot |
| 📈 **Statistics** | Daily, weekly, monthly reaction and user stats |
| 🚫 **Chat Banning** | Block specific chats from receiving reactions |
| 🔧 **Maintenance Mode** | Take the bot offline without stopping the process |
| 💾 **DB Backup** | One-command database backup delivered to your DM |
| 🖥 **Health Check** | Full system health report on demand |
| 🌈 **Colored Logs** | ANSI-colored console logs + rotating file logs |

---

## 📂 Project Structure

```
AutoReactionBot/
├── main.py                 ← Entry point
├── config.py               ← All configuration & env vars
├── database.py             ← Async SQLite layer (aiosqlite)
├── keyboards.py            ← All InlineKeyboardMarkup builders
├── utils.py                ← Logging, rate limiter, emoji picker, helpers
├── requirements.txt
├── .env.example
│
├── handlers/
│   ├── __init__.py         ← register_all()
│   ├── start.py            ← /start, main menu, force-join verify
│   ├── admin.py            ← /admin, dashboard, groups, channels, logs
│   ├── settings.py         ← Toggle settings, /setdelay
│   ├── emoji_manager.py    ← Add/remove/toggle/weight emojis
│   ├── broadcast.py        ← Broadcast to users/groups/channels/all
│   ├── forcejoin.py        ← /addfj /removefj /listfj
│   ├── statistics.py       ← /stats, daily/weekly/monthly views
│   ├── maintenance.py      ← /maintenance /backup /optimize /health
│   └── reaction.py         ← Core auto-reaction engine + queue worker
│
├── assets/
│   ├── banner.jpg          ← (place your banner image here)
│   └── logo.png            ← (place your logo here)
│
├── logs/                   ← Rotating log files (auto-created)
├── database/               ← bot.db lives here (auto-created)
└── cache/                  ← Temporary cache (auto-created)
```

---

## 🗄 Database Schema

| Table | Purpose |
|---|---|
| `users` | All bot users with join date, last seen |
| `groups` | Groups the bot is a member of |
| `channels` | Channels the bot administers |
| `settings` | Key-value store for all toggleable settings |
| `admins` | Additional bot admins (beyond the owner) |
| `emojis` | Emoji pool with category, weight, enabled flag |
| `statistics` | Daily aggregated reaction/user/group counters |
| `broadcast_logs` | History of every broadcast with success/fail counts |
| `reaction_logs` | Per-message reaction history |
| `banned_chats` | Chats excluded from auto-reactions |
| `force_join` | Channels required for force-join verification |

---

## 🛠 Requirements

- **Python 3.12+**
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- Your numeric Telegram User ID (from [@userinfobot](https://t.me/userinfobot))

---

## 📦 Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourname/AutoReactionBot.git
cd AutoReactionBot
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
nano .env          # or use any text editor
```

Fill in at minimum:

```env
BOT_TOKEN=your_bot_token_here
OWNER_ID=your_telegram_user_id
DEVELOPER_USERNAME=@your_username
```

### 5. (Optional) Add your banner image

Place a `banner.jpg` inside the `assets/` directory. The bot will send it as
the welcome image on `/start`. If absent, the bot falls back to a text-only welcome.

---

## 🚀 Running the Bot

```bash
python main.py
```

To keep it running in the background with auto-restart:

```bash
# Using screen
screen -S autoreactionbot
python main.py
# Ctrl+A, D to detach

# Using nohup
nohup python main.py &> logs/nohup.log &

# Using systemd (recommended for servers)
# See systemd section below
```

### Systemd Service (Linux)

Create `/etc/systemd/system/autoreactionbot.service`:

```ini
[Unit]
Description=AutoReactionBot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/path/to/AutoReactionBot
ExecStart=/path/to/venv/bin/python main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable autoreactionbot
sudo systemctl start autoreactionbot
sudo systemctl status autoreactionbot
```

---

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | — | BotFather token |
| `OWNER_ID` | ✅ | — | Your Telegram user ID |
| `DEVELOPER_USERNAME` | ✅ | `@developer` | Shown on /start screen |
| `MORE_BOTS_LINK` | ❌ | `https://t.me/` | "More Bots" button URL |
| `LOG_LEVEL` | ❌ | `INFO` | Logging verbosity |
| `LOG_CHANNEL_ID` | ❌ | `0` | Telegram channel for error logs |
| `REACTION_DELAY` | ❌ | `0.5` | Seconds between reactions |
| `REACTION_COOLDOWN` | ❌ | `2.0` | Per-chat cooldown seconds |
| `REACTION_QUEUE_MAX_SIZE` | ❌ | `500` | Max queue depth |
| `REACTION_RETRY_COUNT` | ❌ | `3` | Retry attempts per reaction |
| `FLOOD_THRESHOLD` | ❌ | `10` | Max global reactions per window |
| `FLOOD_WINDOW` | ❌ | `10.0` | Flood check window (seconds) |
| `RATE_LIMIT_PER_CHAT` | ❌ | `5` | Max reactions per chat per window |
| `BROADCAST_DELAY` | ❌ | `0.05` | Seconds between broadcast sends |

---

## 🤖 Bot Commands

| Command | Access | Description |
|---|---|---|
| `/start` | Everyone | Show welcome screen |
| `/admin` | Owner | Open admin panel |
| `/settings` | Owner | Toggle bot settings |
| `/stats` | Owner | View statistics |
| `/broadcast` | Owner | Broadcast to users/groups/channels |
| `/addemoji` | Owner | Add emoji to pool |
| `/listemojis` | Owner | List all emojis |
| `/setdelay` | Owner | Set reaction delay |
| `/ban` | Owner | Ban a chat |
| `/unban` | Owner | Unban a chat |
| `/addfj` | Owner | Add force-join channel |
| `/removefj` | Owner | Remove force-join channel |
| `/listfj` | Owner | List force-join channels |
| `/maintenance` | Owner | Toggle maintenance mode |
| `/backup` | Owner | Download DB backup |
| `/optimize` | Owner | Optimise database |
| `/health` | Owner | System health report |

---

## 📋 Admin Panel Navigation

```
/admin
 ├── 📊 Dashboard         — Live stats: users, groups, channels, reactions, CPU, RAM
 ├── ⚙️ Settings          — Toggle all features with live ✅/❌ indicators
 ├── 😀 Emoji Manager
 │    ├── ➕ Add Emoji
 │    ├── 🗑 Remove Emoji
 │    ├── 📋 List Emojis   — Paginated, shows ID/weight/status
 │    ├── 🔀 Toggle Emoji
 │    └── ⚖️ Set Weight
 ├── 📢 Broadcast
 │    ├── 👥 Users
 │    ├── 🏘 Groups
 │    ├── 📡 Channels
 │    └── 🌍 All           — Live progress bar during send
 ├── 📈 Statistics         — Daily / Weekly / Monthly breakdown
 ├── 🏘 Groups             — List all active groups
 ├── 📡 Channels           — List all active channels
 ├── 🚫 Banned Chats       — Manage chat bans
 ├── 📋 Logs               — Last 20 log lines inline
 ├── 🔧 Maintenance        — Toggle maintenance mode
 └── 🔄 Restart            — Restart bot process
```

---

## 🔧 How Auto Reaction Works

1. A message arrives in a group or channel where the bot is admin.
2. The bot checks: auto-reaction enabled? not banned? not in maintenance? supported message type?
3. Global flood protector and per-chat rate limiter are consulted.
4. An emoji is selected (weighted random, or fixed highest-weight).
5. A `_ReactionJob` is placed in an `asyncio.Queue`.
6. A background worker consumes jobs one at a time with configurable delay.
7. The worker calls `setMessageReaction` with up to 3 retries on failure.
8. Permanent errors (chat not found, reactions not supported) are skipped immediately.
9. The reaction is logged to the database.

---

## 🛡 Security

- All admin and owner commands are gated by strict user ID checks.
- All SQL queries use parameterized statements (no injection possible).
- Input is validated and sanitized before storage.
- Callback data is validated via pattern matching.
- Flood and rate limiters prevent API abuse.

---

## 📸 Screenshots

> _Place your screenshots here._

| Welcome Screen | Admin Panel | Dashboard |
|:---:|:---:|:---:|
| ![welcome](assets/screenshot_welcome.png) | ![admin](assets/screenshot_admin.png) | ![dashboard](assets/screenshot_dashboard.png) |

---

## 📄 License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2025 AutoReactionBot

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

## 👨‍💻 Developer

Built with ❤️ using **python-telegram-bot v22** and **aiosqlite**.

> Telegram: [@yourusername](https://t.me/yourusername)

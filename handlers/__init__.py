"""
AutoReactionBot - Handlers Package
Exports a single register_all() function that wires every handler module
onto the Application instance.
"""

from handlers import (
    admin,
    broadcast,
    emoji_manager,
    forcejoin,
    maintenance,
    reaction,
    settings,
    start,
    statistics,
)


def register_all(application) -> None:
    """
    Register every handler module onto the given Application.
    Order matters: more specific handlers (conversations, commands)
    must be registered before the catch-all message handler.
    """
    # 1. Start / main menu
    start.register(application)

    # 2. Admin panel (commands + callbacks)
    admin.register(application)

    # 3. Settings toggles
    settings.register(application)

    # 4. Emoji manager (conversations)
    emoji_manager.register(application)

    # 5. Broadcast (conversation)
    broadcast.register(application)

    # 6. Force join management
    forcejoin.register(application)

    # 7. Statistics
    statistics.register(application)

    # 8. Maintenance / backup / health
    maintenance.register(application)

    # 9. Auto-reaction engine — registered LAST so command handlers take
    #    priority over the catch-all MessageHandler inside reaction.py
    reaction.register(application)

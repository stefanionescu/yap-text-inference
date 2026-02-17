"""Default tool regression prompts and expected outcomes."""

from typing import TypeAlias

from .apps import DATA as APPS_MESSAGES
from .life import DATA as LIFE_MESSAGES
from .edge_cases import DATA as EDGE_CASES_MESSAGES
from .non_visual import DATA as NON_VISUAL_MESSAGES
from .tech_gaming import DATA as TECH_GAMING_MESSAGES
from .games_casual import DATA as GAMES_CASUAL_MESSAGES
from .social_drama import DATA as SOCIAL_DRAMA_MESSAGES
from .tiktok_reels import DATA as TIKTOK_REELS_MESSAGES
from .photos_camera import DATA as PHOTOS_CAMERA_MESSAGES
from .visual_sharing import DATA as VISUAL_SHARING_MESSAGES
from .banking_finance import DATA as BANKING_FINANCE_MESSAGES
from .daily_utilities import DATA as DAILY_UTILITIES_MESSAGES
from .health_wellness import DATA as HEALTH_WELLNESS_MESSAGES
from .maps_navigation import DATA as MAPS_NAVIGATION_MESSAGES
from .planning_creative import DATA as PLANNING_CREATIVE_MESSAGES
from .social_media_browsing import DATA as SOCIAL_MEDIA_BROWSING_MESSAGES
from .messaging_notifications import DATA as MESSAGING_NOTIFICATIONS_MESSAGES
from .streaming_entertainment import DATA as STREAMING_ENTERTAINMENT_MESSAGES

ToolDefaultEntry: TypeAlias = tuple[str, bool] | tuple[str, list[tuple[str, bool]]]

TOOL_DEFAULT_MESSAGES: list[ToolDefaultEntry] = [
    *APPS_MESSAGES,
    *BANKING_FINANCE_MESSAGES,
    *DAILY_UTILITIES_MESSAGES,
    *EDGE_CASES_MESSAGES,
    *GAMES_CASUAL_MESSAGES,
    *HEALTH_WELLNESS_MESSAGES,
    *LIFE_MESSAGES,
    *MAPS_NAVIGATION_MESSAGES,
    *MESSAGING_NOTIFICATIONS_MESSAGES,
    *NON_VISUAL_MESSAGES,
    *PHOTOS_CAMERA_MESSAGES,
    *PLANNING_CREATIVE_MESSAGES,
    *SOCIAL_DRAMA_MESSAGES,
    *SOCIAL_MEDIA_BROWSING_MESSAGES,
    *STREAMING_ENTERTAINMENT_MESSAGES,
    *TECH_GAMING_MESSAGES,
    *TIKTOK_REELS_MESSAGES,
    *VISUAL_SHARING_MESSAGES,
]

__all__ = ["TOOL_DEFAULT_MESSAGES"]

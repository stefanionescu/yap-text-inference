"""Time classification and formatting utilities."""

from datetime import datetime


def get_time_classification(hour: int) -> str:
    """Classify time of day based on hour.
    
    Args:
        hour: Hour in 24-hour format (0-23)
        
    Returns:
        Time classification string
    """
    if hour == 0:
        return "Midnight"
    elif 1 <= hour <= 3:
        return "Night"
    elif 4 <= hour <= 6:
        return "Early Morning"
    elif 7 <= hour <= 11:
        return "Morning"
    elif hour == 12:
        return "Noon"
    elif 13 <= hour <= 16:
        return "Afternoon"
    elif 17 <= hour <= 20:
        return "Early Evening"
    elif 21 <= hour <= 23:
        return "Evening"
    return "Unknown"


def format_session_timestamp() -> str:
    """Generate formatted timestamp string for session.
    
    Returns:
        Formatted timestamp string with time classification
    """
    now = datetime.now()
    time_classification = get_time_classification(now.hour)
    return now.strftime(f"%d/%m/%Y %A %I:%M %p ({time_classification})")

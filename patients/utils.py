from django.utils import timezone
from django.conf import settings
import math

def is_within_working_hours():
    now = timezone.localtime(timezone.now())  # uses TIME_ZONE from settings
    day = now.weekday()        # Monday=0, Sunday=6
    hour = now.hour
    return (day in settings.WORKING_DAYS and 
            settings.WORKING_START_HOUR <= hour < settings.WORKING_END_HOUR)
            
# patients/utils.py


def is_within_premises(lat, lng, center_lat=-1.286389, center_lng=36.817223, radius_meters=100):
    """
    Check if the given coordinates are within a circular radius of the hospital.
    Default: Nairobi coordinates.
    """
    R = 6371000  # Earth radius in meters
    dlat = math.radians(lat - center_lat)
    dlng = math.radians(lng - center_lng)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(center_lat)) * math.cos(math.radians(lat)) * math.sin(dlng/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance = R * c
    return distance <= radius_meters
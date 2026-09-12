# from django.core.cache import cache
# from django.conf import settings

# CACHE_KEY = 'clock_offset_minutes'

# def get_clock_offset():
#     val = cache.get(CACHE_KEY)
#     if val is None:
#         return getattr(settings, 'CLOCK_OFFSET_MINUTES', 0)
#     return val

# def set_clock_offset(minutes: int):
#     cache.set(CACHE_KEY, minutes, timeout=None)  # no expiry
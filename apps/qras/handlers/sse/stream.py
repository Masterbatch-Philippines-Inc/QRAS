# import json
# from django.utils.timezone import localdate
# from handlers.sse.attendance_rows import build_attendance_payload


# def build_payload(since, dept=None, user=None):
#     from handlers.sse.counts import (
#         get_today_count, get_ut_count, get_ot_count,
#         get_hd_count, get_ml_count, get_ns_count,
#     )

#     try:
#         payload = json.dumps({
#             'today_count': get_today_count(dept),
#             'ut_count':    get_ut_count(dept, user),
#             'ot_count':    get_ot_count(dept, user),
#             'hd_count':    get_hd_count(dept, user),
#             'ml_count':    get_ml_count(dept, user),
#             'ns_count':    get_ns_count(dept),
#         })
#         return payload, since

#     except Exception:
#         fallback = json.dumps({
#             'today_count': 0, 'ut_count': 0, 'ot_count': 0,
#             'hd_count': 0, 'ml_count': 0, 'ns_count': 0,
#             'new_logs_since_last': 0,
#         })
#         return fallback, since


# def event_stream(since, dept=None, user=None):
#     import select
#     import psycopg2
#     from decouple import config
#     from django.db import close_old_connections

#     conn = None

#     while True:
#         try:
#             if conn is None or conn.closed:
#                 conn = psycopg2.connect(
#                     dbname=config('DB_NAME'),
#                     user=config('DB_USER'),
#                     password=config('DB_PASSWORD'),
#                     host=config('DB_HOST'),
#                     port=config('DB_PORT'),
#                 )
#                 conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
#                 cur = conn.cursor()
#                 cur.execute('LISTEN sync_needed;')

#                 # Push once immediately on (re)connect so the client has fresh counts
#                 payload, since = build_payload(since, dept, user)
#                 yield f'data: {payload}\n\n'

#             # Block until a notify arrives (60s keepalive ping to keep connection alive)
#             ready = select.select([conn], [], [], 60)[0]
#             if ready:
#                 import time
#                 time.sleep(1)
#                 # Drain all pending notifies in a loop
#                 conn.poll()
#                 while conn.notifies:
#                     conn.notifies.pop()
#                     time.sleep(0.1)
#                     conn.poll()

#                 payload, since = build_payload(since, dept, user)
#                 yield f'data: {payload}\n\n'
#             else:
#                 # Timeout — send a keepalive comment so the browser doesn't close the connection
#                 yield ': keepalive\n\n'

#             close_old_connections()

#         except GeneratorExit:
#             if conn and not conn.closed:
#                 conn.close()
#             return
#         except Exception:
#             if conn and not conn.closed:
#                 try:
#                     conn.close()
#                 except Exception:
#                     pass
#             conn = None
#             import time
#             time.sleep(3)


# def event_stream_attendance(since, dept=None, user=None):
#     import select
#     import psycopg2
#     from decouple import config
#     from django.db import close_old_connections

#     conn = None

#     while True:
#         try:
#             if conn is None or conn.closed:
#                 conn = psycopg2.connect(
#                     dbname=config('DB_NAME'),
#                     user=config('DB_USER'),
#                     password=config('DB_PASSWORD'),
#                     host=config('DB_HOST'),
#                     port=config('DB_PORT'),
#                 )
#                 conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
#                 cur = conn.cursor()
#                 cur.execute('LISTEN sync_needed;')

#                 payload, since = build_attendance_payload(since, dept, user)
#                 yield f'data: {payload}\n\n'

#             ready = select.select([conn], [], [], 60)[0]
#             if ready:
#                 import time
#                 time.sleep(1)
#                 # Drain all pending notifies in a loop
#                 conn.poll()
#                 while conn.notifies:
#                     conn.notifies.pop()
#                     time.sleep(0.1)
#                     conn.poll()

#                 payload, since = build_attendance_payload(since, dept, user)
#                 yield f'data: {payload}\n\n'
#             else:
#                 yield ': keepalive\n\n'

#             close_old_connections()

#         except GeneratorExit:
#             if conn and not conn.closed:
#                 conn.close()
#             return
#         except Exception:
#             if conn and not conn.closed:
#                 try:
#                     conn.close()
#                 except Exception:
#                     pass
#             conn = None
#             import time
#             time.sleep(3)
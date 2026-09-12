# import logging
# import threading
# import select
# import psycopg2
# from decouple import config

# logger = logging.getLogger(__name__)


# class _SilentStyle:
#     def SUCCESS(self, m): return m
#     def WARNING(self, m): return m
#     def ERROR(self, m):   return m


# class _SilentStdout:
#     def write(self, m):
#         logger.info(m)


# _server_was_unreachable = False
# _auto_sync_was_paused = False


# def _is_server_reachable():
#     import socket
#     from decouple import config
#     host = config('SERVER_DB_HOST', default='')
#     port = int(config('SERVER_DB_PORT', default=5432))
#     if not host:
#         return False
#     try:
#         with socket.create_connection((host, port), timeout=2):
#             return True
#     except OSError:
#         return False


# def run_auto_sync():
#     global _server_was_unreachable, _auto_sync_was_paused

#     from handlers.utils.sync_helpers import is_auto_sync_enabled
#     if not is_auto_sync_enabled():
#         if not _auto_sync_was_paused:
#             print('[AutoSync] Paused by admin.')
#             logger.info('[AutoSync] Paused by admin.')
#             _auto_sync_was_paused = True
#         return

#     if _auto_sync_was_paused:
#         print('[AutoSync] Resumed by admin.')
#         logger.info('[AutoSync] Resumed by admin.')
#         _auto_sync_was_paused = False

#     if not _is_server_reachable():
#         if not _server_was_unreachable:
#             print('[AutoSync] Server is unreachable. Skipping sync until it comes back online.')
#             logger.warning('[AutoSync] Server is unreachable. Sync paused.')
#             _server_was_unreachable = True
#         return

#     if _server_was_unreachable:
#         print('[AutoSync] Server is back online. Resuming sync.')
#         logger.info('[AutoSync] Server is back online. Resuming sync.')
#         _server_was_unreachable = False

#     from django.utils import timezone
#     print(f'[AutoSync] Running at {timezone.now().isoformat()}')
#     try:
#         from handlers.utils.sync_helpers import sync_all_models, sync_scan_files
#         sync_all_models(_SilentStdout(), _SilentStyle())
#         sync_scan_files(_SilentStdout(), _SilentStyle())
#         print(f'[AutoSync] Done.')
#     except Exception as e:
#         print(f'[AutoSync] Failed: {e}')
#         logger.error(f'[AutoSync] Failed: {e}')

# def _listen_for_changes():
#     global _server_was_unreachable

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
#                 cur.execute("LISTEN sync_needed;")
#                 print('[AutoSync] Listening for DB changes...')

#             # Block until a notification arrives (60s timeout to keep connection alive)
#             if select.select([conn], [], [], 60)[0]:
#                 conn.poll()
#                 while conn.notifies:
#                     notify = conn.notifies.pop(0)
#                     print(f'[AutoSync] Change detected on table: {notify.payload}')
#                     run_auto_sync()
#                     import time
#                     time.sleep(2)  # drain any burst notifies before listening again
#                     conn.poll()
#                     while conn.notifies:
#                         conn.notifies.pop()  # discard — already syncing

#         except Exception as e:
#             logger.error(f'[AutoSync] Listener error: {e}. Reconnecting in 5s...')
#             if conn and not conn.closed:
#                 try:
#                     conn.close()
#                 except Exception:
#                     pass
#             conn = None
#             import time
#             time.sleep(5)


# def start():
#     thread = threading.Thread(target=_listen_for_changes, daemon=True)
#     thread.start()
#     print('[AutoSync] Event-driven sync listener started.')
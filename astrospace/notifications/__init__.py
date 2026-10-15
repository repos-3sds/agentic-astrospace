"""Push notifications: scheduling and delivery over the NotificationJob tables.

The API only ever *stores* tokens and preferences (astrospace/api/me_routes.py).
This package is the other half: it decides what to send (morning_brief.py),
and sends it (push.py, worker.py). Nothing here is imported by a request
handler; it runs from `python -m astrospace.notifications.worker`.
"""

import frappe

# Redis keys for monitoring
LOCK_STATS_KEY = "insights:lock_stats"
LOCK_EVENTS_KEY = "insights:lock_events"


def log_lock_acquired(lock_key: str, query_name: str = None):
    """Log when a lock is successfully acquired."""
    try:
        redis = frappe.cache()
        redis.hincrby(LOCK_STATS_KEY, "locks_acquired", 1)

        if frappe.conf.get("insights_debug_locks"):
            _log_event("lock_acquired", lock_key, query_name)
    except Exception:
        pass


def log_lock_released(lock_key: str, query_name: str = None):
    """Log when a lock is released."""
    try:
        redis = frappe.cache()
        redis.hincrby(LOCK_STATS_KEY, "locks_released", 1)

        if frappe.conf.get("insights_debug_locks"):
            _log_event("lock_released", lock_key, query_name)
    except Exception:
        pass


def log_lock_contention(lock_key: str, query_name: str = None):
    """Log when a lock acquisition fails (contention)."""
    try:
        redis = frappe.cache()
        redis.hincrby(LOCK_STATS_KEY, "lock_contentions", 1)

        from .ibis_utils import SEMAPHORE_KEY
        current_semaphore = int(redis.get(SEMAPHORE_KEY) or 0)

        _create_lock_log("lock_contention", lock_key, query_name, current_semaphore)

        if frappe.conf.get("insights_debug_locks"):
            _log_event("lock_contention", lock_key, query_name)
    except Exception:
        pass


def log_semaphore_acquired(slot: int):
    """Log when a semaphore slot is acquired."""
    try:
        redis = frappe.cache()
        redis.hincrby(LOCK_STATS_KEY, "semaphore_acquired", 1)
        current_max = int(redis.hget(LOCK_STATS_KEY, "semaphore_max") or 0)
        if slot > current_max:
            redis.hset(LOCK_STATS_KEY, "semaphore_max", slot)
    except Exception:
        pass


def log_semaphore_released():
    """Log when a semaphore slot is released."""
    try:
        redis = frappe.cache()
        redis.hincrby(LOCK_STATS_KEY, "semaphore_released", 1)
    except Exception:
        pass


def log_queue_full(query_name: str = None):
    """Log when query is rejected due to full queue."""
    try:
        redis = frappe.cache()
        redis.hincrby(LOCK_STATS_KEY, "queue_full_count", 1)

        from .ibis_utils import get_max_concurrent_queries
        _create_lock_log("queue_full", None, query_name, get_max_concurrent_queries())
    except Exception:
        pass


def _create_lock_log(event_type: str, lock_key: str = None, query_name: str = None, semaphore_count: int = None):
    """Create a database log entry for lock events."""
    try:
        from insights.insights.doctype.insights_lock_log.insights_lock_log import create_lock_log
        create_lock_log(event_type, lock_key, query_name, semaphore_count)
    except Exception:
        pass


def log_query_execution(query_name: str, time_taken: float, from_cache: bool = False):
    """Log query execution metrics."""
    try:
        redis = frappe.cache()
        if from_cache:
            redis.hincrby(LOCK_STATS_KEY, "cache_hits", 1)
        else:
            redis.hincrby(LOCK_STATS_KEY, "queries_executed", 1)
            redis.hincrbyfloat(LOCK_STATS_KEY, "total_execution_time", time_taken)
    except Exception:
        pass


def _log_event(event_type: str, lock_key: str, query_name: str = None):
    """Log detailed event for debugging."""
    try:
        import time

        event = {
            "type": event_type,
            "lock_key": lock_key[:50],
            "query": query_name,
            "user": frappe.session.user,
            "time": time.time(),
        }
        redis = frappe.cache()
        # Keep last 100 events
        redis.lpush(LOCK_EVENTS_KEY, frappe.as_json(event))
        redis.ltrim(LOCK_EVENTS_KEY, 0, 99)
    except Exception:
        pass


def get_lock_stats():
    """Get current lock statistics."""
    try:
        redis = frappe.cache()
        stats = redis.hgetall(LOCK_STATS_KEY) or {}
        return {
            k.decode() if isinstance(k, bytes) else k: (
                float(v) if b"." in v else int(v)
            )
            if isinstance(v, bytes)
            else v
            for k, v in stats.items()
        }
    except Exception:
        return {}


def get_recent_events(limit: int = 20):
    """Get recent lock events for debugging."""
    try:
        redis = frappe.cache()
        events = redis.lrange(LOCK_EVENTS_KEY, 0, limit - 1) or []
        return [frappe.parse_json(e) for e in events]
    except Exception:
        return []


def get_current_semaphore_usage():
    """Get current semaphore counter value."""
    try:
        from .ibis_utils import SEMAPHORE_KEY

        redis = frappe.cache()
        value = redis.get(SEMAPHORE_KEY)
        return int(value) if value else 0
    except Exception:
        return 0


"""
Cloud dispatch layer for optional Azure sync targets.

Rules:
- If no cloud targets are active/configured, treat sync as success.
- If one or more active targets fail, sync is considered failed and payload
  should stay in Redis retry queue.
"""

from config import Config
from azure_cosmos_client import save_reading, is_ready as cosmos_ready
from azure_eventhub_client import send_event, is_ready as eventhub_ready


def active_targets() -> dict:
    return {
        "cosmos": Config.SYNC_TO_COSMOS and cosmos_ready(),
        "eventhub": Config.SYNC_TO_EVENTHUB and eventhub_ready(),
    }


def sync_reading_to_cloud(payload: dict) -> bool:
    targets = active_targets()

    outcomes = []
    if targets["cosmos"]:
        outcomes.append(save_reading(payload))
    if targets["eventhub"]:
        outcomes.append(send_event(payload))

    if not outcomes:
        return True
    return all(outcomes)

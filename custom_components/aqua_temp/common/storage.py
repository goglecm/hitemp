import asyncio

from homeassistant.core import HomeAssistant
from homeassistant.util.hass_dict import HassKey

from .consts import DOMAIN

_STORAGE_LOCK: HassKey[asyncio.Lock] = HassKey(f"{DOMAIN}_storage_lock")


def get_storage_lock(hass: HomeAssistant) -> asyncio.Lock:
    """Return the lock serialising read-modify-write cycles of the config store.

    The encryption key and the per-entry preferences share one file, written
    by separate Store instances, so concurrent entries could lose each
    other's changes without it.
    """
    return hass.data.setdefault(_STORAGE_LOCK, asyncio.Lock())

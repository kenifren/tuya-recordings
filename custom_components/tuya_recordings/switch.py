from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_CLOUD_ACTIVITY_PAUSED,
    CONF_LOOKBACK_DAYS,
    CONF_MEDIA_SYNC_ENABLED,
    CONF_MEDIA_SYNC_HOURS,
    CONF_MEDIA_STORAGE_PATH,
    CONF_THUMBNAIL_SYNC_ENABLED,
    DEFAULT_CLOUD_ACTIVITY_PAUSED,
    DEFAULT_LOOKBACK_DAYS,
    DEFAULT_MEDIA_SYNC_ENABLED,
    DEFAULT_MEDIA_SYNC_HOURS,
    DEFAULT_MEDIA_STORAGE_PATH,
    DEFAULT_THUMBNAIL_SYNC_ENABLED,
    DOMAIN,
    LOGGER,
    MANUFACTURER,
    NAME,
)
from . import async_pause_camera_work


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Tuya Recordings switches."""
    LOGGER.debug("Setting up Tuya Recordings switches for %s", entry.entry_id)
    async_add_entities(
        [
            TuyaRecordingsCloudPauseSwitch(hass, entry),
            TuyaRecordingsMediaSyncSwitch(hass, entry),
            TuyaRecordingsThumbnailSyncSwitch(hass, entry),
        ]
    )


class TuyaRecordingsCloudPauseSwitch(SwitchEntity):
    """Pause all Tuya camera cloud/video activity from this integration."""

    _attr_has_entity_name = True
    _attr_name = "Pause Tuya camera cloud activity"
    _attr_icon = "mdi:cloud-off-outline"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_cloud_activity_paused"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or NAME,
            manufacturer=MANUFACTURER,
            model=NAME,
        )

    @property
    def is_on(self) -> bool:
        return bool(self.entry.options.get(CONF_CLOUD_ACTIVITY_PAUSED, self.entry.data.get(CONF_CLOUD_ACTIVITY_PAUSED, DEFAULT_CLOUD_ACTIVITY_PAUSED)))

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "effect": "Stops refreshes, polling, thumbnail sync, media sync, and on-demand uncached clip downloads.",
            "media_sync_enabled": bool(self.entry.options.get(CONF_MEDIA_SYNC_ENABLED, self.entry.data.get(CONF_MEDIA_SYNC_ENABLED, DEFAULT_MEDIA_SYNC_ENABLED))),
            "thumbnail_sync_enabled": bool(self.entry.options.get(CONF_THUMBNAIL_SYNC_ENABLED, self.entry.data.get(CONF_THUMBNAIL_SYNC_ENABLED, DEFAULT_THUMBNAIL_SYNC_ENABLED))),
        }

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set_paused(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set_paused(False)

    async def _async_set_paused(self, paused: bool) -> None:
        options = dict(self.entry.options)
        options[CONF_CLOUD_ACTIVITY_PAUSED] = paused
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        entry_data = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id)
        if isinstance(entry_data, dict) and (client := entry_data.get("client")):
            client.cloud_activity_paused = paused
        if paused:
            await async_pause_camera_work(self.hass, self.entry.entry_id)
        self.async_write_ha_state()


class TuyaRecordingsMediaSyncSwitch(SwitchEntity):
    """Enable Tapo-style background media synchronization."""

    _attr_has_entity_name = True
    _attr_name = "Media Sync"
    _attr_icon = "mdi:sync"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_media_sync"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or NAME,
            manufacturer=MANUFACTURER,
            model=NAME,
        )

    @property
    def is_on(self) -> bool:
        return bool(self.entry.options.get(CONF_MEDIA_SYNC_ENABLED, self.entry.data.get(CONF_MEDIA_SYNC_ENABLED, DEFAULT_MEDIA_SYNC_ENABLED)))

    @property
    def extra_state_attributes(self) -> dict:
        paused = bool(self.entry.options.get(CONF_CLOUD_ACTIVITY_PAUSED, self.entry.data.get(CONF_CLOUD_ACTIVITY_PAUSED, DEFAULT_CLOUD_ACTIVITY_PAUSED)))
        return {
            "lookback_days": self.entry.options.get(CONF_LOOKBACK_DAYS, DEFAULT_LOOKBACK_DAYS),
            "sync_hours": self.entry.options.get(CONF_MEDIA_SYNC_HOURS, DEFAULT_MEDIA_SYNC_HOURS),
            "storage_path": self.entry.options.get(CONF_MEDIA_STORAGE_PATH, DEFAULT_MEDIA_STORAGE_PATH),
            "cloud_activity_paused": paused,
            "effective_state": "paused" if paused else ("enabled" if self.is_on else "disabled"),
        }

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        options = dict(self.entry.options)
        options[CONF_MEDIA_SYNC_ENABLED] = enabled
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        entry_data = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id)
        client = None
        if isinstance(entry_data, dict) and (client := entry_data.get("client")):
            client.media_sync_enabled = enabled
        self.async_write_ha_state()
        if enabled and not getattr(client, "cloud_activity_paused", False) and self.hass.services.has_service(DOMAIN, "sync_media"):
            self.hass.async_create_task(
                self.hass.services.async_call(
                    DOMAIN,
                    "sync_media",
                    {"entry_id": self.entry.entry_id},
                    blocking=False,
                )
            )


class TuyaRecordingsThumbnailSyncSwitch(SwitchEntity):
    """Enable lightweight background thumbnail previews."""

    _attr_has_entity_name = True
    _attr_name = "Thumbnail Sync"
    _attr_icon = "mdi:image-sync"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_thumbnail_sync"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title or NAME,
            manufacturer=MANUFACTURER,
            model=NAME,
        )

    @property
    def is_on(self) -> bool:
        return bool(self.entry.options.get(CONF_THUMBNAIL_SYNC_ENABLED, self.entry.data.get(CONF_THUMBNAIL_SYNC_ENABLED, DEFAULT_THUMBNAIL_SYNC_ENABLED)))

    @property
    def extra_state_attributes(self) -> dict:
        paused = bool(self.entry.options.get(CONF_CLOUD_ACTIVITY_PAUSED, self.entry.data.get(CONF_CLOUD_ACTIVITY_PAUSED, DEFAULT_CLOUD_ACTIVITY_PAUSED)))
        return {
            "lookback_days": self.entry.options.get(CONF_LOOKBACK_DAYS, DEFAULT_LOOKBACK_DAYS),
            "storage_path": self.entry.options.get(CONF_MEDIA_STORAGE_PATH, DEFAULT_MEDIA_STORAGE_PATH),
            "keeps_full_videos": bool(self.entry.options.get(CONF_MEDIA_SYNC_ENABLED, self.entry.data.get(CONF_MEDIA_SYNC_ENABLED, DEFAULT_MEDIA_SYNC_ENABLED))),
            "cloud_activity_paused": paused,
            "effective_state": "paused" if paused else ("enabled" if self.is_on else "disabled"),
        }

    async def async_turn_on(self, **kwargs) -> None:
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        options = dict(self.entry.options)
        options[CONF_THUMBNAIL_SYNC_ENABLED] = enabled
        self.hass.config_entries.async_update_entry(self.entry, options=options)
        entry_data = self.hass.data.get(DOMAIN, {}).get(self.entry.entry_id)
        client = None
        if isinstance(entry_data, dict) and (client := entry_data.get("client")):
            client.thumbnail_sync_enabled = enabled
        self.async_write_ha_state()
        if enabled and not getattr(client, "cloud_activity_paused", False) and self.hass.services.has_service(DOMAIN, "populate_thumbnails"):
            self.hass.async_create_task(
                self.hass.services.async_call(
                    DOMAIN,
                    "populate_thumbnails",
                    {"entry_id": self.entry.entry_id},
                    blocking=False,
                )
            )

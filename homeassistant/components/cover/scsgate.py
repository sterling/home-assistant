"""
Allow to configure a SCSGate cover.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/cover.scsgate/
"""
import logging

import homeassistant.components.scsgate as scsgate
from homeassistant.components.cover import CoverDevice
from homeassistant.const import CONF_NAME

DEPENDENCIES = ['scsgate']
SCS_ID = 'scs_id'


def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Setup the SCSGate cover."""
    devices = config.get('devices')
    covers = []
    logger = logging.getLogger(__name__)

    if devices:
        for _, entity_info in devices.items():
            if entity_info[SCS_ID] in scsgate.SCSGATE.devices:
                continue

            logger.info("Adding %s scsgate.cover", entity_info[CONF_NAME])

            name = entity_info[CONF_NAME]
            scs_id = entity_info[SCS_ID]
            cover = SCSGateCover(
                name=name,
                scs_id=scs_id,
                logger=logger)
            scsgate.SCSGATE.add_device(cover)
            covers.append(cover)

    add_devices_callback(covers)


# pylint: disable=too-many-arguments, too-many-instance-attributes
class SCSGateCover(CoverDevice):
    """Representation of SCSGate cover."""

    def __init__(self, scs_id, name, logger):
        """Initialize the cover."""
        self._scs_id = scs_id
        self._name = name
        self._logger = logger

    @property
    def scs_id(self):
        """Return the SCSGate ID."""
        return self._scs_id

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the cover."""
        return self._name

    @property
    def is_closed(self):
        """Return if the cover is closed."""
        return None

    def open_cover(self, **kwargs):
        """Move the cover."""
        from scsgate.tasks import RaiseRollerShutterTask

        scsgate.SCSGATE.append_task(
            RaiseRollerShutterTask(target=self._scs_id))

    def close_cover(self, **kwargs):
        """Move the cover down."""
        from scsgate.tasks import LowerRollerShutterTask

        scsgate.SCSGATE.append_task(
            LowerRollerShutterTask(target=self._scs_id))

    def stop_cover(self, **kwargs):
        """Stop the cover."""
        from scsgate.tasks import HaltRollerShutterTask

        scsgate.SCSGATE.append_task(HaltRollerShutterTask(target=self._scs_id))

    def process_event(self, message):
        """Handle a SCSGate message related with this cover."""
        self._logger.debug(
            "Rollershutter %s, got message %s",
            self._scs_id, message.toggled)

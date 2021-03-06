"""Support for on/off state of HDMI CEC devices."""
import logging
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    PLATFORM_SCHEMA, ENTITY_ID_FORMAT, BinarySensorDevice)
from homeassistant.const import CONF_NAME, CONF_DEVICES
import homeassistant.helpers.config_validation as cv
import homeassistant.components.cec as cec

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['cec']

CONF_LOGICAL_ADDRESS = 'logical_address'
STATE_TRANSITIONING_ON = 'turning_on'
STATE_TRANSITIONING_OFF = 'turning_off'

DEVICES_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME): cv.string,
    vol.Required(CONF_LOGICAL_ADDRESS): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_DEVICES): vol.Schema({cv.slug: DEVICES_SCHEMA}),
})

ICONS = {
    1: "mdi:camcorder-box",
    2: "mdi:camcorder-box",
    3: "mdi:tune",
    4: "mdi:play-circle-outline",
    5: "mdi:speaker",
    6: "mdi:tune",
    7: "mdi:tune",
    8: "mdi:play-circle-outline",
    9: "mdi:play-circle-outline",
    10: "mdi:tune",
    11: "mdi:play-circle-outline",
}

POWER_STATES = {
    0: True,    # on
    1: False,   # standby
    2: True,    # transitioning from standby to on
    3: False,   # transitioning from on to standby
}


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup HDMI CEC binary sensors."""
    devices = config.get(CONF_DEVICES)

    sensors = []
    if devices is None:
        sensors.append(CECBinarySensor("tv", "TV", 0))
    else:
        for device_name, device_config in devices.items():
            logical_address = int(device_config.get(CONF_LOGICAL_ADDRESS), 16)
            name = device_config.get(CONF_NAME, device_name)

            if 0 <= logical_address <= 14:
                sensors.append(
                    CECBinarySensor(device_name, name, logical_address)
                )
            else:
                _LOGGER.error("Bad logical address for device: %s (%s). " +
                              "Must be between 0 and 14 (inclusively)",
                              logical_address, name)

    add_devices(sensors)


class CECBinarySensor(BinarySensorDevice):
    """Representation of an HDMI CEC Binary Sensor."""

    def __init__(self, device_name, name, logical_address):
        """Initialize the HDMI CEC Binary Sensor."""
        self._device_name = device_name
        self._name = name
        self._address = logical_address
        self._state = False
        self.entity_id = ENTITY_ID_FORMAT.format(self._device_id())

    def _device_id(self):
        return "{}_{}".format(cec.DOMAIN, self._device_name).lower()

    @property
    def icon(self):
        """Get the appropriate device icon."""
        return ICONS.get(self._address, "mdi:television")

    @property
    def name(self):
        """Get device name."""
        return self._name

    @property
    def is_on(self):
        """True if the device is on."""
        return self._state

    def update(self):
        """Update the device state."""
        state = cec.get_device_power_status(self._address)
        self._state = POWER_STATES.get(state, False)

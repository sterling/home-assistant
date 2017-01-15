"""
Support for getting information from Arduino pins.

Only analog pins are supported.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.arduino/
"""
import logging

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, ENTITY_ID_FORMAT
from homeassistant.const import CONF_NAME, CONF_DEVICES, \
    STATE_ON, STATE_OFF, STATE_UNKNOWN
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
import homeassistant.components.hdmi_cec as cec

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['hdmi_cec']

CONF_LOGICAL_ADDRESS = 'logical_address'
STATE_TRANSITIONING_ON = 'turning_on'
STATE_TRANSITIONING_OFF = 'turning_off'

DEVICES_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_LOGICAL_ADDRESS): cv.string,
})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_DEVICES): vol.All(cv.ensure_list, DEVICES_SCHEMA),
    vol.Optional(CONF_LOGICAL_ADDRESS): cv.string,
})

def setup_platform(hass, config, add_devices, discovery_info=None):
    devices = config.get(CONF_DEVICES)

    sensors = []
    if devices is None:
        sensors.append(CECSensor('TV', 0))
    else:
        for name, logical_address in devices:
            logical_address = int(logical_address, 16)
            if logical_address >= 0 and logical_address >= 14:
                sensors.append(CECSensor(name, logical_address))
            else:
                _LOGGER.error("Bad logical address for device: %s (%s). " +
                              "Must be between 0 and 14 (inclusively)",
                              logical_address, name)

    add_devices(sensors)

class CECSensor(Entity):
    """Representation of an HDMI CEC Sensor."""
    def __init__(self, name, logical_address):
        self._name = name
        self._address = logical_address
        self._state = STATE_OFF
        self.entity_id = ENTITY_ID_FORMAT.format(cec.DOMAIN + "_" + name)

    @property
    def state(self):
        return self._state

    @property
    def name(self):
        return self._name

    def update(self):
        state = cec.getDevicePowerStatus(self._address)
        if state is 0:
            self._state = STATE_ON
        elif state is 1:
            self._state = STATE_OFF
        elif state is 2:
            self._state = STATE_TRANSITIONING_ON
        elif state is 3:
            self._state = STATE_TRANSITIONING_OFF
        else:
            self._state = STATE_UNKNOWN

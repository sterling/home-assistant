"""
Support for RESTful garage door.
"""
import logging

import requests
import voluptuous as vol

from homeassistant.components.garage_door import GarageDoorDevice, PLATFORM_SCHEMA
from homeassistant.const import STATE_CLOSED, STATE_OPEN, CONF_NAME, CONF_RESOURCE
import homeassistant.helpers.config_validation as cv

CONF_BODY_OPEN = 'body_open'
CONF_BODY_CLOSED = 'body_closed'
CONF_BODY_TRANS = 'body_trans'
DEFAULT_BODY_OPEN = 'OPEN'
DEFAULT_BODY_CLOSED = 'CLOSED'
DEFAULT_BODY_TRANS = 'TRANS'
DEFAULT_NAME = 'REST Garage Door'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_RESOURCE): cv.url,
    vol.Optional(CONF_BODY_OPEN, default=DEFAULT_BODY_OPEN): cv.string,
    vol.Optional(CONF_BODY_CLOSED, default=DEFAULT_BODY_CLOSED): cv.string,
    vol.Optional(CONF_BODY_TRANS, default=DEFAULT_BODY_TRANS): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})

_LOGGER = logging.getLogger(__name__)

# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    resource = config.get(CONF_RESOURCE)
    default_states = {
        'open': config.get(CONF_BODY_OPEN),
        'closed': config.get(CONF_BODY_CLOSED),
        'trans': config.get(CONF_BODY_TRANS)
    }

    try:
        response = requests.get(resource, timeout=10)
        state = response.text
    except requests.exceptions.MissingSchema:
        _LOGGER.error("Missing resource or schema in configuration. "
                      "Add http:// or https:// to your URL")
        return False
    except requests.exceptions.ConnectionError:
        _LOGGER.error("No route to resource/endpoint: %s", resource)
        return False

    add_devices_callback([
        RestGarageDoor(config.get(CONF_NAME), resource, state, default_states)
    ])


class RestGarageDoor(GarageDoorDevice):
    """Representation of a RESTful garage door."""

    def __init__(self, name, resource, state, default_states):
        """Initialize the garage door."""
        self._name = name
        self._resource = resource
        self._state = None
        self._default_states = default_states

        self.set_state(state)

    def set_state(self, state):
        self._state = state if state in self._default_states.values() else None

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def is_closed(self):
        """Return true if garage door is closed."""
        return self._state == self._default_states['closed']

    def log_endpoint_failure(self, action, status_code):
        _LOGGER.error("Failed to %s from %s. Received status code: %d",
                      action, self._resource, status_code)

    def update(self):
        """Get the latest data from REST API and update the state."""
        response = requests.get(self._resource, timeout=2)

        if response.status_code == 200:
            self.set_state(response.text)
        else:
            self.log_endpoint_failure('get state', response.status_code)

    def close_door(self, **kwargs):
        """Close the garage door."""
        self._trigger(False)

    def open_door(self, **kwargs):
        """Open the garage door."""
        self._trigger(True)

    def _trigger(self, open):
        """Trigger the door."""
        action = self._default_states['open'] if open else self._default_states['closed']
        response = requests.post(self._resource, data=action, timeout=2, headers={'Content-type': 'text/plain'})

        if response.status_code == 200:
            self._state = action
        else:
            self.log_endpoint_failure('set state', response.status_code)

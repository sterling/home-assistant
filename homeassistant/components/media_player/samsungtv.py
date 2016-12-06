"""
Support for interface with an Samsung TV.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.samsungtv/
"""
import logging

import voluptuous as vol

from homeassistant.components.media_player import (
    SUPPORT_NEXT_TRACK, SUPPORT_PAUSE, SUPPORT_PREVIOUS_TRACK,
    SUPPORT_TURN_OFF, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_STEP,
    MediaPlayerDevice, PLATFORM_SCHEMA)
from homeassistant.const import (
    CONF_HOST, CONF_NAME, STATE_OFF, STATE_ON, STATE_UNKNOWN, CONF_PORT)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['samsungctl==0.5.1']

_LOGGER = logging.getLogger(__name__)

CONF_TIMEOUT = 'timeout'

DEFAULT_NAME = 'Samsung TV Remote'
DEFAULT_PORT = 55000
DEFAULT_TIMEOUT = 0

SUPPORT_SAMSUNGTV = SUPPORT_PAUSE | SUPPORT_VOLUME_STEP | \
    SUPPORT_VOLUME_MUTE | SUPPORT_PREVIOUS_TRACK | \
    SUPPORT_NEXT_TRACK | SUPPORT_TURN_OFF

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
})


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Samsung TV platform."""
    name = config.get(CONF_NAME)

    # Generate a configuration for the Samsung library
    remote_config = {
        'name': 'HomeAssistant',
        'description': config.get(CONF_NAME),
        'id': 'ha.component.samsung',
        'port': config.get(CONF_PORT),
        'host': config.get(CONF_HOST),
        'timeout': config.get(CONF_TIMEOUT),
    }

    add_devices([SamsungTVDevice(name, remote_config)])


class SamsungTVDevice(MediaPlayerDevice):
    """Representation of a Samsung TV."""

    def __init__(self, name, config):
        """Initialize the Samsung device."""
        from samsungctl import Remote
        # Save a reference to the imported class
        self._remote_class = Remote
        self._name = name
        # Assume that the TV is not muted
        self._muted = False
        # Assume that the TV is in Play mode
        self._playing = True
        self._state = STATE_UNKNOWN
        self._remote = None
        self._config = config

    def update(self):
        """Retrieve the latest data."""
        # Send an empty key to see if we are still connected
        return self.send_key('KEY')

    def get_remote(self):
        """Create or return a remote control instance."""
        if self._remote is None:
            # We need to create a new instance to reconnect.
            self._remote = self._remote_class(self._config)

        return self._remote

    def send_key(self, key):
        """Send a key to the tv and handles exceptions."""
        try:
            self.get_remote().control(key)
            self._state = STATE_ON
        except (self._remote_class.UnhandledResponse,
                self._remote_class.AccessDenied, BrokenPipeError):
            # We got a response so it's on.
            # BrokenPipe can occur when the commands is sent to fast
            self._state = STATE_ON
            self._remote = None
            return False
        except (self._remote_class.ConnectionClosed, OSError):
            self._state = STATE_OFF
            self._remote = None
            return False

        return True

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def supported_media_commands(self):
        """Flag of media commands that are supported."""
        return SUPPORT_SAMSUNGTV

    def turn_off(self):
        """Turn off media player."""
        self.send_key('KEY_POWEROFF')
        # Force closing of remote session to provide instant UI feedback
        self.get_remote().close()

    def volume_up(self):
        """Volume up the media player."""
        self.send_key('KEY_VOLUP')

    def volume_down(self):
        """Volume down media player."""
        self.send_key('KEY_VOLDOWN')

    def mute_volume(self, mute):
        """Send mute command."""
        self.send_key('KEY_MUTE')

    def media_play_pause(self):
        """Simulate play pause media player."""
        if self._playing:
            self.media_pause()
        else:
            self.media_play()

    def media_play(self):
        """Send play command."""
        self._playing = True
        self.send_key('KEY_PLAY')

    def media_pause(self):
        """Send media pause command to media player."""
        self._playing = False
        self.send_key('KEY_PAUSE')

    def media_next_track(self):
        """Send next track command."""
        self.send_key('KEY_FF')

    def media_previous_track(self):
        """Send the previous track command."""
        self.send_key('KEY_REWIND')

    def turn_on(self):
        """Turn the media player on."""
        self.send_key('KEY_POWERON')

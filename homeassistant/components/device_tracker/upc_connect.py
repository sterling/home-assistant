"""
Support for UPC ConnectBox router.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.upc_connect/
"""
import asyncio
import logging
import xml.etree.ElementTree as ET

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
import homeassistant.helpers.config_validation as cv
from homeassistant.components.device_tracker import (
    DOMAIN, PLATFORM_SCHEMA, DeviceScanner)
from homeassistant.const import CONF_HOST, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_create_clientsession


_LOGGER = logging.getLogger(__name__)

DEFAULT_IP = '192.168.0.1'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_HOST, default=DEFAULT_IP): cv.string,
})

CMD_LOGIN = 15
CMD_LOGOUT = 16
CMD_DEVICES = 123


@asyncio.coroutine
def async_get_scanner(hass, config):
    """Return the UPC device scanner."""
    scanner = UPCDeviceScanner(hass, config[DOMAIN])
    success_init = yield from scanner.async_login()

    return scanner if success_init else None


class UPCDeviceScanner(DeviceScanner):
    """This class queries a router running UPC ConnectBox firmware."""

    def __init__(self, hass, config):
        """Initialize the scanner."""
        self.hass = hass
        self.host = config[CONF_HOST]
        self.password = config[CONF_PASSWORD]

        self.data = {}
        self.token = None

        self.headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': "http://{}/index.html".format(self.host),
            'User-Agent': ("Mozilla/5.0 (Windows NT 10.0; WOW64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/47.0.2526.106 Safari/537.36")
        }

        self.websession = async_create_clientsession(
            hass, auto_cleanup=False,
            cookie_jar=aiohttp.CookieJar(unsafe=True, loop=hass.loop)
        )

        @asyncio.coroutine
        def async_logout(event):
            """Logout from upc connect box."""
            try:
                yield from self._async_ws_function(CMD_LOGOUT)
                self.token = None
            finally:
                self.websession.detach()

        hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, async_logout)

    @asyncio.coroutine
    def async_scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        if self.token is None:
            reconnect = yield from self.async_login()
            if not reconnect:
                _LOGGER.error("Not connected to %s", self.host)
                return []

        raw = yield from self._async_ws_function(CMD_DEVICES)

        try:
            xml_root = yield from self.hass.loop.run_in_executor(
                None, ET.fromstring, raw)
            return [mac.text for mac in xml_root.iter('MACAddr')]
        except (ET.ParseError, TypeError):
            _LOGGER.warning("Can't read device from %s", self.host)
            self.token = None
            return []

    @asyncio.coroutine
    def async_get_device_name(self, device):
        """The firmware doesn't save the name of the wireless device."""
        return None

    @asyncio.coroutine
    def async_login(self):
        """Login into firmware and get first token."""
        response = None
        try:
            # get first token
            self.websession.cookie_jar.clear()
            with async_timeout.timeout(10, loop=self.hass.loop):
                response = yield from self.websession.get(
                    "http://{}/common_page/login.html".format(self.host)
                )

            yield from response.text()
            self.token = response.cookies['sessionToken'].value

            # login
            data = yield from self._async_ws_function(CMD_LOGIN, {
                'Username': 'NULL',
                'Password': self.password,
            })

            # successfull?
            if data is not None:
                return True
            return False

        except (asyncio.TimeoutError, aiohttp.errors.ClientError):
            _LOGGER.error("Can not load login page from %s", self.host)
            return False

        finally:
            if response is not None:
                yield from response.release()

    @asyncio.coroutine
    def _async_ws_function(self, function, additional_form=None):
        """Execute a command on UPC firmware webservice."""
        form_data = {
            'token': self.token,
            'fun': function
        }

        if additional_form:
            form_data.update(additional_form)

        response = None
        try:
            with async_timeout.timeout(10, loop=self.hass.loop):
                response = yield from self.websession.post(
                    "http://{}/xml/getter.xml".format(self.host),
                    data=form_data,
                    headers=self.headers
                )

                # error on UPC webservice
                if response.status != 200:
                    _LOGGER.warning(
                        "Error %d on %s.", response.status, function)
                    self.token = None
                    return

                # load data, store token for next request
                raw = yield from response.text()
                self.token = response.cookies['sessionToken'].value

                return raw

        except (asyncio.TimeoutError, aiohttp.errors.ClientError):
            _LOGGER.error("Error on %s", function)
            self.token = None

        finally:
            if response is not None:
                yield from response.release()

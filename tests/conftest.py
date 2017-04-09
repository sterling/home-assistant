"""Setup some common test helper things."""
import functools
import logging
from unittest.mock import patch

import pytest
import requests_mock as _requests_mock

from homeassistant import util, bootstrap
from homeassistant.util import location
from homeassistant.components import mqtt

from .common import async_test_home_assistant
from .test_util.aiohttp import mock_aiohttp_client

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


def test_real(func):
    """Force a function to require a keyword _test_real to be passed in."""
    @functools.wraps(func)
    def guard_func(*args, **kwargs):
        real = kwargs.pop('_test_real', None)

        if not real:
            raise Exception('Forgot to mock or pass "_test_real=True" to %s',
                            func.__name__)

        return func(*args, **kwargs)

    return guard_func


# Guard a few functions that would make network connections
location.detect_location_info = test_real(location.detect_location_info)
location.elevation = test_real(location.elevation)
util.get_local_ip = lambda: '127.0.0.1'


@pytest.fixture
def hass(loop):
    """Fixture to provide a test instance of HASS."""
    hass = loop.run_until_complete(async_test_home_assistant(loop))

    yield hass

    loop.run_until_complete(hass.async_stop())


@pytest.fixture
def requests_mock():
    """Fixture to provide a requests mocker."""
    with _requests_mock.mock() as m:
        yield m


@pytest.fixture
def aioclient_mock():
    """Fixture to mock aioclient calls."""
    with mock_aiohttp_client() as mock_session:
        yield mock_session


@pytest.fixture
def mqtt_mock(loop, hass):
    """Fixture to mock MQTT."""
    with patch('homeassistant.components.mqtt.MQTT') as mock_mqtt:
        loop.run_until_complete(bootstrap.async_setup_component(
            hass, mqtt.DOMAIN, {
                mqtt.DOMAIN: {
                    mqtt.CONF_BROKER: 'mock-broker',
                }
            }))
        client = mock_mqtt()
        client.reset_mock()
        return client

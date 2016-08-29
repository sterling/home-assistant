"""The tests the cover command line platform."""

import os
import tempfile
import unittest
from unittest import mock

import homeassistant.core as ha
import homeassistant.components.cover as cover
from homeassistant.components.cover import (
    command_line as cmd_rs)


class TestCommandCover(unittest.TestCase):
    """Test the cover command line platform."""

    def setup_method(self, method):
        """Setup things to be run when tests are started."""
        self.hass = ha.HomeAssistant()
        self.hass.config.latitude = 32.87336
        self.hass.config.longitude = 117.22743
        self.rs = cmd_rs.CommandCover(self.hass, 'foo',
                                      'cmd_open', 'cmd_close',
                                      'cmd_stop', 'cmd_state',
                                      None)  # FIXME

    def teardown_method(self, method):
        """Stop down everything that was started."""
        self.hass.stop()

    def test_should_poll(self):
        """Test the setting of polling."""
        self.assertTrue(self.rs.should_poll)
        self.rs._command_state = None
        self.assertFalse(self.rs.should_poll)

    def test_query_state_value(self):
        """Test with state value."""
        with mock.patch('subprocess.check_output') as mock_run:
            mock_run.return_value = b' foo bar '
            result = self.rs._query_state_value('runme')
            self.assertEqual('foo bar', result)
            mock_run.assert_called_once_with('runme', shell=True)

    def test_state_value(self):
        """Test with state value."""
        with tempfile.TemporaryDirectory() as tempdirname:
            path = os.path.join(tempdirname, 'cover_status')
            test_cover = {
                'statecmd': 'cat {}'.format(path),
                'opencmd': 'echo 1 > {}'.format(path),
                'closecmd': 'echo 1 > {}'.format(path),
                'stopcmd': 'echo 0 > {}'.format(path),
                'value_template': '{{ value }}'
            }
            self.assertTrue(cover.setup(self.hass, {
                'cover': {
                    'platform': 'command_line',
                    'covers': {
                        'test': test_cover
                    }
                }
            }))

            state = self.hass.states.get('cover.test')
            self.assertEqual('unknown', state.state)

            cover.open_cover(self.hass, 'cover.test')
            self.hass.pool.block_till_done()

            state = self.hass.states.get('cover.test')
            self.assertEqual('open', state.state)

            cover.close_cover(self.hass, 'cover.test')
            self.hass.pool.block_till_done()

            state = self.hass.states.get('cover.test')
            self.assertEqual('open', state.state)

            cover.stop_cover(self.hass, 'cover.test')
            self.hass.pool.block_till_done()

            state = self.hass.states.get('cover.test')
            self.assertEqual('closed', state.state)

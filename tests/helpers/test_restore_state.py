"""The tests for the Restore component."""
import asyncio
from datetime import timedelta
from unittest.mock import patch, MagicMock

from homeassistant.bootstrap import setup_component
from homeassistant.const import EVENT_HOMEASSISTANT_START
from homeassistant.core import CoreState, split_entity_id, State
import homeassistant.util.dt as dt_util
from homeassistant.components import input_boolean, recorder
from homeassistant.helpers.restore_state import (
    async_get_last_state, DATA_RESTORE_CACHE)

from tests.common import (
    get_test_home_assistant, mock_coro, init_recorder_component)


@asyncio.coroutine
def test_caching_data(hass):
    """Test that we cache data."""
    hass.config.components.add('recorder')
    hass.state = CoreState.starting

    states = [
        State('input_boolean.b0', 'on'),
        State('input_boolean.b1', 'on'),
        State('input_boolean.b2', 'on'),
    ]

    with patch('homeassistant.helpers.restore_state.last_recorder_run',
               return_value=MagicMock(end=dt_util.utcnow())), \
            patch('homeassistant.helpers.restore_state.get_states',
                  return_value=states), \
            patch('homeassistant.helpers.restore_state.async_get_instance',
                  return_value=mock_coro()):
        state = yield from async_get_last_state(hass, 'input_boolean.b1')

    assert DATA_RESTORE_CACHE in hass.data
    assert hass.data[DATA_RESTORE_CACHE] == {st.entity_id: st for st in states}

    assert state is not None
    assert state.entity_id == 'input_boolean.b1'
    assert state.state == 'on'

    hass.bus.async_fire(EVENT_HOMEASSISTANT_START)

    yield from hass.async_block_till_done()

    assert DATA_RESTORE_CACHE not in hass.data


def _add_data_in_last_run(entities):
    """Add test data in the last recorder_run."""
    # pylint: disable=protected-access
    t_now = dt_util.utcnow() - timedelta(minutes=10)
    t_min_1 = t_now - timedelta(minutes=20)
    t_min_2 = t_now - timedelta(minutes=30)

    recorder_runs = recorder.get_model('RecorderRuns')
    states = recorder.get_model('States')
    with recorder.session_scope() as session:
        run = recorder_runs(
            start=t_min_2,
            end=t_now,
            created=t_min_2
        )
        recorder._INSTANCE._commit(session, run)

        for entity_id, state in entities.items():
            dbstate = states(
                entity_id=entity_id,
                domain=split_entity_id(entity_id)[0],
                state=state,
                attributes='{}',
                last_changed=t_min_1,
                last_updated=t_min_1,
                created=t_min_1)
            recorder._INSTANCE._commit(session, dbstate)


def test_filling_the_cache():
    """Test filling the cache from the DB."""
    test_entity_id1 = 'input_boolean.b1'
    test_entity_id2 = 'input_boolean.b2'

    hass = get_test_home_assistant()
    hass.state = CoreState.starting

    init_recorder_component(hass)

    _add_data_in_last_run({
        test_entity_id1: 'on',
        test_entity_id2: 'off',
    })

    hass.block_till_done()
    setup_component(hass, input_boolean.DOMAIN, {
        input_boolean.DOMAIN: {
            'b1': None,
            'b2': None,
        }})

    hass.start()

    state = hass.states.get('input_boolean.b1')
    assert state
    assert state.state == 'on'

    state = hass.states.get('input_boolean.b2')
    assert state
    assert state.state == 'off'

    hass.stop()

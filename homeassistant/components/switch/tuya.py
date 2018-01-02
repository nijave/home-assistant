"""
Simple platform to control **SOME** Tuya switch devices.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.tuya/
"""
import voluptuous as vol
from homeassistant.components.switch import SwitchDevice, PLATFORM_SCHEMA
from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_ID)
import homeassistant.helpers.config_validation as cv
import logging

REQUIREMENTS = ['pytuya==1.0']

CONF_DEVICE_ID = 'device_id'
CONF_LOCAL_KEY = 'local_key'

DEFAULT_ID = 1

ATTR_CURRENT = 'current'
ATTR_CURRENT_CONSUMPTION = 'current_consumption'
ATTR_VOLTAGE = 'voltage'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_DEVICE_ID): cv.string,
    vol.Required(CONF_LOCAL_KEY): cv.string,
    vol.Optional(CONF_ID, default=DEFAULT_ID): cv.string,
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up of the Tuya switch."""
    import pytuya

    add_devices([TuyaDevice(
        pytuya.OutletDevice(
            config.get(CONF_DEVICE_ID),
            config.get(CONF_HOST),
            config.get(CONF_LOCAL_KEY),
        ),
        config.get(CONF_NAME),
        config.get(CONF_ID)
    )])


class TuyaDevice(SwitchDevice):
    """Representation of a Tuya switch."""

    def __init__(self, device, name, switchid):
        """Initialize the Tuya switch."""
        self._device = device
        self._name = name
        # TODO make sure state is reliably set (see 'update' method below)
        self._state = False #device.status()['dps']['1']
        self._switchid = switchid

    @property
    def name(self):
        """Get name of Tuya switch."""
        return self._name

    @property
    def is_on(self):
        """Check if Tuya switch is on."""
        return self._state

    @property
    def device_state_attributes(self):
        try:
            attrs = {}
            attrs[ATTR_CURRENT] = "{} mA".format(self._status['dps']['4'])
            attrs[ATTR_CURRENT_CONSUMPTION] = "{} W".format(self._status['dps']['5']/10)
            attrs[ATTR_VOLTAGE] = "{} V".format(self._status['dps']['6']/10)
        except: # No status info
            logging.getLogger(__name__).exception("Problem getting device state attributes")
            attrs = None
        return attrs

    def turn_on(self, **kwargs):
        """Turn Tuya switch on."""
        self._device.set_status(True, self._switchid)

    def turn_off(self, **kwargs):
        """Turn Tuya switch off."""
        self._device.set_status(False, self._switchid)
    
    def update(self):
        retry_limit = 3
        '''
        Tuya device tends to send back a RST,ACK on first try
        which kills the TCP connection. It seems sporadic since
        occassionally the status update works fine on the first
        try. Theory is the device has an issue with HA constantly
        querying it or the connection not being closed properly.
        
        Regardless, it seems to work consistently with this workaround
        in place.
        '''
        for i in range(retry_limit):
            try:
                self._status = self._device.status()
                self._state = self._status['dps']['1']
                return
            except:
                if i+1 == retry_limit:
                    raise ConnectionRefusedError("Failed communicating with outlet after 3 tries")
                else:
                    logging.getLogger(__name__).warn("Try: {}/{} - failed to update information for {}".format(i+1, retry_limit, self._device))
                    continue


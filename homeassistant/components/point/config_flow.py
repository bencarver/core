"""Config flow for Minut Point."""
from collections import OrderedDict
import logging

from pypoint import PointSession

from homeassistant import config_entries
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

DATA_FLOW_IMPL = "point_flow_implementation"

_LOGGER = logging.getLogger(__name__)


@callback
def register_flow_implementation(hass, domain, client_id, client_secret):
    """Register a flow implementation.

    domain: Domain of the component responsible for the implementation.
    name: Name of the component.
    client_id: Client id.
    client_secret: Client secret.
    """
    if DATA_FLOW_IMPL not in hass.data:
        hass.data[DATA_FLOW_IMPL] = OrderedDict()

    hass.data[DATA_FLOW_IMPL][domain] = {
        CONF_CLIENT_ID: client_id,
        CONF_CLIENT_SECRET: client_secret,
    }


class PointFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self.flow_impl = None

    async def async_step_import(self, user_input=None):
        """Handle external yaml configuration."""
        if self._async_current_entries():
            return self.async_abort(reason="already_setup")

        self.flow_impl = DOMAIN

        return await self.async_step_auth()

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        if self._async_current_entries():
            return self.async_abort(reason="already_setup")

        return await self._async_create_session()

    async def async_step_code(self, code=None):
        """Received code for authentication."""
        if self._async_current_entries():
            return self.async_abort(reason="already_setup")

        if code is None:
            return self.async_abort(reason="no_code")

        _LOGGER.debug(
            "Should close all flows below %s",
            self._async_in_progress(),
        )
        # Remove notification if no other discovery config entries in progress

        return await self._async_create_session(code)

    async def _async_create_session(self):
        """Create point session and entries."""

        flow = self.hass.data[DATA_FLOW_IMPL][DOMAIN]
        client_id = flow[CONF_CLIENT_ID]
        client_secret = flow[CONF_CLIENT_SECRET]
        point_session = PointSession(
            async_get_clientsession(self.hass),
            client_id,
            client_secret,
        )
        await point_session.get_access_token()  # No code parameter needed
        _LOGGER.debug("Got new token")
        if not point_session.is_authorized:
            _LOGGER.error("Authentication Error")
            return self.async_abort(reason="auth_error")

        _LOGGER.info("Successfully authenticated Point")
        user_email = (await point_session.user()).get("email") or ""

        return self.async_create_entry(
            title=user_email,
            data={
                "token": point_session.token,
                "refresh_args": {
                    CONF_CLIENT_ID: client_id,
                    CONF_CLIENT_SECRET: client_secret,
                },
            },
        )

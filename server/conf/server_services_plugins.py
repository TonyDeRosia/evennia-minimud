"""

Server plugin services

This plugin module can define user-created services for the Server to
start.

This module must handle all imports and setups required to start a
twisted service (see examples in evennia.server.server). It must also
contain a function start_plugin_services(application). Evennia will
call this function with the main Server application (so your services
can be added to it). The function should not return anything. Plugin
services are started last in the Server startup process.

"""


from twisted.application import service, internet
from twisted.internet import task
from evennia.utils import logger


class HeartbeatService(service.Service):
    """Simple service that logs a heartbeat periodically."""

    def startService(self):
        super().startService()
        self._task = task.LoopingCall(self._beat)
        self._task.start(30)

    def stopService(self):
        if self._task.running:
            self._task.stop()
        super().stopService()

    def _beat(self):
        logger.log_info("Heartbeat from plugin service")


def start_plugin_services(server):
    """Hook for attaching additional Twisted services to the Server."""

    heartbeat = HeartbeatService()
    server.services.append(heartbeat)


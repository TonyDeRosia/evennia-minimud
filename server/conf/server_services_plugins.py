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


def start_plugin_services(server):
    """Hook for attaching additional Twisted services to the Server."""

    # The core game requires no extra services.  If you wish to run your
    # own Twisted ``IService`` alongside the Evennia Server, create and
    # start it here.

    # Example (broadcast time every minute):
    #
    #   from twisted.internet import task
    #   from evennia.utils import logger
    #
    #   def announce():
    #       logger.log_info("Tick ", time.time())
    #
    #   t = task.LoopingCall(announce)
    #   t.start(60)
    #   server.services.addService(t)
    #
    # Remove or replace with your own service implementations.

    pass

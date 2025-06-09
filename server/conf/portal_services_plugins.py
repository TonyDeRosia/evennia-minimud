"""
Start plugin services

This plugin module can define user-created services for the Portal to
start.

This module must handle all imports and setups required to start
twisted services (see examples in evennia.server.portal.portal). It
must also contain a function start_plugin_services(application).
Evennia will call this function with the main Portal application (so
your services can be added to it). The function should not return
anything. Plugin services are started last in the Portal startup
process.

"""


def start_plugin_services(portal):
    """Hook for adding custom Twisted services to the Portal."""

    # By default the Portal does not require any extra services.  This
    # function exists solely as an extension point.  To enable one you
    # would import or define a twisted ``IService`` here and attach it to
    # ``portal``.

    # Example (very basic TCP echo service):
    #
    #   from twisted.internet import protocol
    #
    #   class Echo(protocol.Protocol):
    #       def dataReceived(self, data):
    #           self.transport.write(data)
    #
    #   factory = protocol.ServerFactory()
    #   factory.protocol = Echo
    #   portal.application.listenTCP(9000, factory)
    #
    # Remove or modify this sample as needed.

    pass

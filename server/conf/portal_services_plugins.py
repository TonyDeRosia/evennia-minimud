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


from twisted.internet import protocol
from twisted.application import internet


class Echo(protocol.Protocol):
    def dataReceived(self, data):
        self.transport.write(data)


def start_plugin_services(portal):
    """Hook for adding custom Twisted services to the Portal."""

    factory = protocol.ServerFactory()
    factory.protocol = Echo

    # Attach the Echo service to the Twisted application container. The
    # `application` attribute was introduced in newer Evennia versions but
    # older installs may not define it yet, so fall back to the Portal's
    # parent service when needed.
    application = getattr(portal, "application", None) or portal.parent
    application.addService(internet.TCPServer(9000, factory))


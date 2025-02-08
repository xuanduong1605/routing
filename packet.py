from copy import deepcopy


class Packet:
    """
    The Packet class defines packets that clients and routers send in the simulated
    network.

    Parameters
    ----------
    kind
        Either Packet.TRACEROUTE or Packet.ROUTING. Use Packet.ROUTING for all packets
        created by your implementations.
    srcAddr
        The address of the source of the packet.
    dstAddr
        The address of the destination of the packet.
    content
        The content of the packet. Must be a string.
    """

    TRACEROUTE = 1
    ROUTING = 2

    def __init__(self, kind, srcAddr, dstAddr, content=None):
        self.kind = kind
        self.srcAddr = srcAddr
        self.dstAddr = dstAddr
        self.content = content
        self.route = [srcAddr]

    def copy(self):
        """Create a deep copy of the packet.

        This gets called automatically when the packet is sent to avoid aliasing issues.
        """
        content = deepcopy(self.content)
        p = Packet(self.kind, self.srcAddr, self.dstAddr, content=content)
        p.route = list(self.route)
        return p

    def isTraceroute(self):
        """Returns True if the packet is a traceroute packet."""
        return self.kind == Packet.TRACEROUTE

    def isRouting(self):
        """Returns True is the packet is a routing packet."""
        return self.kind == Packet.ROUTING

    def getContent(self):
        """Returns the content of the packet."""
        return self.content

    def addToRoute(self, addr):
        """DO NOT CALL from DVrouter or LSrouter."""
        self.route.append(addr)

    def getRoute(self):
        """DO NOT CALL from DVRouter or LSrouter."""
        return self.route

    def animateSend(self, src, dst, latency):
        """DO NOT CALL from DVRouter or LSrouter."""
        if hasattr(Packet, "animate"):
            Packet.animate(self, src, dst, latency)

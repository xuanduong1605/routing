import time
import queue


class Router:
    """
    The Router base class that handles the details of packet send/receive and link
    changes. Subclasses should override the following methods to implement routing
    algorithm functionalities:

    - __init__
    - handlePacket
    - handleNewLink
    - handleRemoveLink
    - handleTime
    - debugString (optional)

    Parameters
    ----------
    addr
        The address of this router.
    heartbeatTime
        Routing information should be sent at least once every heartbeatTime ms.
    """

    def __init__(self, addr, heartbeatTime=None):
        self.addr = addr
        self.links = {}  # Links indexed by port
        self.linkChanges = queue.Queue()  # Thread-safe queue for link changes
        self.keepRunning = True

    def changeLink(self, change):
        """Add, remove, or change the ccost of a link.

        The `change` argument is a tuple with first element being "add" or "remove".
        """
        self.linkChanges.put(change)

    def addLink(self, port, endpointAddr, link, cost):
        """Add new link to router."""
        if port in self.links:
            self.removeLink(port)
        self.links[port] = link
        self.handleNewLink(port, endpointAddr, cost)

    def removeLink(self, port):
        """Remove link from router."""
        self.links = {p: link for p, link in self.links.items() if p != port}
        self.handleRemoveLink(port)

    def runRouter(self):
        """Main loop of router."""
        while self.keepRunning:
            time.sleep(0.1)
            timeMillisecs = int(round(time.time() * 1000))
            try:
                change = self.linkChanges.get_nowait()
                if change[0] == "add":
                    self.addLink(*change[1:])
                elif change[0] == "remove":
                    self.removeLink(*change[1:])
            except queue.Empty:
                pass
            for port in self.links.keys():
                packet = self.links[port].recv(self.addr)
                if packet:
                    self.handlePacket(port, packet)
            self.handleTime(timeMillisecs)

    def send(self, port, packet):
        """Send a packet out given port."""
        try:
            self.links[port].send(packet, self.addr)
        except KeyError:
            pass

    def handlePacket(self, port, packet):
        """Process incoming packet.

        Subclasses should override this method. The default implementation simply sends
        packet back out the port it arrived.

        This method is called whenever a packet arrives on port number `port`. Check
        whether the packet is a traceroute packet or a routing packet and handle it
        appropriately. Methods and fields of the packet class are defined in packet.py.

        Parameters
        ----------
        port
            The port number on which the packet arrived.
        packet
            The received packet instance.
        """
        self.send(port, packet)

    def handleNewLink(self, port, endpoint, cost):
        """Handle new link.

        Subclasses should override this method. The default implementation is empty.

        This method is called whenever a new link is added on port number `port`
        connecting to a router or client with address `endpoint` and link cost `cost`.
        You should store the argument values in a data structure to use for routing.
        If you want to send packets along this link, call `self.send(port, packet)`.

        Parameters
        ----------
        port
            The port number on which the link was added.
        endpoint
            The address of the other endpoint of the link.
        cost
            The link cost.
        """
        pass

    def handleRemoveLink(self, port):
        """Handle removed link.

        Subclasses should override this method. The default implementation is empty.

        This method is called when the existing link on port number `port` is
        disconnected. You should update the data structures appropriately.

        Parameters
        ----------
        port
            The port number on which the link was removed.
        """
        pass

    def handleTime(self, timeMillisecs):
        """Handle current time.

        Subclasses should override this method. The default implementation is empty.

        This method is called regularly for sending routing packets at regular
        intervals.
        """
        pass

    def debugString(self):
        """Generate a string for debugging in network visualizer.

        Subclasses may override this method.

        This method is called by the network visualization to print current router
        details. Return any string that will be helpful for debugging. This method is
        for your own convenience and will not be graded.
        """
        return f"Mirror router: address {self.addr}"

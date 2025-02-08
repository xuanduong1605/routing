import sys
import threading
import json
import pickle
import signal
import time
import queue
from collections import defaultdict
from client import Client
from link import Link
from router import Router
from DVrouter import DVrouter
from LSrouter import LSrouter

# DVRouter and LSRouter imports placed in main and conditioned by DV|LS
# argument so a syntax error in one of the files will not prevent the other
# from being tested


def json_load_byteified(file_handle):
    return _byteify(json.load(file_handle, object_hook=_byteify), ignore_dicts=True)


def _byteify(data, ignore_dicts=False):
    # If this is a unicode string, return its string representation
    if isinstance(data, str):
        return data.encode("utf-8")
    # If this is a list of values, return list of byteified values
    if isinstance(data, list):
        return [_byteify(item, ignore_dicts=True) for item in data]
    # If this is a dictionary, return dictionary of byteified keys and values
    # but only if we haven't already byteified it
    if isinstance(data, dict) and not ignore_dicts:
        return {
            _byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
            for key, value in data.items()
        }
    # If this is anything else, return it in its original form
    return data


class Network:
    """The Network class maintains all clients, routers, links, and confguration.

    Parameters
    ----------
    netJsonFilepath
        The path to the JSON file that contains the network configurations.
    routerClass
        Whether to use DVrouter, LSrouter, or the default router.
    visualize
        Whether to visualize the network.
    """

    def __init__(self, netJsonFilepath, routerClass, visualize=False):
        # Parse configuration details
        with open(netJsonFilepath, "r") as f:
            netJson = json.load(f)
        self.latencyMultiplier = 100
        self.endTime = netJson["endTime"] * self.latencyMultiplier
        self.visualize = visualize
        if visualize:
            self.latencyMultiplier *= netJson["visualize"]["timeMultiplier"]
        self.clientSendRate = netJson["clientSendRate"] * self.latencyMultiplier

        # Parse and create routers, clients, and links
        self.routers = self.parseRouters(netJson["routers"], routerClass)
        self.clients = self.parseClients(netJson["clients"], self.clientSendRate)
        self.links = self.parseLinks(netJson["links"])

        # Parse link changes
        if "changes" in netJson:
            self.changes = self.parseChanges(netJson["changes"])
        else:
            self.changes = None

        # Parse correct routes and create some tracking fields
        self.correctRoutes = self.parseCorrectRoutes(netJson["correctRoutes"])
        self.threads = []
        self.routes = {}
        self.routesLock = threading.Lock()

    def parseRouters(self, routerParams, routerClass):
        """Parse routes from the `routerParams` dict."""
        routers = {}
        for addr in routerParams:
            routers[addr] = routerClass(addr, heartbeatTime=self.latencyMultiplier * 10)
        return routers

    def parseClients(self, clientParams, clientSendRate):
        """Parse clients from `clientParams` dict."""
        clients = {}
        for addr in clientParams:
            clients[addr] = Client(addr, clientParams, clientSendRate, self.updateRoute)
        return clients

    def parseLinks(self, linkParams):
        """Parse links from the `linkParams` dict."""
        links = {}
        for addr1, addr2, p1, p2, c12, c21 in linkParams:
            link = Link(addr1, addr2, c12, c21, self.latencyMultiplier)
            links[(addr1, addr2)] = (p1, p2, c12, c21, link)
        return links

    def parseChanges(self, changesParams):
        """Parse link changes from the `changesParams` dict."""
        changes = queue.PriorityQueue()
        for change in changesParams:
            changes.put(change)
        return changes

    def parseCorrectRoutes(self, routesParams):
        """Parse correct routes from the `routesParams` dict/"""
        correctRoutes = defaultdict(list)
        for route in routesParams:
            src, dst = route[0], route[-1]
            correctRoutes[(src, dst)].append(route)
        return correctRoutes

    def run(self):
        """Run the network.

        Start threads for each client and router. Start thread to track link changes.
        If not visualizing, wait until end time and print the final routes.
        """
        for router in self.routers.values():
            thread = RouterThread(router)
            thread.start()
            self.threads.append(thread)
        for client in self.clients.values():
            thread = ClientThread(client)
            thread.start()
            self.threads.append(thread)
        self.addLinks()
        if self.changes:
            self.handleChangesThread = HandleChangesThread(self)
            self.handleChangesThread.start()

        if not self.visualize:
            signal.signal(signal.SIGINT, self.handleInterrupt)
            time.sleep(self.endTime / float(1000))
            self.finalRoutes()
            sys.stdout.write("\n" + self.getRouteString() + "\n")
            self.joinAll()

    def addLinks(self):
        """Add links to clients and routers."""
        for addr1, addr2 in self.links:
            p1, p2, c12, c21, link = self.links[(addr1, addr2)]
            if addr1 in self.clients:
                self.clients[addr1].changeLink(("add", link))
            if addr2 in self.clients:
                self.clients[addr2].changeLink(("add", link))
            if addr1 in self.routers:
                self.routers[addr1].changeLink(("add", p1, addr2, link, c12))
            if addr2 in self.routers:
                self.routers[addr2].changeLink(("add", p2, addr1, link, c21))

    def handleChanges(self):
        """Handle changes to links.

        Run this method in a separate thread. Use a priority queue to track the time of
        next change.
        """
        startTime = time.time() * 1000
        while not self.changes.empty():
            changeTime, target, change = self.changes.get()
            currentTime = time.time() * 1000
            waitTime = (changeTime * self.latencyMultiplier + startTime) - currentTime
            if waitTime > 0:
                time.sleep(waitTime / float(1000))

            # Link changes
            if change == "up":
                addr1, addr2, p1, p2, c12, c21 = target
                link = Link(addr1, addr2, c12, c21, self.latencyMultiplier)
                self.links[(addr1, addr2)] = (p1, p2, c12, c21, link)
                self.routers[addr1].changeLink(("add", p1, addr2, link, c12))
                self.routers[addr2].changeLink(("add", p2, addr1, link, c21))
            elif change == "down":
                addr1, addr2 = target
                p1, p2, _, _, link = self.links[(addr1, addr2)]
                self.routers[addr1].changeLink(("remove", p1))
                self.routers[addr2].changeLink(("remove", p2))

            # Update visualization
            if hasattr(Network, "visualizeChangesCallback"):
                Network.visualizeChangesCallback(change, target)

    def updateRoute(self, src, dst, route):
        """
        Callback function used by clients to update the current routes taken by
        traceroute packets.
        """
        self.routesLock.acquire()
        timeMillisecs = int(round(time.time() * 1000))
        isGood = route in self.correctRoutes[(src, dst)]
        try:
            _, _, currentTime = self.routes[(src, dst)]
            if timeMillisecs > currentTime:
                self.routes[(src, dst)] = (route, isGood, timeMillisecs)
        except KeyError:
            self.routes[(src, dst)] = (route, isGood, timeMillisecs)
        finally:
            self.routesLock.release()

    def getRouteString(self, labelIncorrect=True):
        """
        Create a string with all the current routes found by traceroute packets and
        whether they are correct.
        """
        self.routesLock.acquire()
        routeStrings = []
        allCorrect = True
        for src, dst in self.routes:
            route, isGood, _ = self.routes[(src, dst)]
            info = "" if (isGood or not labelIncorrect) else "Incorrect Route"
            routeStrings.append(f"{src} -> {dst}: {route} {info}")
            if not isGood:
                allCorrect = False
        routeStrings.sort()
        if allCorrect and len(self.routes) > 0:
            routeStrings.append("\nSUCCESS: All Routes correct!")
        else:
            routeStrings.append("\nFAILURE: Not all routes are correct")
        routeString = "\n".join(routeStrings)
        self.routesLock.release()
        return routeString

    def getRoutePickle(self):
        """Create a pickle with the current routes found by traceroute packets."""
        self.routesLock.acquire()
        routePickle = pickle.dumps(self.routes)
        self.routesLock.release()
        return routePickle

    def resetRoutes(self):
        """Reset the routes found by traceroute packets."""
        self.routesLock.acquire()
        self.routes = {}
        self.routesLock.release()

    def finalRoutes(self):
        """Have the clients send one final batch of traceroute packets."""
        self.resetRoutes()
        for client in self.clients.values():
            client.lastSend()
        time.sleep(4 * self.clientSendRate / float(1000))

    def joinAll(self):
        if self.changes:
            self.handleChangesThread.join()
        for thread in self.threads:
            thread.join()

    def handleInterrupt(self, signum, _):
        self.joinAll()
        print("")
        quit()


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python network.py "
            "[networkSimulationFile.json] "
            "[DV|LS (router class, optional)]"
        )
        return

    netCfgFilepath = sys.argv[1]
    RouterClass = Router
    if len(sys.argv) >= 3:
        if sys.argv[2] == "DV":
            RouterClass = DVrouter
        elif sys.argv[2] == "LS":
            RouterClass = LSrouter

    net = Network(netCfgFilepath, RouterClass, visualize=False)
    net.run()
    return


class RouterThread(threading.Thread):
    def __init__(self, router):
        threading.Thread.__init__(self)
        self.router = router

    def run(self):
        self.router.runRouter()

    def join(self, timeout=None):
        # Terrible style (think about changing) but works like a charm
        self.router.keepRunning = False
        super(RouterThread, self).join(timeout)


class ClientThread(threading.Thread):

    def __init__(self, client):
        threading.Thread.__init__(self)
        self.client = client

    def run(self):
        self.client.runClient()

    def join(self, timeout=None):
        # Terrible style (think about changing) but works like a charm
        self.client.keepRunning = False
        super(ClientThread, self).join(timeout)


class HandleChangesThread(threading.Thread):

    def __init__(self, network):
        threading.Thread.__init__(self)
        self.network = network

    def run(self):
        self.network.handleChanges()


if __name__ == "__main__":
    main()

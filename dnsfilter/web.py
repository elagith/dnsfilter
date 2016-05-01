#!/usr/bin/python
#
# Copyright 2016 Deany Dean
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
import argparse
import json
import logging
from twisted.internet import reactor
from twisted.web import server, resource, http
import whitelists

"""
Module containing the web interface
"""

_LOG = logging.getLogger("dnsfilter.web")

class WebResource(resource.Resource):

    """
    Base resource type
    """

    def render(self, request):
        _LOG.info("Request received: %s", request)
        
        response = resource.Resource.render(self, request)
        return _get_response(request, response)

class RootWebResource(WebResource):

    """
    The handler for the root resources
    """

    def __init__(self, args):
        WebResource.__init__(self)
        self.putChild("domains", DNSFilterWebservice(args.url))
        self.putChild("admin", AdminWebHandler())

    def getChild(self, path, request):
        return WelcomeHandler()

class WelcomeHandler(WebResource):
    
    """
    The handler for the welcome page
    """

    def render_GET(self, request):
        return "WELCOME\n"

class AdminWebHandler(WebResource):
   
    """
    The handler for the admin UI
    """

    def render_GET(self, request):
        return "ADMIN UI NOT IMPLEMENTED\n"

class DNSFilterWebservice(WebResource):

    """
    The handler for the webservice interface
    """

    def __init__(self, storage_url):
        self.storage_url = storage_url
        WebResource.__init__(self)

    def getChild(self, path, request):
        return DNSFilterWebservice(self.storage_url)

    def render_POST(self, request):
        """
        Add a new domain entry
        """
        if request.path == "/domains":
            if "domain" not in request.args.keys():
                request.setResponseCode(http.BAD_REQUEST)
                return "BAD REQUEST\n"

            domain = request.args["domain"][0]
            wl = _get_whitelist(self.storage_url)

            if not wl.contains(domain):
                _LOG.info("Adding domain %s for request %s", domain, request)
                wl.add(domain)
            
            request.setHeader("Location", "/domains/"+domain)
            return "CREATED\n" 
        else:
            request.setResponseCode(http.NOT_FOUND) 
            return "NOT FOUND\n"

    def render_GET(self, request):
        """
        Read the list of configure domains
        """
        if request.path == "/domains":
            _LOG.debug("Getting domains for %s", request)
            result = []

            for domain in _get_whitelist(self.storage_url).get_all():
                result.append(domain)

            _LOG.debug("Got domains %s for request %s", result, request)
            return result
        else:
            request.setResponseCode(http.NOT_FOUND)
            return "NOT FOUND\n"

    def render_DELETE(self, request):
        """
        Delete a domain entry
        """
        if request.path.startswith("/domains/"):
            domain = request.path.replace("/domains/", "")
            wl = _get_whitelist(self.storage_url)
            if wl.contains(domain):
                _LOG.info("Deleting domain %s for request %s", domain, request)
                wl.delete(domain)
                return "DELETED\n"
            else:
                request.setResponseCode(http.NOT_FOUND) 
                return "NOT FOUND\n"   
        else:
            request.setResponseCode(http.NOT_FOUND) 
            return "NOT FOUND\n"

    def render_PUT(self, request):
        request.setResponseCode(http.NOT_IMPLEMENTED) 
        return "NOT IMPLEMENTED\n"

def _get_whitelist(url):
    return whitelists.load(url)

def _get_response_str(data):
    if isinstance(data, basestring) or not hasattr(data, "__iter__"):
        return str(data)
    return '\n'.join((str(i) for i in data))+"\n"

def _get_response(request, data):
    content_type = request.getHeader("Content-Type")

    if content_type == "application/json":
        return json.dumps(data)
    else:
        return _get_response_str(data)

def init(args):
    # Set the default logging config
    FMT = '%(asctime)-15s [%(levelname)s] [%(module)s:%(lineno)d]  %(message)s'
    level = logging.INFO
    if args.debug:
        level = logging.DEBUG
    elif args.quiet:
        level = logging.ERROR
    logging.basicConfig(level=level, format=FMT)

def start(args):
    """
    Run the dnsfilter web interface.
    """
    web = RootWebResource(args)

    reactor.listenTCP(args.port, server.Site(web), 80, args.addr)

    _LOG.info("DNS filter web listening on %s:%d...", args.addr, args.port)
    reactor.run()

# Read options from CLI
parser = argparse.ArgumentParser(description="Start the DNS filter web")
parser.add_argument('--addr', nargs='?', type=str, default="", 
    help="IP address to listen on")
parser.add_argument('--port', nargs='?', type=int, default=8080,
    help="Port to listen on")
parser.add_argument('--storage-url', nargs='?', type=str,
    default="mongo:localhost:27017:dnsfilter", help="A storage service to use",
    dest="url")
parser.add_argument("--debug", action="store_true", default=False,
    help="Enable debugging mode (verbose logging)")
parser.add_argument("--quiet", action="store_true", default=False,
    help="Enable quiet mode (no logging)")
args = parser.parse_args()

if __name__ == '__main__':
    init(args)
    raise SystemExit(start(args))
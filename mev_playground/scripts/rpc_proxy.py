"""JSON-RPC proxy that routes builder methods to rbuilder and everything else to Reth.

Contender calls eth_chainId on the builder URL, but rbuilder only supports
eth_sendBundle and eth_sendRawTransaction. This proxy sits in front of rbuilder
and forwards standard RPC calls to Reth while passing bundle calls to rbuilder.

Environment variables:
    BUILDER_URL: rbuilder JSON-RPC URL (e.g. http://172.28.3.1:8645)
    RPC_URL: Reth JSON-RPC URL (e.g. http://172.28.1.1:8545)
    PROXY_PORT: Port to listen on (default: 8650)
"""

import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import Request, urlopen
from urllib.error import URLError

BUILDER_URL = os.environ["BUILDER_URL"]
RPC_URL = os.environ["RPC_URL"]
PROXY_PORT = int(os.environ.get("PROXY_PORT", "8650"))

BUILDER_METHODS = {"eth_sendBundle", "eth_sendRawTransaction"}


class ProxyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            request = json.loads(body)
            method = request.get("method", "")
        except (json.JSONDecodeError, AttributeError):
            method = ""

        target = BUILDER_URL if method in BUILDER_METHODS else RPC_URL

        try:
            req = Request(target, data=body, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=30) as resp:
                response_body = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(response_body)
        except URLError as e:
            error = json.dumps({"jsonrpc": "2.0", "error": {"code": -32000, "message": str(e)}, "id": request.get("id")})
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(error.encode())

    def log_message(self, format, *args):
        print(f"{args[0]}", flush=True)


if __name__ == "__main__":
    print(f"RPC proxy listening on :{PROXY_PORT}", flush=True)
    print(f"  Builder methods ({', '.join(BUILDER_METHODS)}) -> {BUILDER_URL}", flush=True)
    print(f"  All other methods -> {RPC_URL}", flush=True)
    server = HTTPServer(("0.0.0.0", PROXY_PORT), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

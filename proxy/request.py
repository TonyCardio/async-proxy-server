import re
from urllib.parse import urlparse

REGEX_HEADER = re.compile(r'(.+?): (.+)')
REGEX_KEEP_ALIVE = re.compile(r'keep-alive', re.IGNORECASE)


class Request:
    """Implements request to Proxy"""

    def __init__(self, request_lines):
        first_line = request_lines[0]
        method_url_protocol = first_line.split(" ")
        self.method = method_url_protocol[0]
        self.remote_host, self.remote_port = self.get_host_port(
            method_url_protocol[1])
        self.headers = self.parse_headers(request_lines[1:])
        self.lines = request_lines
        self.is_keep_alive = False
        self.token = None

    def parse_headers(self, headers_lines):
        """Parse headers from headers lines"""
        headers = {}
        for header in headers_lines:
            match = REGEX_HEADER.search(header)
            if match:
                headers[match.group(1)] = match.group(2)

        if "Host" in headers:
            self.remote_host, self.remote_port = self.get_host_port(
                headers["Host"])

        if "Proxy-Authorization" in headers:
            self.token = headers["Proxy-Authorization"]

        conn_header = "Connection" if "Connection" in headers \
            else "Proxy-Connection" if "Proxy-Connection" in headers else None

        if conn_header:
            self.is_keep_alive = True if REGEX_KEEP_ALIVE.search(
                headers[conn_header]) else False

        return headers

    def get_host_port(self, url):
        """
        Get remote host port from url
        Depends on request method type
        """
        host_port = url.split(":")

        if self.method == "CONNECT":
            remote_host, remote_port = host_port
        else:
            parsed_url = urlparse(url)
            remote_port = parsed_url.port if parsed_url.port else 80
            remote_host = parsed_url.hostname if parsed_url.hostname \
                else host_port[0]

        return remote_host, remote_port

    def get_encoded_lines(self):
        """Get list of bytes request lines"""
        return [(line + "\r\n").encode() for line in self.lines]

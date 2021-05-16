import asyncio
import traceback
from .request import Request
from .token_auth import ProxyTokenAuth
from .token_auth import ProxyTokenAuthError

auth = ProxyTokenAuth()


class Proxy:
    """Implements proxy-server"""

    def __init__(self,
                 host,
                 port,
                 banned_hosts=None,
                 with_auth=False,
                 tokens=None):
        self.host = host
        self.port = port
        self.banned_hosts = set(banned_hosts) if banned_hosts else set()
        self.tokens = set(tokens) if tokens else set()
        self.with_auth = with_auth
        auth.set_token_verifier(self.is_valid_token)

    async def is_valid_token(self, token):
        """Check token validity"""
        return not self.with_auth or token in self.tokens

    @staticmethod
    async def pipe(reader, writer):
        """Connect reader to writer"""
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    writer.write_eof()
                    await writer.drain()
                    return
                else:
                    writer.write(data)
                    await writer.drain()
        except (OSError, asyncio.IncompleteReadError) as e:
            print(f"(pipe) {str(e)}")
            pass

    @staticmethod
    async def get_request(local_reader):
        """Get first request from client"""
        data = ""
        while True:
            try:
                line = await local_reader.readline()
                if line != b'':
                    data += line.decode()
                if line == b'\r\n':
                    break
                if not line:
                    break
            except OSError as e:
                break
            except ConnectionResetError as e:
                break

        return data

    @staticmethod
    def loop_exception_handler(loop, context):
        """Handle special loop exceptions"""
        exception = context.get("exception")
        transport = context.get("transport")
        if exception:
            if isinstance(exception, TimeoutError):
                if transport:
                    transport.abort()
                    return
            if isinstance(exception, OSError):
                # operation on non-socket on Windows, because fd == -1
                # the semaphore timeout period has expired on Windows
                IGNORE_ERRNO = {
                    10038,
                    121,
                }

                FORCE_CLOSE_ERRNO = {
                    113,  # no route to host
                }
                if exception.errno in IGNORE_ERRNO:
                    print("IGNORED")
                    return
                elif exception.errno in FORCE_CLOSE_ERRNO:
                    print("FORCE_CLOSED")
                    if transport:
                        transport.abort()
                        return

        loop.default_exception_handler(context)

    @auth.auth_required
    async def serve_https(self, request, local_reader, local_writer):
        """
        Serve client CONNECT request
        Open tunnel and connect client writer to remote server reader
        """
        try:
            remote_reader, remote_writer = await asyncio.open_connection(
                request.remote_host, request.remote_port)
        except Exception as e:
            print(f"(serve_https) '{request.remote_host}:"
                  f"{request.remote_port}' {str(e)} ")
            return

        local_writer.write(b'HTTP/1.1 200 Connection established\r\n\r\n')
        await local_writer.drain()

        task_cli_to_serv = asyncio.ensure_future(
            Proxy.pipe(local_reader, remote_writer))
        task_serv_to_cli = asyncio.ensure_future(
            Proxy.pipe(remote_reader, local_writer))

        await asyncio.wait([task_cli_to_serv, task_serv_to_cli],
                           return_when=asyncio.FIRST_COMPLETED)

        task_cli_to_serv.cancel()
        task_serv_to_cli.cancel()

        remote_writer.close()
        await remote_writer.wait_closed()

    @auth.auth_required
    async def serve_http(self, request, local_reader, local_writer):
        """
        Serve client HTTP requests
        Check keep-alive request
        """
        try:
            remote_reader, remote_writer = await asyncio.open_connection(
                request.remote_host, request.remote_port)
        except Exception as e:
            print(f"(serve_http) '{request.remote_host}:"
                  f"{request.remote_port}' {str(e)} ")
            return

        remote_writer.writelines(request.get_encoded_lines())
        await remote_writer.drain()
        await Proxy.pipe(remote_reader, local_writer)

        if request.is_keep_alive:
            task_cli_to_serv = asyncio.ensure_future(
                Proxy.pipe(local_reader, remote_writer))
            task_serv_to_cli = asyncio.ensure_future(
                Proxy.pipe(remote_reader, local_writer))

            await asyncio.wait([task_cli_to_serv, task_serv_to_cli],
                               return_when=asyncio.FIRST_COMPLETED)

            task_cli_to_serv.cancel()
            task_serv_to_cli.cancel()

        remote_writer.close()
        await remote_writer.wait_closed()

    async def handle_client(self, local_reader, local_writer):
        """
        Get first request from client
        Decide is it HTTP or HTTPS
        """
        request = await Proxy.get_request(local_reader)

        if not len(request):
            return

        request_lines = request.split('\r\n')[:-1]

        if len(request_lines) < 2:
            return

        request = Request(request_lines)
        if request.remote_host in self.banned_hosts:
            local_writer.write(b'BAN')
            return

        try:
            if request.method == 'CONNECT':
                await self.serve_https(request, local_reader, local_writer)
            else:
                await self.serve_http(request, local_reader, local_writer)
        except ProxyTokenAuthError:
            print(f"Unathorized {request.remote_host}")
            non_auth_resp = f"{request.method} 401 HTTP/1.1\r\n\r\n"
            local_writer.write(non_auth_resp.encode())

    async def handle_client_wrapper(self, reader, writer):
        """Wrap accepting client"""
        try:
            await self.handle_client(reader, writer)
        except (asyncio.IncompleteReadError, asyncio.CancelledError):
            pass
        except (ConnectionResetError, TimeoutError, BrokenPipeError):
            pass
        except Exception:
            print("TRACEBACK")
            traceback.print_exc()
        finally:
            writer.close()
            await writer.wait_closed()

    def start_proxy(self):
        """Enter point of Proxy"""
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(Proxy.loop_exception_handler)
        coro = asyncio.start_server(
            self.handle_client_wrapper, self.host, self.port)
        server = loop.run_until_complete(coro)

        print(f'Serving on {self.host}:{self.port}')
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            pass

        if hasattr(asyncio, "all_tasks"):
            tasks = asyncio.all_tasks(loop)
        else:
            tasks = asyncio.Task.all_tasks(loop)

        for task in tasks:
            task.cancel()

        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()

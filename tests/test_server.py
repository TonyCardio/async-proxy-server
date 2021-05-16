import os
import sys
import unittest
import time
import asyncio
import aiounittest
from multiprocessing import Process

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             os.path.pardir))

from proxy.async_proxy import Proxy


def start_proxy():
    proxy = Proxy(
        TestProxy.host,
        TestProxy.port,
        with_auth=True,
        tokens=[TestProxy.auth_token],
        banned_hosts=TestProxy.banned)
    proxy.start_proxy()


class TestProxy(aiounittest.AsyncTestCase):
    host = "localhost"
    port = 30303
    auth_token = "123"
    banned = ["anytask.org", "mathprofi.ru"]

    @classmethod
    def setUpClass(cls) -> None:
        cls.proxy = Process(target=start_proxy)
        cls.proxy.start()
        time.sleep(1)

    async def test_connect(self):
        reader, writer = await asyncio.open_connection(
            TestProxy.host, TestProxy.port)
        writer.close()
        await writer.wait_closed()

    async def test_https_should_open_tunnel(self):
        req = [f'CONNECT vk.com:443 HTTP/1.1\r\n',
               f'Host: vk.com:443\r\n',
               f'Proxy-Connection: keep-alive\r\n',
               f'Proxy-Authorization: {TestProxy.auth_token}\r\n\r\n']
        reader, writer = await asyncio.open_connection(
            TestProxy.host, TestProxy.port)

        encoded_req_lines = [x.encode() for x in req]
        writer.writelines(encoded_req_lines)
        await writer.drain()
        resp = await reader.read(4096)
        writer.close()
        await writer.wait_closed()
        self.assertEqual(resp, b'HTTP/1.1 200 Connection established\r\n\r\n')

    async def test_http_returns_200(self):
        req = [f'GET http://anytask.urgu.org/ HTTP/1.1\r\n',
               f'Host: anytask.urgu.org\r\n',
               f'Proxy-Connection: close\r\n',
               f'Proxy-Authorization: {TestProxy.auth_token}\r\n\r\n']
        reader, writer = await asyncio.open_connection(
            TestProxy.host, TestProxy.port)

        encoded_req_lines = [x.encode() for x in req]
        writer.writelines(encoded_req_lines)
        await writer.drain()
        resp = await reader.read(4096)
        writer.close()
        await writer.wait_closed()
        status = resp.decode().split(" ")[1]
        self.assertEqual(status, "200")

    async def test_https_req_to_banned_host_returns_ban_message(self):
        req = [f'CONNECT anytask.org:443 HTTP/1.1\r\n',
               f'Host: anytask.org:443\r\n',
               f'Proxy-Connection: close\r\n',
               f'Proxy-Authorization: {TestProxy.auth_token}\r\n\r\n']
        reader, writer = await asyncio.open_connection(
            TestProxy.host, TestProxy.port)

        encoded_req_lines = [x.encode() for x in req]
        writer.writelines(encoded_req_lines)
        await writer.drain()
        resp = await reader.read(4096)
        writer.close()
        await writer.wait_closed()
        self.assertEqual(resp, b'BAN')

    async def test_http_req_to_banned_host_returns_ban_message(self):
        req = [f'GET http://mathprofi.ru HTTP/1.1\r\n',
               f'Host: mathprofi.ru:443\r\n',
               f'Proxy-Connection: close\r\n',
               f'Proxy-Authorization: {TestProxy.auth_token}\r\n\r\n']
        reader, writer = await asyncio.open_connection(
            TestProxy.host, TestProxy.port)

        encoded_req_lines = [x.encode() for x in req]
        writer.writelines(encoded_req_lines)
        await writer.drain()
        resp = await reader.read(4096)
        writer.close()
        await writer.wait_closed()
        self.assertEqual(resp, b'BAN')

    async def test_https_req_without_auth_returns_401(self):
        req = [f'CONNECT vk.com:443 HTTP/1.1\r\n',
               f'Host: vk.com:443\r\n',
               f'Proxy-Connection: keep-alive\r\n',
               f'Proxy-Authorization: bad-key\r\n\r\n']
        reader, writer = await asyncio.open_connection(
            TestProxy.host, TestProxy.port)

        encoded_req_lines = [x.encode() for x in req]
        writer.writelines(encoded_req_lines)
        await writer.drain()
        resp = await reader.read(4096)
        writer.close()
        await writer.wait_closed()
        status = resp.decode().split(" ")[1]
        self.assertEqual(status, "401")

    async def test_http_req_without_auth_returns_401(self):
        req = [f'GET http://anytask.urgu.org/ HTTP/1.1\r\n',
               f'Host: anytask.urgu.org\r\n',
               f'Proxy-Connection: close\r\n',
               f'Proxy-Authorization: bad-key\r\n\r\n']
        reader, writer = await asyncio.open_connection(
            TestProxy.host, TestProxy.port)

        encoded_req_lines = [x.encode() for x in req]
        writer.writelines(encoded_req_lines)
        await writer.drain()
        resp = await reader.read(4096)
        writer.close()
        await writer.wait_closed()
        status = resp.decode().split(" ")[1]
        self.assertEqual(status, "401")

    async def test_return_empty_resp_when_empty_req(self):
        req = [b'\r\n']

        reader, writer = await asyncio.open_connection(
            TestProxy.host, TestProxy.port)
        writer.writelines(req)
        await writer.drain()
        resp = await reader.read(4096)
        writer.close()
        await writer.wait_closed()
        self.assertEqual(resp, b'')

    @classmethod
    def tearDownClass(cls) -> None:
        cls.proxy.terminate()


if __name__ == '__main__':
    unittest.main()

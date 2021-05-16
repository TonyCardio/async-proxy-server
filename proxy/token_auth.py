from functools import wraps


class ProxyTokenAuthError(Exception):
    """Implements Proxy Unauthorized exc"""

    def __init__(self, text="Unauthorized"):
        self.txt = text


class ProxyTokenAuth:
    """Implements """

    def __init__(self,
                 header="Proxy-Authorization",
                 token_verifier=None):
        self.header = header
        self.token_verifier = token_verifier

    async def _is_authenticated(self, request):
        """Check token_verifier result"""
        token = request.headers.get(self.header, None) if self.header \
            else request.token
        if self.token_verifier:
            return await self.token_verifier(token)
        return False

    def set_token_verifier(self, token_verifier):
        self.token_verifier = token_verifier

    def auth_required(self, handler=None):
        """Wrapper of Proxy auth required coroutines"""

        @wraps(handler)
        async def wrapper(self_obj, request, *args, **kwargs):
            if not await self._is_authenticated(request):
                raise ProxyTokenAuthError

            return await handler(self_obj, request, *args, **kwargs)

        return wrapper

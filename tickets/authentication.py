from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .models import Token


class TokenAuthentication(BaseAuthentication):
    keyword = 'Bearer'

    def authenticate(self, request):
        auth = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth.startswith(f'{self.keyword} '):
            return None
        token_key = auth[len(self.keyword) + 1:]
        try:
            token = Token.objects.select_related('usuario').get(key=token_key)
        except Token.DoesNotExist:
            raise AuthenticationFailed('Token inválido o expirado.')
        if not token.usuario.activo:
            raise AuthenticationFailed('Usuario inactivo.')
        return (token.usuario, token)

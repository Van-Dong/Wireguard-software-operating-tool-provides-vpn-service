# middleware change access-token cookie to HTTP Header Authorization
class AccessTokenMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before  the view (and later middleware) are called.
        access_token = request.COOKIES.get('access_token')
        if access_token:
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
            
            from rest_framework_simplejwt.tokens import UntypedToken
            from rest_framework_simplejwt.authentication import JWTAuthentication
            try:
                untyped_token = UntypedToken(access_token)
                user = JWTAuthentication().get_user(untyped_token)
            except (Exception):
                from django.shortcuts import redirect
                response = redirect('/login/')  # 'home' là tên URL 
                response.delete_cookie('access_token') 
                return response
                   
        response = self.get_response(request)
        return response

from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from django.http import HttpResponse
from channels.auth import AuthMiddlewareStack


@database_sync_to_async
def get_user_from_token(token_str):
    User = get_user_model()
    try:
        untyped_token = UntypedToken(token_str) # token hết hạn or không hợp lệ sẽ sinh ra ngoại lệ
        user = JWTAuthentication().get_user(untyped_token)
        if user is not None: 
            return user
        else:
            # No user associated with the JWT
            return AnonymousUser()

    except (InvalidToken, TokenError, User.DoesNotExist) as e:
        print("Invalid token: ", e)
        return AnonymousUser()

# Parse cookie string to cookie dict 
def parse_cookie(cookie_strings):
    cookie_dict = {}
    cookie_pairs = cookie_strings.split('; ')
    for pair in cookie_pairs:
        key, value = pair.split('=', 1)
        cookie_dict[key] = value
    return cookie_dict

class TokenAuthMiddleware: 
    def __init__(self, app):
        # Store the ASGI application we were passed
        self.app = app

    async def __call__(self, scope, receive, send):
        # Look up user from query string (you should also do things like
        # checking if it is a valid user ID, or if scope["user"] is already
        # populated).
        headers_dict = dict((k.decode('utf-8'), v.decode('utf-8'))
                            for k, v in scope['headers'])   # convert header to dict

        if 'cookie' in headers_dict:
            cookie_dict = parse_cookie(headers_dict['cookie'])
            if 'access_token' in cookie_dict:
                # Check user có xác thực không ?
                # print(cookie_dict['access_token'])
                jwtToken = cookie_dict['access_token']
                # print('access_token', jwtToken)
                scope['user'] = await get_user_from_token(jwtToken)
                if scope['user'].is_authenticated and scope['user'].is_staff:
                    print('Client access to /events/.')
                    return await self.app(scope, receive, send)
                
                
        # Xác thực thất bại 
        print('Unauthorized for /events/. Need Admin Account.')
        # scope['user'] = AnonymousUser()
        # return await self.app(scope, receive, send)
        return HttpResponse(status=400)

def TokenAuthMiddlewareStack(inner):
    return AuthMiddlewareStack(TokenAuthMiddleware(inner)) 

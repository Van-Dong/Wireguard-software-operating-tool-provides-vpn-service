from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenViewBase
from vpn_manager.serializers.serializers import CustomTokenObtainPairSerializer  # phải liên kết với gói khác nên hơi phiền phức 
from rest_framework_simplejwt.views import TokenViewBase
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import render
from django.shortcuts import redirect


# from .serializers import CustomTokenOb


import logging
# Tạo logger
logger = logging.getLogger(__name__)


# /login/ GET
class LoginView(APIView):
    def get(self, request):
        if request.user.is_authenticated:
            if request.user.is_staff:
                return redirect('/dashboard/')   
            return redirect('/wg-client/peer/')
        logger.info("[%s] [] - HTTP GET /login/ 200 - Access /login/", request.META['REMOTE_ADDR'])
        return render(request, 'login/login.html')

# /api/token/ POST
class CustomTokenObtainPairView(TokenViewBase):
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs): 
        serializer = self.get_serializer(data=request.data) 
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e: 
            logger.warning("[%s] [] - HTTP POST /api/token/ 401 - Attempt to log in with failed account: %s", request.META['REMOTE_ADDR'], request.data)
            return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

        data = serializer.validated_data
        try: # giải mã jwt token string và lấy trường jti trong token 
            decoded_token = UntypedToken(data['access'])  # class UntypedToken
            jti = decoded_token.payload['jti']
        except (InvalidToken, TokenError):
            jti = ''
        
        response = Response(data, status=status.HTTP_200_OK)
          
        # Set the access token in the cookie
        response.set_cookie(
            key = 'access_token',
            value = data['access'],
            max_age=3600*3,   # seconds
            httponly = True,
            samesite = 'Lax'  # hoặc 'Strict'
        )
        logger.info("[%s] [%s] - HTTP POST /api/token/ 200 - Account %s has logged into the application", request.META['REMOTE_ADDR'], jti, request.user.username)
        
        return response  

# /logout/ GET
class LogoutView(APIView):
    permission_classes = (IsAuthenticated, )
    
    def get(self, request):
    
        # return response
        response = redirect('/login/')  # 'home' là tên URL 
        response.delete_cookie('access_token')
        logger.info("[%s] [%s] - HTTP GET /logout/ 200 - Account %s has logged out", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username)
        return response

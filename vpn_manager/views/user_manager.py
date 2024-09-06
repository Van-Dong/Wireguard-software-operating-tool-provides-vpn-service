from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import render
# from vpn_manager.models.models import User
from vpn_manager.models.user import User
from vpn_manager.serializers.serializers import UserSerializer

import logging
# Tạo logger
logger = logging.getLogger(__name__)


# /profile/ GET POST
class ProfileView(APIView):
    permission_classes = (IsAuthenticated, )
    
    def get(self, request):
        # logger.info(f"[{request.META.get('REMOTE_ADDR')}] [{request.auth['jti']}] - Account {request.user.username} access /profile/ - HTTP GET /profile/ 200")
        logger.info("[%s] [%s] - HTTP GET /profile/ 200 - Account %s access /profile/", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username)
        return render(request, 'profile/profile.html')
    
    def post(self, request):
        # request.user contain: name, id, email,...
        id = request.user.id
        user = User.objects.get(pk=id)
        
        if str(id) != request.data['id']:
            # logger.error(f"[{request.META.get('REMOTE_ADDR')}] [{request.auth['jti']}] - Account {request.user.username} update id user not match: current user id={id} and update user id={request.data['id']} - HTTP POST /profile/ 400")
            logger.error("[%s] [%s] - HTTP POST /profile/ 400 - Account %s update id user not match: current user id=%d and update user id=%d", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username, id, int(request.data['id']))
            return Response({"status": False, "message": "An error occurred!"}, status=status.HTTP_400_BAD_REQUEST)
        
        if len(request.data['password']) >= 6:
            user.set_password(request.data['password'])
            user.save() 
            logger.info("[%s] [%s] - HTTP POST /profile/ 200 - Account %s updated password!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username)
            return Response({"status": True, "message": "Change password successfully!"})
        
        logger.warning("[%s] [%s] - HTTP POST /profile/ 400 - Account %s update user password is shorter than 6", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username)
        return Response({"status": False, "message": "Password is short!"}, status=status.HTTP_400_BAD_REQUEST)    
       
# /users/  GET
# /users/{id}  GET POST PATCH DELETE
class UserView(ModelViewSet):
    permission_classes = (IsAuthenticated, IsAdminUser, )

    queryset = User.objects.filter(is_active=True, is_staff=False)
    serializer_class = UserSerializer
    
    allowed_methods = ('GET', 'POST', 'PATCH', 'DELETE')
    
    def list(self, request):
        queryset = User.objects.filter(is_active=True)
        serializer = UserSerializer(queryset, many=True)
        logger.info("[%s] [%s] - HTTP GET /users/ 200 - Account %s access /users/", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username)
        return render(request, 'settings/user_settings.html', context={"users": serializer.data})

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        request.data['password'] = "***"
        logger.info("[%s] [%s] - HTTP POST /users/ 200 - Account %s created user with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username, request.data)
        return response

    # /users/{pk}  PATCH
    def partial_update(self, request, pk):
        user = User.objects.get(pk=pk)
        if request.data['password'] == '':
            del request.data['password']
        serialized = UserSerializer(user, data=request.data, partial=True)

        if not serialized.is_valid():
            logger.info("[%s] [%s] - HTTP PATCH /users/%s/ 400 - Account %s updated user id=%s was error with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], pk, request.user.username, pk, request.data)
            return Response(serialized.errors, status=status.HTTP_400_BAD_REQUEST)
        serialized.save()
 
        if 'password' in request.data:
            user.set_password(request.data['password'])
            user.save()
        
        request.data['password'] = '***'
        logger.info("[%s] [%s] - HTTP PATCH /users/%s/ 200 - Account %s updated user id=%s success fully with data: %s!", request.META['REMOTE_ADDR'], request.auth['jti'], pk, request.user.username, pk, request.data)
        return Response(serialized.data, status=status.HTTP_200_OK)

    # /user/{pk}  DELETE
    def destroy(self, request, pk):
        try:
            user = User.objects.get(pk=pk)
            user.is_active = False
            user.save()
            logger.info("[%s] [%s] - HTTP DELETE /users/%s/ 200 - Account %s deleted user id=%s successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], pk, request.user.username, pk)
            return Response(data={"status": True, "message": "Delete user successfully!"}, status = status.HTTP_200_OK)
        except User.DoesNotExist:
            logger.info("[%s] [%s] - HTTP DELETE /users/%s/ 200 - Account %s deleted user id=%s falied with error: User doesn't exist!", request.META['REMOTE_ADDR'], request.auth['jti'], pk, request.user.username, pk)
            return Response(data={"status": False, "message": "User doesn't exist!"}, status = status.HTTP_400_BAD_REQUEST)


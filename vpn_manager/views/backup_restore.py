from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.http import HttpResponse  # for download file
from django.shortcuts import render
from django.core.management import call_command
from io import StringIO
from django.db import transaction 

from vpn_manager.config import *
from datetime import datetime
from django.apps import apps
import os, json, tempfile, time


import logging
# Tạo logger
logger = logging.getLogger(__name__)

# /backup/ POST GET
class BackupView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser, )
    
    def get(self, request):
        backup_all_database_path = BACKUP_FOLDER_PATH + 'all_database' 
        times = []
        
        list_file_backup = os.listdir(backup_all_database_path)
        list_file_backup.sort(reverse=True)
        
        
        for time in list_file_backup:
            time = time.split('.')[0]
            time = {
                'ms': time,
                'datetime': datetime.fromtimestamp(int(time)).strftime("%d/%m/%Y %H:%M:%S")
            }
            times.append(time)
        logger.info("[%s] [%s] - HTTP GET /backup/ 200 - Account %s access /backup/!", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username)  
        return render(request, 'utilities/backup.html', context={'times': times})
        
    
    def post(self, request):
        # copy_dir('server', 'backup')
        is_success = self.backup()
        if is_success:
            return Response(data={"status": False, "message": "Back up is successfully!"}, status = status.HTTP_200_OK)
        return Response(data={"status": False, "message": "Back up is failed!"}, status = status.HTTP_400_BAD_REQUEST)
    
    def backup(self):
        current_time = round(time.time())  # second from 1970
        # date = datetime.fromtimestamp(current_time)  # convert seconds to datetime
        output_file = f'all_database/{current_time}.json'
    
        try:
            with open(BACKUP_FOLDER_PATH + output_file, 'w') as f:
                call_command('dumpdata', 'vpn_manager', stdout=f, indent=4)
            return True
        except Exception as e:
            return False

# /recover/<str:time>/ POST
class RecoverView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser, )
    
    def get(self, request, time):
        backup_file_path = BACKUP_FOLDER_PATH + 'all_database/' + f'{time}.json' 
        if os.path.exists(backup_file_path):
            try:
                with open(backup_file_path, 'r') as f:
                    content = f.read()
                response = HttpResponse(content, content_type='application/json')
                response['Content-Disposition'] = f'attach; filename=database_backup_{time}.json'
                return response
            except:
                return Response(data={"status": False, "message": "File not found!"}, status=status.HTTP_404_NOT_FOUND)
          
    def post(self, request, time):
        backup_file_path = BACKUP_FOLDER_PATH + 'all_database/' + f'{time}.json' 
        if os.path.exists(backup_file_path):
            temp_file =  BACKUP_FOLDER_PATH + 'temp/tmp_database.json'  # lưu database dự phòng để phòng có lỗi khi loaddata 
          
            try:
                call_command('dumpdata', 'vpn_manager', '-o', temp_file, indent=4)
                with transaction.atomic():
                    call_command('flush', '--no-input')
                    call_command('loaddata', backup_file_path)
                return Response(data={"status": True, "message": "Recover is successfully!"}, status = status.HTTP_200_OK)
            except Exception as e:   
                call_command('loaddata', temp_file)  # backup if recover failed
                return Response(data={"status": False, "message": f"An error occurred: {e}!"}, status = status.HTTP_500_INTERNAL_SERVER_ERROR)           
        else:
            return Response(data={"status": False, "message": "File backup doesn't exist!"}, status = status.HTTP_400_BAD_REQUEST)
    
    # for backup all_database
    def delete(self, request, time):
        backup_file_path = BACKUP_FOLDER_PATH + 'all_database/' + f'{time}.json' 
        if os.path.exists(backup_file_path):
            try:
                os.remove(backup_file_path)
                
                return Response(data={"status": True, "message": "Delete backup file successfully!"}, status = status.HTTP_200_OK)
            except Exception as e:
                return Response(data={"status": False, "message": str(e)}, status = status.HTTP_400_BAD_REQUEST)
        else:
            return Response(data={"status": False, "message": "File backup doesn't exist!"}, status = status.HTTP_400_BAD_REQUEST)
 

# /export/<str: model_name>/
class ExportView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser, )
    def get(self, request, model_name):
        model_name = model_name.lower()
        if model_name in ['user', 'vpnconnection', 'interface', 'globalsetting']:
            out = StringIO()
            call_command('dumpdata', f'vpn_manager.{model_name}', stdout=out, indent=4)
            # content = out.getvalue()
            response = HttpResponse(out.getvalue(), content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename={model_name}.json'
            
            logger.info("[%s] [%s] - HTTP GET /export/%s/ 200 - Account %s export model %s successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], model_name, request.user.username, model_name)  
            return response
        elif model_name == 'all':
            out = StringIO()
            call_command('dumpdata', 'vpn_manager', stdout=out, indent=4)
            content = out.getvalue()
            response = HttpResponse(content, content_type='application/json')
            response['Content-Disposition'] = 'attachment; filename=database_backup.json'
            
            logger.info("[%s] [%s] - HTTP GET /export/%s/ 200 - Account %s export all database successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], model_name, request.user.username)  
            return response
        else:
            return Response(data={"status": False, "message": "Model isn't exist!"}, status=status.HTTP_404_NOT_FOUND)

class ImportView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser, )
    
    def post(self, request, model_name):
        # validate file
        result = self.validate_file_import(request.FILES)
        if result['status'] == False:
            return Response(data=result, status=status.HTTP_400_BAD_REQUEST)
        
        # file_content = uploaded_file.read().decode('utf-8')  # file content khi read la dang bytes
        result = self.load_data(request.FILES['file'], model_name)
        if result['status'] == True:
            
            logger.info("[%s] [%s] - HTTP POST /import/%s/ 200 - Account %s load data from file successfully!", request.META['REMOTE_ADDR'], request.auth['jti'], model_name, request.user.username)  
            return Response(data=result)
        else:
            return Response(data=result, status=status.HTTP_400_BAD_REQUEST)

    # class ImportView
    def validate_file_import(self, fileField):
        # fileField not upload
        if 'file' not in fileField: 
            return {"status": False, "message": "No file provided"}

        file = fileField['file']

        # check file is .json
        if not file.name.lower().endswith('.json') or not file.content_type == 'application/json':
            return {"status": False, "message": "Type of file must be .json"}
    
    # check size is limit
        if file.size > MAX_UPLOAD_FILE_SIZE:
            return {"status": False, "message": f"Size file must be less than {MAX_UPLOAD_FILE_SIZE/1024/1024} MB!"}
    
        try:
            content = json.load(file)
            return {"status": True}
        except Exception as e:
            return {"status": False, "message": f"Content file is invalid: {e}!"}

    # load_data from file, check it, and replace for current data
    def load_data(self, file, model_name):
    
        temp_file_path = ''
        try: # save file import to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json', dir=BACKUP_FOLDER_PATH + 'temp') as temp_file:
                for chunk in file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
        except Exception as e:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            return {"status": False, "message": f"Error in proccessing file: {e}"}

        file_data_before_recover =  BACKUP_FOLDER_PATH + 'temp/tmp_data_before.json'  # lưu database dự phòng để phòng có lỗi khi loaddata 
        if model_name == "all":  # all database      
            # run command load data (take temp file is input)
            
            try: 
                call_command('dumpdata', 'vpn_manager', '-o', file_data_before_recover, indent=4) # data du phong co loi xay ra
                call_command('loaddata', temp_file_path, app_label='vpn_manager')
                os.remove(temp_file_path)
            except Exception as e:
                os.remove(temp_file_path)
                call_command('loaddata', file_data_before_recover)  # rollback khi co loi xay ra
                return {"status": False, "message": f"An error occurred: {e}"}
    
        else:  # online one_database
            exclude_model = LIST_MODEL.copy()
            exclude_model.remove(f'vpn_manager.{model_name}')
            try:
                call_command('dumpdata', f'vpn_manager.{model_name}', '-o', file_data_before_recover, indent=4)
                if model_name in ['globalsetting', 'interface']:
                    self.empty_model(model_name)
            
                call_command('loaddata', temp_file_path, app_label='vpn_manager', exclude=exclude_model)
                os.remove(temp_file_path)
            except Exception as e:
                os.remove(temp_file_path)
                call_command('loaddata', file_data_before_recover, app_label='vpn_manager', exclude=exclude_model)
                return {"status": False, "message": f"An error occurred: {e}"} 
        
        return {"status": True, "message": "Load data successfully!"}   

    def empty_model(self, model_name):
    # Lấy model từ tên model
        try:
            Model = apps.get_model(app_label='vpn_manager', model_name=model_name)
        except LookupError:
            # print(f"Model '{model_name}' does not exist.")
            return {"status": False, "message": f"Model '{model_name}' does not exist."}
    
        # Xóa toàn bộ dữ liệu trong bảng
        try:
            Model.objects.all().delete()
            # print(f"All data in {model_name} table has been deleted.")
            return {"status": True}
        except Exception as e:
            # print(f"Failed to delete data in {model_name} table: {str(e)}")
            return {"status": False, "message": f"Failed to delete data in {model_name} table: {str(e)}"}



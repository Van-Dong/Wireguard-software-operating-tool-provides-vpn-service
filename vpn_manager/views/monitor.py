from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.shortcuts import render

# from vpn_manager.models.models import VpnConnection, VpnConnectionStatus
from vpn_manager.models.vpnconnection import VpnConnection
from vpn_manager.models.vpnconnectionstatus import VpnConnectionStatus
from datetime import timedelta
from django.utils import timezone
import logging
from datetime import datetime

# Tạo logger
logger = logging.getLogger(__name__)

# /monitor/ GET
class MonitorView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser, )
    def get(self, request):
        return render(request, 'monitor/monitor.html')

# /dashboard/  GET  ---TEST---
class DashboardView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)  # IsAdminUser: only staff = True. (nhan vien)

    def get(self, request):
        data_five_hours = self.statistic_transfer(hours_ago=5, time_distance=1)
        data_one_day = self.statistic_transfer(days_ago=1, time_distance=4)
        data_one_week = self.statistic_transfer(days_ago=7, time_distance=24)
        data_one_month = self.statistic_transfer(days_ago=28, time_distance=24*7)
        data_peer = self.statistic_peer()
        enabled_peer = [data_peer[1], data_peer[0] - data_peer[1]]
        connected_peer = [data_peer[2], data_peer[0] - data_peer[2]]
        list_vpnconnection = VpnConnection.objects.all().values('id', 'name').order_by('name')
        list_vpnconnection = list(list_vpnconnection)
        
        logger.info("[%s] [%s] - HTTP GET /dashboard/ 200 - Account %s access /dashboard/", request.META['REMOTE_ADDR'], request.auth['jti'], request.user.username)
        return render(request, 'monitor/dashboard.html', context={
            "enabled_peer": enabled_peer, 
            "connected_peer": connected_peer, 
            "data_five_hours": data_five_hours,
            "data_one_day": data_one_day,
            "data_one_week": data_one_week,
            "data_one_month": data_one_month, 
            "list_vpnconnection": list_vpnconnection,
        })
    
    def statistic_peer(self):
        count_peer = VpnConnection.objects.count()
        count_enable_peer = VpnConnection.objects.filter(enabled=True).count()
        count_peer_connected = VpnConnectionStatus.objects.values('peer').distinct().count()  # -1 đề phòng TH peer = NULL khi reset 
        if VpnConnectionStatus.objects.filter(peer=None).exists():
            count_peer_connected = count_peer_connected - 1
        return [count_peer, count_enable_peer, count_peer_connected]

    # return [transfer30p, transfer1h, transfer1.5h, transfer2h, transfer2.5h, transfer3h]
    def statistic_transfer(self, days_ago=0, hours_ago=0, time_distance=0.5): # time_distance is hour
        now = timezone.now()
        time_ago = now - timedelta(days=days_ago, hours=hours_ago)
        result = VpnConnectionStatus.objects.filter(created_at__gte=time_ago).values_list('peer__id', 'receive', 'transmit', 'type', 'created_at') 
        # values('title', 'author') trả về dạng QuerySet của dict --> có tên trường 
        # nếu dùng values_list('title', 'author') --> trả về dạng querySET của tuple --> không có tên trường

        data = {
            'tx': [], # every 30 hours
            'rx': [],
        }
        distance = timedelta(hours=time_distance)
        cur_time = time_ago + distance
        
        sum_tx = 0
        sum_rx = 0
        for x in reversed(result): # time_ago --> now 
            # đã reset phiên chưa
            if x[3] == 2:
                continue
        
            # Nếu data hiện tại quá mốc hiện tại
            if x[4] < cur_time:
                # kiểm tra xem đang ở mốc nào
                sum_rx += x[1]
                sum_tx += x[2]
            else:
                cur_time += distance
                data['tx'].append(sum_tx)
                data['rx'].append(sum_rx)
                sum_tx = 0
                sum_rx = 0
                # print(cur_time)
                while cur_time < x[4]:
                    data['tx'].append(0)
                    data['rx'].append(0)
                    cur_time += distance
                sum_rx += x[1]
                sum_tx += x[2]
        # Hết vòng lặp thì còn time cuối chư chạy 
        data['tx'].append(sum_tx)
        data['rx'].append(sum_rx)
        cur_time += distance
        
        while cur_time <= now:
            data['tx'].append(0)
            data['rx'].append(0)
            cur_time += distance
            # print(cur_time)
        data['tx'].reverse()
        data['rx'].reverse()
        # print(data)
        
        return data  # phần tử cuối của mỗi mảng trong data là sum rồi 
            
# /statistic-peer/<int:id>/
class StatisticVPNConnectionView(APIView):
    permission_classes = (IsAuthenticated, IsAdminUser)
    
    def get(self, request, id):
        data_one_day = self.statistic_transfer(id, days_ago=1, time_distance=4)
        data_one_week = self.statistic_transfer(id, days_ago=7, time_distance=24)
        list_endpoint = self.statistic_change_endpoint(id)
        return Response(data={"status": True, "data": {
            'data_one_week': data_one_week, 
            'data_one_day': data_one_day,
            'list_endpoint': list_endpoint
            }})
    
    def statistic_transfer(self, id, days_ago=0, hours_ago=0, time_distance=0.5): # time_distance is hour
        now = timezone.now()
        time_ago = now - timedelta(days=days_ago, hours=hours_ago)
        result = VpnConnectionStatus.objects.filter(created_at__gte=time_ago, peer_id=id).values_list('peer__id', 'receive', 'transmit', 'type', 'created_at') 
    
        data = {
            'tx': [], # every 30 hours
            'rx': [],
        }
        distance = timedelta(hours=time_distance)
        cur_time = time_ago + distance
        
        sum_tx = 0
        sum_rx = 0
        for x in reversed(result): # time_ago --> now 
            # đã reset phiên chưa
            if x[3] == 2:
                continue
        
            # Nếu data hiện tại quá mốc hiện tại
            if x[4] < cur_time:
                # kiểm tra xem đang ở mốc nào
                sum_rx += x[1]
                sum_tx += x[2]
            else:
                cur_time += distance
                data['tx'].append(sum_tx)
                data['rx'].append(sum_rx)
                sum_tx = 0
                sum_rx = 0
                # print(cur_time)
                while cur_time < x[4]:
                    data['tx'].append(0)
                    data['rx'].append(0)
                    cur_time += distance
                sum_rx += x[1]
                sum_tx += x[2]
        # Hết vòng lặp thì còn time cuối chư chạy 
        data['tx'].append(sum_tx)
        data['rx'].append(sum_rx)
        cur_time += distance
        
        while cur_time <= now:
            data['tx'].append(0)
            data['rx'].append(0)
            cur_time += distance
            # print(cur_time)
        data['tx'].reverse()
        data['rx'].reverse()
        # print(data)
        
        return data  # phần tử cuối của mỗi mảng trong data là sum rồi 
    
    def statistic_change_endpoint(self, id):
        result = VpnConnectionStatus.objects.filter(peer_id=id, type=1).values_list('curr_endpoint', 'created_at').order_by('-created_at')
        result = list(result) 
        for i in range(len(result)):
            result[i] = list(result[i])
            result[i][1] = result[i][1].strftime("%d/%m/%Y %H:%M:%S")
        return result
    

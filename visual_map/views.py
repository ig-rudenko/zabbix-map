from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required(login_url='accounts/login')
def main(request):
    return render(request, 'main.html')


@login_required(login_url='accounts/login')
def automap(request):
    return render(request, 'automap.html')


@login_required(login_url='accounts/login')
def sendmap(request):
    return render(request, 'zabbix-map.html')
from pyzabbix import ZabbixAPI
from datetime import datetime
import branca
import folium
import os
import sys
from folium.plugins import MousePosition, MeasureControl, Fullscreen
import pandas as pd
from configparser import ConfigParser

cfg = ConfigParser()
cfg.read(f'{sys.path[0]}/conf')
zabbixURL = cfg.get('Zabbix', 'url')
zabbixUser = cfg.get('Zabbix', 'user')
zabbixPassword = cfg.get('Zabbix', 'password')


def get_hosts_with_problem(zabbix_group_id: int) -> dict:
    """
    Определяет недоступные узлы сети для конкретной группы Zabbix, а также их подтверждения проблем
    :param zabbix_group_id: ID Группы в Zabbix
    :return: словарь из ID тех узлов, которые недоступны в этой группе и подтверждения по этим проблемам
    """
    problems = {}  # Конечный словарь
    with ZabbixAPI(server=zabbixURL) as z:
        z.login(user=zabbixUser, password=zabbixPassword)
        print(f'get {zabbix_group_id} group from Zabbix')
        hosts_id = [
            host['hostid'] for host in
            z.host.get(groupids=[f'{zabbix_group_id}'], output=['hostid'], filter={'status': '0'})
        ]

        for id_ in hosts_id:
            device_problem = z.problem.get(hostids=[id_], selectAcknowledges='extend', filter={'name': 'Оборудование недоступно'})
            if device_problem:
                if device_problem[0]['acknowledges']:
                    acknowledges = [[ack['message'], ack['clock']] for ack in device_problem[0]['acknowledges']] or ['']
                    problems[id_] = acknowledges

    return problems


def popup(host_name, acknowledge_messages: list=None):
    """
    Создает всплывающее меню, при нажатии на объект
    :param host_name: Уникальное имя объекта в БД Zabbix
    :param acknowledge_messages: Список из подтверждений проблемы, если такая имеется
    :return: Объект folium.Popup
    """
    font_style = '"color:black;font-size:18px"'
    title = 'Посмотреть в Zabbix'
    html_str = f'''
    <p>
    <a href="{zabbixURL}/zabbix.php?action=host.view&filter_name={host_name}&filter_ip=&filter_dns=&filter_port=&filter_status=0&filter_evaltype=0&filter_tags%5B0%5D%5Btag%5D=&filter_tags%5B0%5D%5Boperator%5D=0&filter_tags%5B0%5D%5Bvalue%5D=&filter_maintenance_status=1&filter_show_suppressed=0&filter_set=1" 
    title="{title}" style={font_style} target="_blank">{host_name}</a>
    </p>
    '''
    if acknowledge_messages:
        for ack in acknowledge_messages:
            html_str += f'<p>{datetime.fromtimestamp(int(ack[1]))} -> {ack[0]}</p>\n'

    height = 300 if acknowledge_messages else 50
    width = 500 if acknowledge_messages else len(host_name) * 12

    iframe = branca.element.IFrame(html=html_str, width=width, height=height)

    return folium.Popup(iframe, max_width=500)


def marker_format(hostid: str):
    """
    Возвращает цвет и размер значка в зависимости от типа оборудования и его доступности
    :param name: Имя файла, где находится данный узел
    :param hostid: ID Узла в БД Zabbix
    :return: Словарь {"color": "red", "radius": 5}
    """
    default_property = {
        "color": "#00cc00",
        "color_border": "#00cc00",
        "radius": 3,
        "fill_opacity": 1
    }
    if hostid in devices_down_ids:
        default_property["color"] = "red"
        default_property["color_border"] = "red"
        default_property["fill_opacity"] = 1
        default_property["radius"] = 4
    return default_property


# Создаем карту для Севастополя
zabbix_map = folium.Map(location=[44.607468, 33.515746], zoom_start=11)

for file_name in os.listdir(f'{sys.path[0]}/locations'):  # Перебираем файлы
    if not file_name.endswith('.csv'):  # считываем только .csv файлы
        continue
    group_name = file_name[:-4]  # Обрезаем последние 4 символа: ".csv"
    print('File:', file_name)
    data = pd.read_csv(f'{sys.path[0]}/locations/{file_name}')
    names = data["Name"]
    lats = data["location_lat"]
    lons = data["location_lon"]
    hostids = data['hostid']

    # Создаем словари проблем для недоступного оборудования
    with ZabbixAPI(server=zabbixURL) as z:
        z.login(user=zabbixUser, password=zabbixPassword)
        group = z.hostgroup.get(filter={'name': group_name})  # Находим группу в Zabbix
    if not group:  # Если такая группа НЕ существует, то пропускаем данный файл
        continue

    # Создаем группу на карте
    map_group = folium.FeatureGroup(name=group_name).add_to(zabbix_map)

    # Проблемные узлы данной группы
    hosts_problem = get_hosts_with_problem(group[0]['groupid'])

    # Создаем список ID недоступного оборудования для группы
    devices_down_ids = [p for p in hosts_problem]
    print("Devices down:", devices_down_ids)

    point_devices_down = []
    for name, lat, lon, hostid in zip(names, lats, lons, hostids):
        marker = marker_format(str(hostid))  # Получаем цвет и размер маркера
        point = folium.CircleMarker(
            location=(lat, lon),                    # Координаты
            popup=popup(name, hosts_problem.get(str(hostid))),    # Всплывающее меню
            radius=marker["radius"],                # Размер
            fill_color=marker["color"],             # Цвет
            tooltip=name,                           # Имя
            color=marker["color_border"],           # Цвет периметра значка
            weight=1,                               # Толщина
            fill_opacity=marker["fill_opacity"]     # Прозрачность
        )
        if marker["color"] == "red":  # Если оборудование недоступно, то
            point_devices_down.append(point)  # Добавляем его в список недоступного оборудования
            continue
        point.add_to(map_group)

    #   Если в данном файле имеется недоступное оборудование, то необходимо добавить его в самом конце,
    # чтобы оно отображалось поверх других
    for dev in point_devices_down:
        dev.add_to(map_group)

# Добавляем кнопку "На весь экран"
Fullscreen(
    position="topright",
    title="Развернуть",
    title_cancel="Свернуть",
    force_separate_button=True,
).add_to(zabbix_map)

folium.LayerControl().add_to(zabbix_map)

MousePosition().add_to(zabbix_map)  # Добавляем модуль, для отображения гео координат при наведении мышкой

zabbix_map.add_child(MeasureControl(position='topleft'))  # Добавляем инструмент "Линейку"

zabbix_map.save(f"{sys.path[0]}/templates/zabbix-map.html")  # Сохраняем карту

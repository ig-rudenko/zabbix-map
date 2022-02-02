from pyzabbix import ZabbixAPI
import argparse
from configparser import ConfigParser
import sys

json_geo = {
    "type": "FeatureCollection",
    "features": []
}

cfg = ConfigParser()
cfg.read(f'{sys.path[0]}/conf')
zabbixURL = cfg.get('Zabbix', 'url')
zabbixUser = cfg.get('Zabbix', 'user')
zabbixPassword = cfg.get('Zabbix', 'password')


def zabbix_get(group_id: int, type_: str):
    with ZabbixAPI(server=zabbixURL) as z:
        z.login(user=zabbixUser, password=zabbixPassword)
        res = 'Name,location_lat,location_lon,hostid\n'  # Создаем названия столбцов
        hosts = z.host.get(groupids=group_id, selectInterfaces=['ip'], selectInventory=['location_lat', 'location_lon'])
    # print(hosts[0])
    for num, host in enumerate(hosts, start=1):
        if host['inventory']['location_lat'] and host['inventory']['location_lon'] and host["status"] == '0':
            if type_ == 'csv':
                res += f"{host['name'].replace(',', ';')}," \
                       f"{host['inventory']['location_lat']}," \
                       f"{host['inventory']['location_lon']}," \
                       f"{host['hostid']}\n"

            elif type_ == 'json':
                json_geo["features"].append(
                    {
                        "type": "Feature",
                        "id": f"0{num}" if num < 10 else f"{num}",
                        "properties": {
                            "name": f"{host['name']}"
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [
                                float(host['inventory']['location_lat'].replace(',', '')),
                                float(host['inventory']['location_lon'].replace(',', ''))
                            ]
                        }
                    }
                )
        elif (not host['inventory']['location_lon'] or not host['inventory']['location_lat']) and host["status"] == '0':
            print(host["name"])
    if type_ == 'csv':
        res = res.replace(',,', ',')
        return res
    elif type_ == 'json':
        return json_geo


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Zabbix Interactive Map")
    parser.add_argument(nargs='*', dest='groups', help='Zabbix group names', default='', metavar='')
    args = parser.parse_args()

    print(args.groups)

    for g in args.groups:   # Проходимся по введенным именам групп
        with ZabbixAPI(server=zabbixURL) as z:
            z.login(user=zabbixUser, password=zabbixPassword)
            group = z.hostgroup.get(filter={'name': g})     # Находим группу в Zabbix
        if group:  # Если такая группа существует
            with open(f'{sys.path[0]}/locations/{g}.csv', 'w') as file:   # Открываем файл для записи
                file.write(     # Записываем в файл
                    zabbix_get(     # Получаем данные из Zabbix
                        int(group[0]['groupid']),   # ID группы
                        'csv'   # Формат файла
                    )
                )

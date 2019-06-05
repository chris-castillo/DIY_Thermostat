import time
import socket
from datetime import datetime, timezone

def get_ip():
    # https://stackoverflow.com/a/28950776
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def read_temp_raw(device_file):
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
 
def read_temp(device_file):
    lines = read_temp_raw(device_file)
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f

def write_temp(device_file,localIP,client):
    temp_c, temp_f = read_temp(device_file)

    towritetime = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    test_json = [{"tags":{"localIP":localIP},
                    "fields":{"temp":temp_c},
                    "time":towritetime,
                    "measurement":"temperature"}]

    client.write_points(test_json)
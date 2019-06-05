import json
from influxdb import InfluxDBClient

path = '/home/albert/config_web/'

with open(path+'thermoCurrentStates', 'r') as infile:
	variablesToPass = json.load(infile)

client = InfluxDBClient(host='localhost', port=8086)
client.switch_database('temperature')
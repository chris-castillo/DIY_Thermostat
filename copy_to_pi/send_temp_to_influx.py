from influxdb import InfluxDBClient
import pi_functions as pi_fn

localIP = pi_fn.get_ip()

influx_host = 'server.home'

client = InfluxDBClient(host=influx_host, port=8086)
client.switch_database('temperature')
 
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
 
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

while True:
    pi_fn.write_temp()
    time.sleep(30)
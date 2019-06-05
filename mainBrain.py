#!/usr/bin/env python
from flask import Flask, jsonify, render_template, request, send_file, make_response
import json
from influxdb import InfluxDBClient
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime
import matplotlib.dates as mdates
from scipy.signal import savgol_filter

def return_influx(timerange=1,fahrenheit=False):
	# timerange is units of hours

	# construct query string
	query = 'SELECT * FROM temperature WHERE time > now() - ' + str(timerange) + 'h'

	# query influxdb database
	results = client.query(query)

	# instantiate dictionary and assign values based on query
	temps_in_range = {}
	for curr_IP,room in zip(IPs,rooms):
		# instantiate
		temps_in_range[room] = {}
		temps_in_range[room]['time'] = []
		temps_in_range[room]['temp'] = []

		#retrieve datapoints only related to each specific IP
		temp_points = results.get_points(tags={'localIP':curr_IP})
		
		#assign values from query to dictionary
		for point in temp_points:
			temps_in_range[room]['time'].append(point['time'])
			temps_in_range[room]['temp'].append(point['temp'])

		#convert time string to datetime
		temp_date_string_list = temps_in_range[room]['time']
		temp_date_datetime_list = [datetime.strptime(temp_time.split(".")[0], influx_time_format_string_code) for temp_time in temp_date_string_list]

		temps_in_range[room]['time'] = temp_date_datetime_list
	
	if fahrenheit:
		for room in rooms:
			temps_in_range[room]['temp'] = [convertC2F(temp_temp) for temp_temp in temps_in_range[room]['temp']]


	return(temps_in_range)

def get_influx():
	results = client.query('SELECT * FROM temperature ORDER BY DESC LIMIT 2000')

	current_temps = {}

	for curr_IP,name in zip(IPs,names):
		temp_points = results.get_points(tags={'localIP':curr_IP})
		list2collect = []
		for point in temp_points:
			# print(curr_IP,point)
			list2collect.append(point)
		# print(curr_IP,list2collect)
		curr_temp_C = list2collect[-1]['temp']
		current_temps[name] = round(convertC2F(curr_temp_C),numDecimals2Round)

	current_temps['avg'] = round(np.average([current_temps[name] for name in names[:-1]]),numDecimals2Round)

	return(current_temps)

def convertC2F(inputC):
	return inputC*1.8+32

numDecimals2Round = 1


IPs = ['192.168.1.213','192.168.1.214','192.168.1.215','192.168.1.216']
rooms = ['kitchen','office','TV','bedroom']
options = rooms + ['avg']

influx_time_format_string_code = '%Y-%m-%dT%H:%M:%S'

client = InfluxDBClient(host='localhost', port=8086)
client.switch_database('temperature')

app = Flask(__name__)

path = '/home/albert/config_web/'

variablesToPass = {	"cool": 			False, 
					"heat":				True, 
					"air":				True,
					"lowtemp":			60, 
					"hightemp":			80,
					"temp2use":			'avg'
						}

current_temps = return_influx(fahrenheit=True)

for room in rooms:
	variablesToPass[room] = current_temps[room]['temp'][-1]

with open(path+'thermoCurrentStates', 'w') as outfile:
	json.dump(variablesToPass, outfile)

@app.route('/interactive')
def interactive():

	current_temps = return_influx()

	for room in rooms:
		variablesToPass[room] = current_temps[room]['temp'][-1]

	print([variablesToPass[room] for room in rooms])
	variablesToPass['avg'] = np.average([variablesToPass[room] for room in rooms])


	return render_template("interactive.html", variables = variablesToPass, names=options)

@app.route('/background_process',methods=['POST'])
def background_process():
	req = request.form.get('data').split()
	print(req)

	if len(req) == 1:
		variablesToPass['temp2use'] = req[0]
	else:	
		if req[2] == "+":
			variablesToPass[req[1] + "temp"] += 1

		if req[2] == "-":
			variablesToPass[req[1] + "temp"] -= 1

	with open(path+'thermoCurrentStates', 'w') as outfile:
		json.dump(variablesToPass, outfile)

	return jsonify(variablesToPass)


@app.route('/thermostat_plot_png/<hours>')
def thermostat_plot_png(hours):
	#retrieve latest 


	current_temps = return_influx(hours)

	fig, ax = plt.subplots()

	for room in rooms:
		dates = mdates.date2num(current_temps[room]['time'])
		#window filter scaled based on data size
		num_data_points = len(current_temps[room]['temp'])
		window_filter = int(num_data_points/5)
		#ensure window filter is odd
		if (window_filter % 2 == 0): window_filter += 1
		yhat = savgol_filter(current_temps[room]['temp'], window_filter, 3) 
		if variablesToPass['temp2use'] == room:
			ax.plot_date(dates,yhat,'-',linewidth=3)
		else:
			ax.plot_date(dates,yhat,'-')
		# ax.plot_date(dates,current_temps[room]['temp'],'o',ms=0.5)

	# also show average
	all_temps = np.concatenate([current_temps[room]['temp'] for room in rooms])
	all_dates = mdates.date2num(np.concatenate([current_temps[room]['time'] for room in rooms]))
	# print(all_dates)

	# ax.plot_date(all_dates,all_temps,'o',ms=0.5)

	_sorted = np.argsort(all_dates)
	all_dates = all_dates[_sorted]
	all_temps = all_temps[_sorted]

	num_data_points = len(all_temps)
	window_filter = int(num_data_points/2)
	if (window_filter % 2 == 0): window_filter += 1
	yhat = savgol_filter(all_temps, window_filter, 3) 
	# ax.plot_date(all_dates,all_temps,'o',ms=0.7)

	if variablesToPass['temp2use'] == 'avg':
		ax.plot_date(all_dates,yhat,'--',linewidth=3)
	else:
		ax.plot_date(all_dates,yhat,'--')
	ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))

	plt.tight_layout()

	canvas = FigureCanvas(fig)
	img = BytesIO()
	fig.savefig(img)
	img.seek(0)

	# all figs are kept in memory, close so that we dont keep all of them (every 5 seconds!)
	plt.close(fig)

	return send_file(img, mimetype='image/png')


if __name__ == "__main__":
    app.run(host='0.0.0.0')

#!/usr/bin/env python
from flask import Flask, jsonify, render_template, request, send_file, make_response
import json
from influxdb import InfluxDBClient
import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from io import BytesIO
import matplotlib.dates as mdates
from scipy.signal import savgol_filter
import functions as fn
from datetime import datetime

numDecimals2Round = 1

IPs = ['192.168.1.213','192.168.1.214','192.168.1.215','192.168.1.216']
rooms = ['kitchen','office','TV','bedroom']
options = rooms + ['avg']

influx_time_format_string_code = '%Y-%m-%dT%H:%M:%S'

client = InfluxDBClient(host='localhost', port=8086)
client.switch_database('temperature')

app = Flask(__name__)

path = '/home/albert/config_web/'

flask_info = fn.flask_info(client, IPs, rooms,influx_time_format_string_code)

flask_info.retrieve_latest_influxdb_setTemps()

@app.route('/interactive')
def interactive():

	flask_info.retrieve_influxdb_temps(fahrenheit=True)

	flask_info.retrieve_latest_influxdb_setTemps()

	return render_template("interactive.html", flask_info = flask_info)

@app.route('/background_process',methods=['POST'])
def background_process():
	req = request.form.get('data').split()
	print(req)

	if len(req) == 1:
		flask_info.thermoSetTemps['temp2use'] = req[0]
	else:	
		if req[2] == "+":
			flask_info.thermoSetTemps[req[1] + "temp"] += 1

		if req[2] == "-":
			flask_info.thermoSetTemps[req[1] + "temp"] -= 1

	flask_info.write_logic_to_influxdb()

	flask_info.retrieve_latest_influxdb_setTemps()

	return jsonify(flask_info.thermoSetTemps)


@app.route('/thermostat_plot_png/<hours>')
def thermostat_plot_png(hours):
	#retrieve latest 

	flask_info.retrieve_influxdb_temps(timerange=hours,fahrenheit=True)

	flask_info.retrieve_all_influxdb_setTemps(timerange=hours)

	fig, ax = plt.subplots()

	for room in rooms:
		dates = mdates.date2num(flask_info.all_temps[room]['time'])
		#window filter scaled based on data size
		num_data_points = len(flask_info.all_temps[room]['temp'])
		window_filter = int(num_data_points/5)
		#ensure window filter is odd
		if (window_filter % 2 == 0): window_filter += 1
		yhat = savgol_filter(flask_info.all_temps[room]['temp'], window_filter, 3) 
		if flask_info.thermoSetTemps['temp2use'] == room:
			ax.plot_date(dates,yhat,'-',linewidth=3)
		else:
			ax.plot_date(dates,yhat,'-')
		# ax.plot_date(dates,flask_info.all_temps[room]['temp'],'o',ms=0.5)

	# also show average
	all_temps = np.concatenate([flask_info.all_temps[room]['temp'] for room in rooms])
	all_dates = mdates.date2num(np.concatenate([flask_info.all_temps[room]['time'] for room in rooms]))
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

	if flask_info.thermoSetTemps['temp2use'] == 'avg':
		ax.plot_date(all_dates,yhat,'--',linewidth=3)
	else:
		ax.plot_date(all_dates,yhat,'--')


	# --------- PLOT SET TEMPS ----------------
	dates = mdates.date2num(flask_info.all_setTemps['time'])

	#append current time so we can see up to date
	dates = np.append(dates,mdates.date2num(datetime.utcnow()))

	_hightemp = flask_info.all_setTemps['hightemp']
	_lowtemp = flask_info.all_setTemps['lowtemp']

	_hightemp = np.append(_hightemp,_hightemp[-1])
	_lowtemp  = np.append(_lowtemp,_lowtemp[-1])

	ax.plot_date(dates,_hightemp,'-',c='blue')
	ax.plot_date(dates,_lowtemp,'-',c='red')

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

from datetime import datetime

class flask_info():
	def __init__(self, client, IPs, rooms,influx_time_format_string_code):
		self.client = client
		self.IPs = IPs
		self.rooms = rooms
		self.options = rooms + ['avg']
		self.influx_time_format_string_code = influx_time_format_string_code

	def retrieve_influxdb_temps(self,timerange=1,fahrenheit=False):
		# timerange is units of hours

		# construct query string
		query = 'SELECT * FROM temperature WHERE time > now() - ' + str(timerange) + 'h'

		# query influxdb database
		results = self.client.query(query)

		# instantiate dictionary and assign values based on query
		temps_in_range = {}
		for curr_IP,room in zip(self.IPs,self.rooms):
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
			temp_date_datetime_list = [datetime.strptime(temp_time.split(".")[0], self.influx_time_format_string_code) for temp_time in temp_date_string_list]

			temps_in_range[room]['time'] = temp_date_datetime_list
		
		if fahrenheit:
			for room in self.rooms:
				temps_in_range[room]['temp'] = [convertC2F(temp_temp) for temp_temp in temps_in_range[room]['temp']]


		_most_recent_temps = {}
		for room in self.rooms:
			_most_recent_temps[room] = temps_in_range[room]['temp'][-1]

		self.all_temps = temps_in_range
		self.most_recent_temps = _most_recent_temps

	def retrieve_latest_influxdb_setTemps(self):
		# construct query string
		query = 'SELECT * FROM setTemps GROUP BY * ORDER BY DESC LIMIT 1'

		# query influxdb database
		results = self.client.query(query)

		last_point = next(results.get_points())

		print(last_point)

		self.thermoSetTemps = last_point

	def retrieve_all_influxdb_setTemps(self,timerange=1,fahrenheit=False):
		# timerange is units of hours

		# construct query string
		query = 'SELECT * FROM setTemps WHERE time > now() - ' + str(timerange) + 'h'

		# query influxdb database
		results = self.client.query(query)

		# instantiate dictionary and assign values based on query
		set_in_range = {}

		keys_to_iterate_over = ['time','lowtemp','hightemp']

		for key in keys_to_iterate_over:
			set_in_range[key] = []

		temp_points = results.get_points()

		for point in temp_points:
			for key in keys_to_iterate_over:
				set_in_range[key].append(point[key])

		temp_date_string_list 	= set_in_range['time']
		temp_date_datetime_list = [datetime.strptime(temp_time.split(".")[0], self.influx_time_format_string_code + "Z") for temp_time in temp_date_string_list]

		set_in_range['time'] = temp_date_datetime_list

		self.all_setTemps = set_in_range

	def write_logic_to_influxdb(self):

		json_body = [{	"time":datetime.utcnow().strftime(self.influx_time_format_string_code),
						"measurement":"setTemps",
						"fields":self.thermoSetTemps}]

		self.client.write_points(json_body)


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
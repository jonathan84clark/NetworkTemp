###################################################################
# USER SERVER
# DESC: Serves up images to display to the user.
# You will need to allow traffic through the TCP port sudo ufw allow 3589
# Author: Jonathan L Clark
# Company: Special Services Group LLC
# sudo pip3 install flask-wtf
# pip3 install email_validator
# the session manager components were based on the above source. Since we are using SQLLite3.
# Date: 4/20/2021
###################################################################
from flask import session, redirect, url_for 
from flask import Flask
from flask import render_template
from flask import request
from flask import jsonify
from flask import abort
from os.path import expanduser
import time
import threading
import os
import pathlib
import datetime
import math
import sqlite3
from sqlite3 import Error
from datetime import datetime

# creates a Flask application, named app
app = Flask(__name__)

# Queit down the logging
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

DB_FILE = "/home/jonathan/Documents/Git/temperature_data.db"


# a route where we will display a welcome message via an HTML template
@app.route("/")
def home():
    return render_template('index.html')

@app.route('/data', methods=['GET', 'POST'])
def data():
    dataSet = {"min_values" : [], "max_values" : [], "average_values" : [], "hourly_values" : []}
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        if request.method == 'POST':
            pass
        else:
            cursor.execute('SELECT * FROM environment') 
            records = cursor.fetchall()
            displayMax = True
            displayMin = False
            displayAverage = True
            displayAllDaily = False
            record_start_date = "5/10/2021"
            record_end_date = "6/11/2021"
            
            start_date_obj = None #datetime.strptime(record_start_date, "%m/%d/%Y")
            end_date_obj = None #datetime.strptime(record_end_date, "%m/%d/%Y")
            current_day = 0
            daily_record_cnt = 0.0
            first_record = True
            max_values = []
            min_values = []
            average_values = []
            date_stamp_str = ""
            for x in range(0, 10):
                max_values.append(0.0)
                min_values.append(0.0)
                average_values.append(0.0)
            
            for record in records:
                epoch_time = float(record[0])
                timeStamp = datetime.fromtimestamp(epoch_time)
                record_filter_valid = True
                if start_date_obj != None and end_date_obj != None:
                    if not (timeStamp >= start_date_obj and timeStamp <= end_date_obj):
                        record_filter_valid = False
                        
                if record_filter_valid:
                    if current_day != timeStamp.day:
                        # Output rows based on min/max values
                        if not first_record:
                            if displayMax:
                                max_values[6] = max_values[6] * (9.0/5.0) + 32.0
                                max_values[1] = max_values[1] * (9.0/5.0) + 32.0
                                max_values[0] = max_values[0] * (9.0/5.0) + 32.0
                                max_values[9] = max_values[9] * (9.0/5.0) + 32.0
                                max_values[3] *= 10.0                              
                                dataSet["max_values"].append({"date" : date_stamp_str, "system_temp" : max_values[0], "garage_temp" : max_values[1], "garage_humid" : max_values[2], "garage_pressure" : max_values[3], "outdoor_temp" : max_values[4], "outdoor_humid" : max_values[5], "indoor_temp" : max_values[6], "indoor_humid" : max_values[7], "indoor_pressure" : max_values[8], "indoor_cpu" : max_values[9]})
                            if displayMin:
                                min_values[6] = min_values[6] * (9.0/5.0) + 32.0
                                min_values[1] = min_values[1] * (9.0/5.0) + 32.0
                                min_values[0] = min_values[0] * (9.0/5.0) + 32.0
                                min_values[9] = min_values[9] * (9.0/5.0) + 32.0  
                                min_values[3] *= 10.0 
                                dataSet["min_values"].append({"date" : date_stamp_str, "system_temp" : min_values[0], "garage_temp" : min_values[1], "garage_humid" : min_values[2], "garage_pressure" : min_values[3], "outdoor_temp" : min_values[4], "outdoor_humid" : min_values[5], "indoor_temp" : min_values[6], "indoor_humid" : min_values[7], "indoor_pressure" : min_values[8], "indoor_cpu" : min_values[9]})   
                            if displayAverage:
                                average_values[6] = (average_values[6] / daily_record_cnt) * (9.0/5.0) + 32.0
                                average_values[1] = (average_values[1] / daily_record_cnt) * (9.0/5.0) + 32.0
                                average_values[0] = (average_values[0] / daily_record_cnt) * (9.0/5.0) + 32.0
                                average_values[9] = (average_values[9] / daily_record_cnt) * (9.0/5.0) + 32.0
                                average_values[3] = (average_values[3] / daily_record_cnt) * 10.0 
                                dataSet["average_values"].append({"date" : date_stamp_str, "system_temp" : average_values[0], "garage_temp" : average_values[1], "garage_humid" : average_values[2] / daily_record_cnt, "garage_pressure" : average_values[3], "outdoor_temp" : average_values[4] / daily_record_cnt, "outdoor_humid" : average_values[5] / daily_record_cnt, "indoor_temp" : average_values[6], "indoor_humid" : average_values[7] / daily_record_cnt, "indoor_pressure" : average_values[8] / daily_record_cnt, "indoor_cpu" : average_values[9] / daily_record_cnt})
                        # Create a new starting condition, assert that the max and min values are the first values in the record
                        for x in range(0, 10):
                            max_values[x] = record[x+1] # Records always start at idx1 because the date is idx0
                            min_values[x] = record[x+1]
                            average_values[x] = 0.0
                        daily_record_cnt = 0.0
                        date_stamp_str = timeStamp.strftime("%m/%d/%Y")
                        current_day = timeStamp.day
                        first_record = False
                
                    # Now, calculate daily statistics
                    for x in range(0, 10):
                        if max_values[x] < record[x+1]:
                            max_values[x] = record[x+1]
                        if min_values[x] > record[x+1]:
                            min_values[x] = record[x+1]
                        average_values[x] += record[x+1]
                    
                    daily_record_cnt += 1
                
                    if displayAllDaily:
                        date_string = timeStamp.strftime("%m/%d/%Y")
                        time_string = timeStamp.strftime("%H:%M:%S")
                        dataSet["hourly_values"].append({"date" : date_string, "time" : time_string, "system_temp" : record[1], "garage_temp" : record[2], "garage_humid" : record[3], "garage_pressure" : record[4], "outdoor_temp" : record[5], "outdoor_humid" : record[6], "indoor_temp" : record[7], "indoor_humid" : record[8], "indoor_pressure" : record[9], "indoor_cpu" : record[10]})
            
    except Exception as ex:
        print("Exception: " + str(ex))
        return jsonify(dataSet)
    
    output = jsonify(dataSet)
    
    return output    
        
# run the application (using the default WebServer: werkzeug
if __name__ == "__main__":
    app.useReloader = False
    
    thread = threading.Thread(target=app.run, kwargs={'port': 3000,'host':'0.0.0.0'})
    thread.daemon = True
    thread.start()
        
    while True:
        time.sleep(1)

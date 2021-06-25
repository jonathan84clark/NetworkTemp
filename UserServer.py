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

DB_FILE = "/home/pi/temperature_data.db"


# a route where we will display a welcome message via an HTML template
@app.route("/")
def home():
    return render_template('index.html')

@app.route('/data', methods=['GET', 'POST'])
def data():
    dataSet = {}
    
    try:
        conn = sqlite3.connect(DB_FILE)
        if request.method == 'POST':
            pass
        else:
            #if 'edit_user' in request.args:
            #    target_user = request.args.get('edit_user')        
            pass
            
    except Exception as ex:
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

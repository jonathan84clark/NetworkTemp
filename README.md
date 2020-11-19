# Network Temp 
The network temp project is designed to provide both indoor and outdoor temperatures. The data from these sensors is taken and analyzed for patterns. The Network Sensors use Flask and run on the Raspberry PI. They interface with a DHT11 temp/humid sensor and MPL3115A pressure sensor. The goal of the project is to provide live temperature information and to collect temperature data for later analysis for the purpose of predicting weather patterns.  

# Wiring    
The MPL3115A connects to the I2C pins on the Raspberry PI (SCL, SDA). The DHT11 pin is setup in the __init__ function.  

# Compilation and Setup  
The setup steps can be seen on the TemperatureServer.py script (ignoring the OpenCV setup information) here are the setup commands:
```bash
# Pull in the code
cd~
git clone https://github.com/jonathan84clark/NetworkTemp.git

# Setup the PI to interface with the dht11
sudo apt-get update
sudo apt-get install python-pip
sudo python -m pip install --upgrade pip setuptools wheel
git clone https://github.com/adafruit/Adafruit_Python_DHT.git
cd Adafruit_Python_DHT
sudo python setup.py install

# Setup the I2C interface for the MPL3115A
pip install smbus

# Setup Flask
pip install Flask

# Setup Numpy
pip install numpy
python -m pip install --user numpy scipy matplotlib ipython jupyter pandas sympy nose
```
Now that the system is setup, run the TemperatureServer.py script. More dependancies may need to be setup.

# Setup to start on boot
To run the temperature server on boot add the following line to /etc/init.d/rc.local
```bash
sudo -H -u pi python /home/pi/NetworkTemp/TemperatureServer.py &
```

# Status 
As of 8/5/2020 the project is still in development. The system is being run continually to get both outdoor temperature and humidity.  

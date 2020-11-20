from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
import json
import os.path

shadow = {
  "state": { "desired": { "color": { "r": 10 }, "engine": "ON", "temp" : 72.0 } }
}

USER_DIR = os.path.expanduser("~")

PATH_TO_CERT = USER_DIR + "/.security/c039a05d5e-certificate.pem.crt"
PATH_TO_KEY = USER_DIR + "/.security/c039a05d5e-private.pem.key"
PATH_TO_ROOT = USER_DIR + "/.security/AmazonRootCA1.pem"

myJSONPayload = json.dumps(shadow)
def customCallback(data, param2, param3):
    print(data)
    
try:
    print("Call")
    # For certificate based connection
    myShadowClient = AWSIoTMQTTShadowClient("myClientID")
    # For Websocket connection
    # myMQTTClient = AWSIoTMQTTClient("myClientID", useWebsocket=True)
    # Configurations
    # For TLS mutual authentication
    myShadowClient.configureEndpoint("a2yizg9mkkd9ph-ats.iot.us-west-2.amazonaws.com", 8883)
    # For Websocket
    # myShadowClient.configureEndpoint("YOUR.ENDPOINT", 443)
    # For TLS mutual authentication with TLS ALPN extension
    # myShadowClient.configureEndpoint("YOUR.ENDPOINT", 443)
    myShadowClient.configureCredentials(PATH_TO_ROOT, PATH_TO_KEY, PATH_TO_ROOT)
    # For Websocket, we only need to configure the root CA
    # myShadowClient.configureCredentials("YOUR/ROOT/CA/PATH")
    myShadowClient.configureConnectDisconnectTimeout(10)  # 10 sec
    myShadowClient.configureMQTTOperationTimeout(5)  # 5 sec
    
    myShadowClient.connect()
    # Create a device shadow instance using persistent subscription
    myDeviceShadow = myShadowClient.createShadowHandlerWithName("SkywireCameraThing", True)
    # Shadow operations
    myDeviceShadow.shadowGet(customCallback, 5)
    myDeviceShadow.shadowUpdate(myJSONPayload, customCallback, 5)
    #myDeviceShadow.shadowDelete(customCallback, 5)
    myDeviceShadow.shadowRegisterDeltaCallback(customCallback)
    myDeviceShadow.shadowUnregisterDeltaCallback()
    print("Call5")
except:
    print("Exception")
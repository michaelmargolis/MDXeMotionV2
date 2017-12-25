import paho.mqtt.client as mqtt

PROTOCOL = mqtt.MQTTv311

class MQTTClient():

    def __init__(self, id, msg_callback):
        self.client = mqtt.Client(client_id=id, clean_session=True, userdata=None, protocol=PROTOCOL)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.msg_callback = msg_callback
    
    def subscribe(self, topic):
        self.client.subscribe(topic)
    
    def publish(self, topic, payload):
         qos = 1 # at least on message will be received by broker
         self.client.publish(topic, payload, qos)
        
    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        print("Connected with result code "+str(rc))

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        self.client.subscribe("$SYS/#")
        self.client.subscribe("flightsim/telemetry")      
        print "on_connect todo - pass topic"        
    
    def on_disconnect(self, client, userdata, flags, rc=0):
        print("Disconnected with result code "+str(rc))
        self.client.loop_stop()

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
        #  print(msg.topic+" "+str(msg.payload))
        if self.msg_callback:
            self.msg_callback(str(msg.payload))       
             

    def connect(self, broker, port=1883):
        print "connecting to mqtt broker " + broker + " on port  " +str(port)
        self.client.connect(broker, port, 180) 
        self.client.loop_start()        
         
    def command(self, topic, msg):
        self.client.publish(topic, msg)
         
    def disconnect(self):
        print("Disconnected from mqtt")
        self.client.disconnect() 
        

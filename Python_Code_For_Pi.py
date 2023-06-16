import hashlib
import time
import RPi.GPIO as GPIO
from pyfingerprint.pyfingerprint import PyFingerprint
from pyfingerprint.pyfingerprint import FINGERPRINT_CHARBUFFER1
import paho.mqtt.client as mqtt

# mosquitto_sub -d -t my_topic
# mosquitto_pub -d -t my_topic -m "Not Unknown User"
# Initialize the fingerprint sensor
try:
    f = PyFingerprint('/dev/ttyS0', 57600, 0xFFFFFFFF, 0x00000000)

    if (f.verifyPassword() == False):
        raise ValueError('The given fingerprint sensor password is wrong!')

except Exception as e:
    print('The fingerprint sensor could not be initialized!')
    print('Exception message: ' + str(e))
    exit(1)

# Initialize the LED and servo
Pin = 21
servoPIN = 13
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(Pin, GPIO.OUT)
GPIO.setup(servoPIN, GPIO.OUT)
p = GPIO.PWM(servoPIN, 50)
p.start(2.5)

# MQTT connection callback
def on_connect(client, userdata, flags, rc):
    print('Connected with result code ' + str(rc))
    client.subscribe('my_topic')
    return 2

# MQTT message callback
def on_message(client, userdata, msg):
    while msg.topic == 'my_topic' and msg.payload == b'Unknown User':
        print('Waiting for valid user...')
        return 2
        
    if msg.topic == 'my_topic':    
        print('Received message: ' + str(msg.payload))
        GPIO.output(Pin, GPIO.HIGH)
        time.sleep(1)
        GPIO.output(Pin, GPIO.LOW)
        time.sleep(1)
    while True:  
        try:
            # Wait for finger to be read
            print('Waiting for finger...')
            
            while (f.readImage() == False):
                pass
         
            # Convert read image to characteristics and store it in charbuffer 1
            f.convertImage(FINGERPRINT_CHARBUFFER1)

            # Search for template
            result = f.searchTemplate()
            positionNumber = result[0]
            accuracyScore = result[1]
             
            # Check if match was found
            if (positionNumber == -1):
                print('No match found!')
                return 1

            # Toggle servo
            print('Found template at position #' + str(positionNumber))
            print('The accuracy score is: ' + str(accuracyScore))
            
            if (positionNumber == 1):
                print('Xin Chao Phung Cong Nguyen voi id la : ' + str(positionNumber))
            elif (positionNumber == 2):
                print('Xin Chao user2 voi id la : ' + str(positionNumber))
            GPIO.output(Pin, GPIO.HIGH)    
            for duty_cycle in range(75, 25, -1):
             p.ChangeDutyCycle(duty_cycle/10)
             time.sleep(0.02)  # Wait for 20ms between each step
            for duty_cycle in range(25, 76):
             p.ChangeDutyCycle(duty_cycle/10)
             time.sleep(0.02)  # Wait for 20ms between each step
            GPIO.output(Pin, GPIO.LOW)

             # Load and hash the template
            f.loadTemplate(positionNumber, FINGERPRINT_CHARBUFFER1)
            characterics = str(f.downloadCharacteristics(FINGERPRINT_CHARBUFFER1)).encode('utf-8')
            print('SHA-2 hash of template: ' + hashlib.sha256(characterics).hexdigest())
            return 1

        except Exception as e:
            print('Operation failed!')        
            print('Exception message: ' + str(e))
            break
                  
        except KeyboardInterrupt:
            GPIO.cleanup()
            p.stop()
            break    

# Create an MQTT client and connect to the broker
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect('localhost', 1883, 60)

# Start the MQTT client loop
client.loop_forever()       

import cv2
import face_recognition
import dlib
import paho.mqtt.publish as publish
from flask import Flask, render_template, Response
from datetime import datetime
import time
import threading

# mosquitto_sub -d -t my_topic
# Set the MQTT broker address and port
# MQTT_SERVER = "192.168.9.218"
MQTT_SERVER = "localhost"
MQTT_PORT = 1883

# Set the MQTT topic to publish to
MQTT_TOPIC = "my_topic"
# Load the known face image and encoding
known_image = face_recognition.load_image_file("/home/lqptoptvt/Desktop/images/boy.jpg")
known_encoding = face_recognition.face_encodings(known_image)[0]

# Set your name
my_name = "Phung Cong Nguyen"

# Create the Flask application
app = Flask(__name__)

# Create a face detector using dlib
detector = dlib.get_frontal_face_detector()

# Define a function to publish the name to MQTT topic every 10 seconds
# Create a global variable to store the thread object
name_thread = None
def publish_name():
    id = 0
    while True:
        try:
            publish.single(MQTT_TOPIC, payload=my_name, hostname=MQTT_SERVER, port=MQTT_PORT, qos=1)
        except ConnectionError as ce:
            print(f"Connection error while publishing message: {ce}")
            # Wait for 5 seconds before retrying
            time.sleep(5)
            continue
        except Exception as e:
            print(f"Error publishing message: {e}")
            # Wait for 10 seconds before retrying
            time.sleep(10)
            continue
        else:
            id += 1
            print(f"User OK !: {my_name}")
               # Save name and time to file

            with open("log.txt", "a") as f:
    
                   f.write(f"{id} {my_name} was recognized at {datetime.now()}\n")
            # Wait for 10 seconds before publishing the next message
            time.sleep(10)
# Define the route for the video feed
@app.route('/video_feed')
def video_feed():
    # Open the default camera
    cap = cv2.VideoCapture(0)

    def generate_frames():
        while True:
            # Capture frame-by-frame
            ret, frame = cap.read()

            # Convert BGR image format to RGB format
            rgb_frame = frame[:, :, ::-1]

            # Detect faces in the frame using dlib
            dlib_faces = detector(rgb_frame, 1)

            # Convert dlib_faces to a list of tuples of (top, right, bottom, left) coordinates
            fc_locations = [(f.top(), f.right(), f.bottom(), f.left()) for f in dlib_faces]

            if len(fc_locations) > 0:
                # Find face encodings
                fc_encodings = face_recognition.face_encodings(rgb_frame, fc_locations)

                # Compare with known face encoding
                for fc_encoding in fc_encodings:
                    matches = face_recognition.compare_faces([known_encoding], fc_encoding)

                    if True in matches:
                        # Draw green box around detected face
                        top, right, bottom, left = fc_locations[matches.index(True)]
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

                        # Display name if recognized
                        cv2.putText(frame, my_name, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                    else:
                        # Draw red box around detected face
                        top, right, bottom, left = fc_locations[0]
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

                        # Display "Unknown user" if not recognized
                        cv2.putText(frame, "Unknown user", (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)

            # Convert the frame to a JPEG image
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            # Yield the frame as a response to the client
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


    # Return the response with MIME type of multipart/x-mixed-replace
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Define the route for the home page
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
  if name_thread is None or not name_thread.is_alive():
      name_thread = threading.Thread(target=publish_name)
      name_thread.start()
      print("Thread started.")
  else:
   print("Thread is already running.")
if __name__ == '__main__':
  app.run(debug=False)
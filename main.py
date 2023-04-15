import threading
import time
from datetime import datetime

import cv2
import face_recognition
import dlib
import os

from flask import Response, Flask, render_template
from paho.mqtt import publish

# Set the path to the folder containing the images to train on
TRAINING_IMAGES_FOLDER = "/home/lqptoptvt/Desktop/images"

# Set the MQTT broker address and port
MQTT_SERVER = "192.168.9.218"
MQTT_PORT = 1883

# Set the MQTT topic to publish to
MQTT_TOPIC = "my_topic"

# Create a list to store the known face encodings
known_encodings = []

# Loop over the images in the training folder and generate encodings for each face
for filename in os.listdir(TRAINING_IMAGES_FOLDER):
    image_path = os.path.join(TRAINING_IMAGES_FOLDER, filename)
    image = face_recognition.load_image_file(image_path)
    encoding = face_recognition.face_encodings(image)[0]
    known_encodings.append(encoding)

# Create a Flask application
app = Flask(__name__)

# Create a face detector using dlib
detector = dlib.get_frontal_face_detector()

# Define a function to publish the name to MQTT topic if there is a match with a known face encoding
def publish_name(name):

    while True:
        try:
            publish.single(MQTT_TOPIC, payload=name, hostname=MQTT_SERVER, port=MQTT_PORT, qos=1)
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

            print(f"User OK !: {name}")
            # Save name and time to file
            with open("log.txt", "a") as f:
                f.write(f"{name} was recognized at {datetime.now()}\n")
            break

# Define the route for the video feed
@app.route('/video_feed')
def video_feed():
    # Open the default camera
    cap = cv2.VideoCapture(0)

    def generate_frames():
        last_publish_time = time.time()
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

                # Compare with known face encodings
                for fc_encoding in fc_encodings:
                    matches = face_recognition.compare_faces(known_encodings, fc_encoding)
                    current_time = time.time()
                    elapsed_time = current_time - last_publish_time
                    if True in matches:
                        # Draw green box around detected face
                        top, right, bottom, left = fc_locations[matches.index(True)]
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

                        # Display name if recognized
                        name = "Phung Cong Nguyen" # Replace with your own name
                        cv2.putText(frame, name, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

                        # Publish name to MQTT topic if there is a match with a known face encoding
                        if elapsed_time >= 15:
                            publish_thread = threading.Thread(target=publish_name, args=(name,))
                            publish_thread.start()
                            last_publish_time = current_time
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
    # Start the Flask application
    app.run(debug=False)
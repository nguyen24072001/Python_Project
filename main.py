import threading
import time
from datetime import datetime

import cv2
import face_recognition
import dlib
import os

from flask import Response, Flask, render_template, request, jsonify
from paho.mqtt import publish

# Đặt đường dẫn đến thư mục chứa hình ảnh để đào tạo trên
TRAINING_IMAGES_FOLDER = "/home/lqptoptvt/Desktop/train/images"
SECOND_PERSON_TRAINING_IMAGES_FOLDER = "/home/lqptoptvt/Desktop/train/images1"

# Đặt địa chỉ và cổng của MQTT broker
# MQTT_SERVER = "192.168.9.218"
MQTT_SERVER = "localhost"
MQTT_PORT = 1883
message_id = 0
# MQTT topic => publish
MQTT_TOPIC = "my_topic"
MQTT_TOPIC2 = "my_topic2"

# Tạo một danh sách để lưu trữ các mã hóa khuôn mặt đã biết
known_encodings = []
KNOWN_NAMES = ["User 1", "User 2"]


def update_known_encodings():
    global known_encodings
    while True:
        # Lặp lại các hình ảnh trong thư mục đào tạo và tạo mã hóa cho từng khuôn mặt
        new_encodings = []
        for filename in os.listdir(TRAINING_IMAGES_FOLDER):
            image_path = os.path.join(TRAINING_IMAGES_FOLDER, filename)
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            if len(encodings) > 0:
                encoding = encodings[0]
                new_encodings.append(encoding)
            else:
                print(f"No face found in {image_path}")
        # Thêm mã hóa cho người thứ hai
        for filename in os.listdir(SECOND_PERSON_TRAINING_IMAGES_FOLDER):
            image_path = os.path.join(SECOND_PERSON_TRAINING_IMAGES_FOLDER, filename)
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            if len(encodings) > 0:
                encoding = encodings[0]
                new_encodings.append(encoding)
            else:
                print(f"No face found in {image_path}")
        # Cập nhật mã hóa đã biết
        known_encodings = new_encodings
        # Sleep 10 giây trước khi kiểm tra lại
        time.sleep(10)

# Bắt đầu chuỗi để cập nhật liên tục các bảng mã đã biết
update_thread = threading.Thread(target=update_known_encodings)

update_thread.start()
# Tạo một ứng dụng Flask
app = Flask(__name__, static_folder='static', static_url_path='/static')

# Tạo máy dò khuôn mặt bằng dlib
detector = dlib.get_frontal_face_detector()

# Function publish name ==> MQTT topic nếu có kết quả khớp với mã hóa khuôn mặt đã biết
def publish_name(name):
    global message_id
    message_id += 1

    while True:

        try:
            publish.single(MQTT_TOPIC, payload=name, hostname=MQTT_SERVER, port=MQTT_PORT, qos=1)
        except ConnectionError as ce:
            print(f"Connection error while publishing message: {ce}")
            # Đợi 5 giây trước khi thử lại
            time.sleep(5)
            continue
        except Exception as e:
            print(f"Error publishing message: {e}")
            # Đợi 10 giây trước khi thử lại
            time.sleep(10)
            continue
        else:

            print(f"User OK !: {name}")
                # Lưu tên và thời gian vào tập tin
            with open("log.txt", "a") as f:

                f.write(f" ID: {message_id} | {name} ĐÃ ĐƯỢC NHẬN DIỆN VÀO LÚC | {datetime.now()}\n")
            break
@app.route('/upload_image', methods=['POST'])
def upload_image():
    try:
        i = 1
        while os.path.exists(os.path.join(TRAINING_IMAGES_FOLDER, 'photo{}.jpg'.format(i))):
            i += 1
        filename = 'photo{}.jpg'.format(i)
        file = request.files['image']
        file.save(os.path.join(TRAINING_IMAGES_FOLDER, filename))
        print(f'Newest picture uploaded User 1 : {filename}')
        payload = f'file://{os.path.join(TRAINING_IMAGES_FOLDER, filename)}'
        publish.single(MQTT_TOPIC2, payload=payload, hostname=MQTT_SERVER, port=MQTT_PORT, qos=1)
        return jsonify({'success': True, 'filename': filename}), 200
    except Exception as e:
        print(f'Error uploading image: {e}')
        return jsonify({'success': False, 'error': 'Failed to upload image'}), 500

@app.route('/upload_image2', methods=['POST'])
def upload_image2():
    try:
        i = 1
        while os.path.exists(os.path.join(SECOND_PERSON_TRAINING_IMAGES_FOLDER, 'photo{}.jpg'.format(i))):
            i += 1
        filename = 'photo{}.jpg'.format(i)
        file = request.files['image']
        file.save(os.path.join(SECOND_PERSON_TRAINING_IMAGES_FOLDER, filename))
        print(f'Newest picture uploaded User 2 : {filename}')
        payload = f'file://{os.path.join(SECOND_PERSON_TRAINING_IMAGES_FOLDER, filename)}'
        publish.single(MQTT_TOPIC2, payload=payload, hostname=MQTT_SERVER, port=MQTT_PORT, qos=1)
        return jsonify({'success': True, 'filename': filename}), 200
    except Exception as e:
        print(f'Error uploading image: {e}')
        return jsonify({'success': False, 'error': 'Failed to upload image'}), 500
# Xác định luồng cho nguồn cấp dữ liệu video_feed
@app.route('/video_feed')
def video_feed():
    # Mở máy ảnh mặc định
    cap = cv2.VideoCapture(0)

    def generate_frames():
        last_publish_time = time.time()
        frame_count = 0
        recognized_count = 0

        while True:

            # Chụp từng khung hình
            ret, frame = cap.read()
            frame_count += 1

            # Chuyển định dạng ảnh BGR sang định dạng RGB
            rgb_frame = frame[:, :, ::-1]

            # Phát hiện khuôn mặt trong khung bằng dlib
            dlib_faces = detector(rgb_frame, 2)

            # Chuyển đổi dlib_faces thành danh sách các bộ tọa độ (trên, phải, dưới, trái)
            fc_locations = [(f.top(), f.right(), f.bottom(), f.left()) for f in dlib_faces]

            if len(fc_locations) > 0:
                # Tìm mã hóa khuôn mặt
                fc_encodings = face_recognition.face_encodings(rgb_frame, fc_locations)

                # So sánh với mã hóa khuôn mặt đã biết
                for fc_location, fc_encoding in zip(fc_locations, fc_encodings):
                    matches = face_recognition.compare_faces(known_encodings, fc_encoding)
                    current_time = time.time()
                    elapsed_time = current_time - last_publish_time
                    if True in matches:
                        # Lấy chỉ số của người được phát hiện
                        i = matches.index(True)
                        # Vẽ hộp màu xanh lá cây xung quanh khuôn mặt được phát hiện
                        top, right, bottom, left = fc_location
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)

                        # Lấy tên của người được công nhận
                        name = KNOWN_NAMES[i]

                        # Tính độ tin cậy nhận dạng
                        confidence = face_recognition.face_distance([known_encodings[i]], fc_encoding)[0]
                        percent_confidence = (1 - confidence) * 100

                        # Vẽ tên và sự tự tin trên hộp màu xanh lá cây
                        cv2.rectangle(frame, (left, bottom + 10), (right, bottom + 30), (0, 255, 0), cv2.FILLED)
                        cv2.putText(frame, f"{name} ({percent_confidence:.2f}% confident)", (left + 6, bottom + 25),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                        # Tính tỷ lệ nhận dạng
                        percent_recognized = recognized_count / frame_count * 100

                        # Vẽ tỷ lệ nhận dạng trên hộp màu xanh lá cây
                        cv2.rectangle(frame, (left, bottom + 40), (right, bottom + 60), (0, 255, 0), cv2.FILLED)
                        cv2.putText(frame, f"Recognition rate: {percent_recognized:.2f}%", (left + 6, bottom + 55),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                        # Publish name => MQTT topic nếu thời gian trôi qua lớn hơn hoặc bằng 15 giây
                        if elapsed_time >= 15:
                            publish_thread = threading.Thread(target=publish_name, args=(name,))
                            publish_thread.start()
                            last_publish_time = current_time
                            recognized_count += 1
                            break

                    else:
                        # Vẽ hộp màu đỏ xung quanh khuôn mặt được phát hiện
                        top, right, bottom, left = fc_locations[0]
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

                        name = "Unknown User"
                        # Hiển thị "Người dùng không xác định" nếu không được nhận dạng
                        cv2.putText(frame, name, (left, top-10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
                        # Publish name => MQTT topic nếu thời gian trôi qua lớn hơn hoặc bằng 15 giây
                        if elapsed_time >= 15:
                            publish_thread = threading.Thread(target=publish_name, args=(name,))
                            publish_thread.start()
                            last_publish_time = current_time
                            break
            #  Chuyển đổi khung thành ảnh JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()

            # Mang lại khung dưới dạng phản hồi cho client
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            # Tính toán và ghi lại tỷ lệ phần trăm nhận dạng khuôn mặt cứ sau 30 khung hình

    # Trả lại phản hồi với loại MIME của multipart/x-mixed-replace
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# Xác định luồng cho trang chủ
@app.route('/')
def index():
    return render_template('index.html', names=KNOWN_NAMES)

@app.route('/', methods=['POST'])
def update_names():
    name1 = request.form['name1']
    name2 = request.form['name2']

    KNOWN_NAMES[0] = name1
    KNOWN_NAMES[1] = name2

    return render_template('index.html', names=KNOWN_NAMES)

if __name__ == '__main__': # Bắt đầu ứng dụng Flask
    app.run(debug=False)
    # Trong Flask, khi chạy ứng dụng, Flask sẽ tìm module chính (tức là file .py chứa đoạn mã này) và chạy nó.
    # Tuy nhiên, khi sử dụng Flask như một module trong một ứng dụng lớn hơn, ví dụ như khi triển khai ứng dụng
    # trên một server, việc sử dụng if __name__ == '__main__': là không cần thiết.
    # Nếu debug được set bằng True, Flask sẽ hiển thị các thông báo lỗi chi tiết trên trình duyệt web.
    # Khi triển khai ứng dụng thực tế, nên đặt debug là False để người dùng không thể xem được
    # thông tin lỗi chi tiết của ứng dụng.

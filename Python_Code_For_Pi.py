import hashlib
import time
import RPi.GPIO as GPIO
from pyfingerprint.pyfingerprint import PyFingerprint
from pyfingerprint.pyfingerprint import FINGERPRINT_CHARBUFFER1
import paho.mqtt.client as mqtt

# Khởi tạo cảm biến vân tay
try:
    # Kết nối với cảm biến vân tay thông qua cổng serial '/dev/ttyS0' với baudrate 57600.
    f = PyFingerprint('/dev/ttyS0', 57600, 0xFFFFFFFF, 0x00000000)
    if (f.verifyPassword() == False):
        raise ValueError('Mật khẩu cảm biến vân tay đã cung cấp là sai!')

# Xử lý ngoại lệ
except Exception as e:
    print('Không thể khởi tạo cảm biến vân tay!')
    print('Thông báo ngoại lệ: ' + str(e))
    exit(1)

# Khởi tạo đèn Led và Servo
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
    print('Đã kết nối với mã kết quả : ' + str(rc))
    client.subscribe('my_topic')
    return 2

# MQTT message callback
def on_message(client, userdata, msg):
    while msg.topic == 'my_topic' and msg.payload == b'Unknown User':
        print('Đang chờ người dùng hợp lệ...')
        return 2

    # Xác định được người dùng hợp lệ thì nháy Led để báo hiệu và kích hoạt Module AS608
    if msg.topic == 'my_topic':    
        print('Xin chào người dùng : ' + str(msg.payload))
        GPIO.output(Pin, GPIO.HIGH) # Led ON !
        time.sleep(1)               # Delay 1 giây
        GPIO.output(Pin, GPIO.LOW)  # Led OFF !
        time.sleep(1)         
        
    while True:  
        try:
            # Quá trình quét mẫu vân tay
            print('Đang đợi mẫu vân tay...')
            
            while (f.readImage() == False):
                pass
         
            # Chuyển đổi hình ảnh đã đọc thành các đặc trưng và lưu trữ nó trong 'charbuffer 1'
            f.convertImage(FINGERPRINT_CHARBUFFER1)

            # Tìm kiếm mẫu
            result = f.searchTemplate()
            positionNumber = result[0]
            accuracyScore = result[1]
             
            # Kiểm tra mẫu vân tay
            if (positionNumber == -1):
                print('No match found!')
                return 1

            print('Đã tìm thấy mẫu ở vị trí #' + str(positionNumber))
            print('Độ tin cậy của mẫu vân tay là :' + str(accuracyScore))

            # Xử lý Servo
            GPIO.output(Pin, GPIO.HIGH)          
            for duty_cycle in range(75, 25, -1): # Vòng lặp for để thay đổi chu kỳ nhiệm vụ của xung PWM đưa vào Servo
             p.ChangeDutyCycle(duty_cycle/10)    # Thiết lập chu kỳ nhiệm vụ
             time.sleep(0.02)                    # Đợi 20ms giữa mỗi bước
            for duty_cycle in range(25, 76):
             p.ChangeDutyCycle(duty_cycle/10)
             time.sleep(0.02)                
            GPIO.output(Pin, GPIO.LOW)

             # Tải Băm mẫu
            f.loadTemplate(positionNumber, FINGERPRINT_CHARBUFFER1)
            characterics = str(f.downloadCharacteristics(FINGERPRINT_CHARBUFFER1)).encode('utf-8')
            print('Hàm băm SHA-2 của mẫu:' + hashlib.sha256(characterics).hexdigest())
            return 1

        # Xử lý ngoại lệ
        except Exception as e:
            print('Lỗi hệ thống!')        
            print('Thông báo ngoại lệ: ' + str(e))
            break

        # Xử lý ngoại lệ khi người dùng ấn phím "Ctrl+C" để dừng chương trình đang chạy
        except KeyboardInterrupt:
            GPIO.cleanup() # Dọn dẹp các GPIO, giải phóng tài nguyên được sử dụng trong quá trình chạy chương trình
            p.stop()       # Dừng quá trình PWM (pulse width modulation)
            break          # Thoát khỏi vòng lặp while đang chạy

# Khởi tạo MQTT client và kết nối đến broker
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect('localhost', 1883, 60)

# Bắt đầu vòng lặp cho MQTT client
client.loop_forever()       

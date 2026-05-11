import cv2
import face_recognition
import numpy as np
from cryptography.fernet import Fernet
import secrets
import os
import sys

# ================= PATH SETUP =================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
known_face_dir = os.path.join(BASE_DIR, "known_faces")
os.makedirs(known_face_dir, exist_ok=True)

face_encodings = []
face_names = []

# ================= LOAD FACES =================
def load_known_faces():
    face_encodings.clear()
    face_names.clear()

    for filename in os.listdir(known_face_dir):
        if filename.endswith((".jpg", ".png")):
            path = os.path.join(known_face_dir, filename)

            image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)

            if len(encodings) > 0:
                face_encodings.append(encodings[0])

                name = filename.split("_")[0]
                face_names.append(name)

    print("Loaded faces:", face_names)


# ✅ LOAD AT START
load_known_faces()

# ================= CAPTURE FACE =================
def capture_and_store_face(name):
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Camera error")
        return False

    print("Press 'C' to capture 3 images")

    count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        cv2.imshow("Capture Face - Press C", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('c'):
            save_path = os.path.join(known_face_dir, f"{name}_{count}.jpg")
            cv2.imwrite(save_path, frame)

            print(f"Saved image {count+1}")
            count += 1

            if count >= 3:
                break

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    load_known_faces()
    return True


# ================= ENCRYPTION =================
# ✅ FIXED KEY (IMPORTANT)
key = b'qYK0XtspiIsFuyI1iRlPHbwELLIpLW0hYLMUp5z3kKM='
cipher_suite = Fernet(key)

def encrypt(data):
    return cipher_suite.encrypt(data.encode())

def decrypt(data):
    return cipher_suite.decrypt(data).decode()


# ================= OTP =================
def generate_otp(length=6):
    return secrets.token_hex(length)[:length].upper()


# ================= FACE MATCH =================
def check_face_match(sender_name):
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("failed")
        return "failed"

    print("Press 'F' to scan face")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        cv2.imshow("Face Authentication - Press F", frame)

        key = cv2.waitKey(1) & 0xFF

        if key == ord('f'):
            print("Scanning face...")

            # 🔥 Resize for better performance
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            face_locations = face_recognition.face_locations(rgb_frame)

            # ✅ Ensure exactly one face
            if len(face_locations) != 1:
                print("failed")
                cap.release()
                cv2.destroyAllWindows()
                return "failed"

            encodings = face_recognition.face_encodings(rgb_frame, face_locations)

            if len(encodings) == 0 or len(face_encodings) == 0:
                print("failed")
                cap.release()
                cv2.destroyAllWindows()
                return "failed"

            face_encoding = encodings[0]

            # 🔥 IMPROVED MATCHING
            matches = face_recognition.compare_faces(face_encodings, face_encoding, tolerance=0.65)
            face_distances = face_recognition.face_distance(face_encodings, face_encoding)

            matched_indexes = [i for i, val in enumerate(matches) if val]

            if len(matched_indexes) > 0:
                best_match_index = min(matched_indexes, key=lambda i: face_distances[i])

                recognized_name = face_names[best_match_index]

                if recognized_name.strip().lower() == sender_name.strip().lower():
                    print("success")
                    cap.release()
                    cv2.destroyAllWindows()
                    return "success"

            print("failed")
            cap.release()
            cv2.destroyAllWindows()
            return "failed"

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("failed")
    return "failed"


# ================= MAIN =================
if __name__ == "__main__":

    # Capture mode
    if len(sys.argv) > 2 and sys.argv[1] == "capture":
        name = sys.argv[2]
        capture_and_store_face(name)

    # Match mode
    else:
        sender = sys.argv[1]
        result = check_face_match(sender)

        # 🔥 VERY IMPORTANT (Django reads this)
        print(result)
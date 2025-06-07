"""
Gestión de cámaras y procesamiento de imágenes
"""
import cv2
import base64
from kivy.graphics.texture import Texture
from config import DEFAULT_CAMERA_INDEX, MAX_CAMERAS_TO_CHECK

class CameraManager:
    def __init__(self):
        self.camera = None
        self.camera_index = DEFAULT_CAMERA_INDEX
        self.num_cameras = 0
        self.latest_frame = None
        self._discover_cameras()
        self.init_camera()

    def _discover_cameras(self):
        """Descubre las cámaras disponibles"""
        self.num_cameras = 0
        for i in range(MAX_CAMERAS_TO_CHECK):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.num_cameras += 1
                cap.release()
            else:
                break
        print(f"Cámaras disponibles: {self.num_cameras}")

    def init_camera(self):
        """Inicializa la cámara"""
        if self.camera:
            self.camera.release()
        try:
            self.camera = cv2.VideoCapture(self.camera_index)
            if not self.camera.isOpened():
                if self.num_cameras > 1:
                    self.camera_index = 1 if self.camera_index == 0 else 0
                    self.camera = cv2.VideoCapture(self.camera_index)
                    if not self.camera.isOpened():
                        self.camera = None
                else:
                    self.camera = None
            if self.camera and self.camera.isOpened():
                print(f"Cámara inicializada en índice: {self.camera_index}")
        except Exception as e:
            print(f"Error al inicializar la cámara: {e}")
            self.camera = None

    def switch_camera(self):
        """Cambia entre cámaras disponibles"""
        if self.num_cameras > 1:
            self.camera_index = 1 if self.camera_index == 0 else 0
            self.init_camera()
            return self.camera and self.camera.isOpened()
        return False

    def get_frame(self):
        """Obtiene un frame de la cámara"""
        if self.camera and self.camera.isOpened():
            ret, frame = self.camera.read()
            if ret:
                self.latest_frame = frame
                return frame
        return None

    def get_display_frame(self):
        """Obtiene frame para mostrar (con flip si es cámara frontal)"""
        frame = self.get_frame()
        if frame is not None:
            return cv2.flip(frame, 1) if self.camera_index == 1 else frame
        return None

    def frame_to_texture(self, frame):
        """Convierte frame a textura de Kivy"""
        if frame is not None:
            buf = frame.tobytes()
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            return texture
        return None

    def frame_to_base64(self, frame):
        """Convierte frame a base64 para envío a APIs"""
        try:
            ret, buffer = cv2.imencode('.jpg', frame)
            if ret:
                return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            print(f"Error al convertir frame a base64: {e}")
        return None

    def release(self):
        """Libera la cámara"""
        if self.camera:
            self.camera.release()
            self.camera = None
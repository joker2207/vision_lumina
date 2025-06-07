"""
Configuraciones y constantes del proyecto
"""
import os

# Configuración del asistente
ASSISTANT_NAME = "Lúmina"

# Credenciales
GEMINI_API_KEY = "AIzaSyDQZ_72X0FfQ_6EefyQZCJQrVFpmnkO9-I"
GOOGLE_CREDENTIALS_FILE = "lumina-credentials.json"

# Configuración de audio
AUDIO_SAMPLE_RATE = 16000
AUDIO_DURATION = 5
TTS_LANGUAGE = "es-ES"

# Configuración de cámara
DEFAULT_CAMERA_INDEX = 0
MAX_CAMERAS_TO_CHECK = 10
CAMERA_FPS = 30

# Configuración de UI
WINDOW_CLEAR_COLOR = (0.15, 0.15, 0.15, 1)
RESULT_LABEL_HEIGHT_HINT = 0.15
CONTROL_LAYOUT_HEIGHT_HINT = 0.25

# Modos de procesamiento
PROCESSING_MODES = [
    'Detección de Objeto',
    'Lectura de QR', 
    'Lectura de Texto (OCR)',
    'Descripción de Imagen',
    'Descripción de Persona'
]

def setup_google_credentials():
    """Configura las credenciales de Google Cloud"""
    json_path = os.path.join(os.path.dirname(__file__), GOOGLE_CREDENTIALS_FILE)
    if os.path.exists(json_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = json_path
        print(f"GOOGLE_APPLICATION_CREDENTIALS establecido a: {json_path}")
        return True
    else:
        print(f"ERROR: Archivo de credenciales no encontrado en {json_path}")
        return False
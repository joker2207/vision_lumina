"""
Manejo de reconocimiento y síntesis de voz
"""
import os
import time
import threading
import queue
import numpy as np
import sounddevice as sd
import scipy.io.wavfile
import io
from gtts import gTTS
from kivy.clock import Clock
from google.cloud import speech_v1p1beta1 as speech
from config import ASSISTANT_NAME, AUDIO_SAMPLE_RATE, AUDIO_DURATION, TTS_LANGUAGE, setup_google_credentials

# Importaciones opcionales para reproducción de audio
try:
    from pydub import AudioSegment
    from pydub.playback import play as pydub_play
except ImportError:
    AudioSegment = None
    pydub_play = None

try:
    import pygame
except ImportError:
    pygame = None

import subprocess
import platform

if platform.system() == "Windows":
    try:
        import winsound
    except ImportError:
        winsound = None
else:
    winsound = None

class SpeechHandler:
    def __init__(self):
        setup_google_credentials()
        self.speech_client = speech.SpeechClient()
        self.speech_config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=AUDIO_SAMPLE_RATE,
            language_code=TTS_LANGUAGE
        )
        self._is_listening = False
        self._is_passive_listening = False
        self._audio_beep_active = False
        self._temp_files = []  # Lista para rastrear archivos temporales

    def start_listening(self, callback):
        """Inicia la escucha de voz"""
        if self._is_listening:
            return
        
        self._is_listening = True
        thread = threading.Thread(target=self._listen_thread, args=(callback,))
        thread.daemon = True
        thread.start()

    def _listen_thread(self, callback):
        """Hilo de escucha de voz"""
        try:
            audio_data = sd.rec(int(AUDIO_DURATION * AUDIO_SAMPLE_RATE), 
                              samplerate=AUDIO_SAMPLE_RATE, channels=1, dtype='int16')
            sd.wait()

            buffer = io.BytesIO()
            scipy.io.wavfile.write(buffer, AUDIO_SAMPLE_RATE, audio_data)
            content = buffer.getvalue()

            audio_config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=AUDIO_SAMPLE_RATE,
                language_code=TTS_LANGUAGE,
                enable_automatic_punctuation=True
            )

            audio_data_gcs = speech.RecognitionAudio(content=content)
            response = self.speech_client.recognize(config=audio_config, audio=audio_data_gcs)

            command = None
            for result in response.results:
                if result.alternatives:
                    command = result.alternatives[0].transcript
                    break

            Clock.schedule_once(lambda dt: callback(command))

        except Exception as e:
            print(f"Error en reconocimiento de voz: {e}")
            Clock.schedule_once(lambda dt: callback(None))
        finally:
            self._is_listening = False

    def start_passive_listening(self, callback):
        """Inicia escucha pasiva para detectar frase clave"""
        if self._is_passive_listening:
            return
        
        self._is_passive_listening = True
        thread = threading.Thread(target=self._passive_listen_loop, args=(callback,))
        thread.daemon = True
        thread.start()

    def _passive_listen_loop(self, callback):
        """Loop de escucha pasiva"""
        while self._is_passive_listening:
            try:
                duration = 3
                audio_data = sd.rec(int(duration * AUDIO_SAMPLE_RATE), 
                                  samplerate=AUDIO_SAMPLE_RATE, channels=1, dtype='int16')
                sd.wait()
                
                buffer = io.BytesIO()
                scipy.io.wavfile.write(buffer, AUDIO_SAMPLE_RATE, audio_data)
                content = buffer.getvalue()
                
                audio = speech.RecognitionAudio(content=content)
                response = self.speech_client.recognize(config=self.speech_config, audio=audio)
                
                for result in response.results:
                    if result.alternatives:
                        text = result.alternatives[0].transcript.lower()
                        if f"{ASSISTANT_NAME.lower()} ayúdame" in text:
                            Clock.schedule_once(lambda dt: callback())
                            self.play_beep("activate")
                            time.sleep(2)
            except Exception as e:
                print(f"Error en escucha pasiva: {e}")
                time.sleep(1)

    def stop_passive_listening(self):
        """Detiene la escucha pasiva"""
        self._is_passive_listening = False

    def play_beep(self, beep_type="general"):
        """Reproduce un beep de feedback"""
        if self._audio_beep_active:
            return
        
        self._audio_beep_active = True
        freq = 800 if beep_type == "activate" else 500
        duration = 0.3
        
        try:
            sd.play(np.sin(2 * np.pi * freq * np.arange(44100 * duration) / 44100), samplerate=44100)
            sd.wait()
        except Exception as e:
            print(f"Error al reproducir beep: {e}")
        finally:
            self._audio_beep_active = False

    def speak_text(self, text):
        """Convierte texto a voz y lo reproduce"""
        if not text or text.strip() == "":
            return

        script_dir = os.path.dirname(__file__)
        timestamp = int(time.time() * 1000)  # Usar timestamp más preciso
        audio_file_mp3 = os.path.join(script_dir, f"temp_speech_{timestamp}.mp3")
        audio_file_wav = os.path.join(script_dir, f"temp_speech_{timestamp}.wav")

        # Agregar archivos a la lista de temporales
        self._temp_files.extend([audio_file_mp3, audio_file_wav])

        try:
            tts = gTTS(text=text, lang='es', slow=False)
            tts.save(audio_file_mp3)
            
            played_successfully = self._try_play_audio(audio_file_mp3, audio_file_wav)
            
            if not played_successfully:
                print("Todos los métodos de reproducción de audio fallaron.")

        except Exception as e:
            print(f"Error al generar texto a voz: {e}")
        finally:
            # Programar limpieza inmediata después de un breve delay
            Clock.schedule_once(lambda dt: self._cleanup_audio_files([audio_file_mp3, audio_file_wav]), 1.0)

    def _try_play_audio(self, mp3_file, wav_file):
        """Intenta reproducir audio con diferentes métodos"""
        # Método 1: Pygame
        if pygame and pygame.mixer.get_init():
            try:
                pygame.mixer.music.load(mp3_file)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                return True
            except Exception as e:
                print(f"Error con pygame: {e}")

        # Método 2: Pydub
        if AudioSegment and pydub_play:
            try:
                audio = AudioSegment.from_mp3(mp3_file)
                pydub_play(audio)
                return True
            except Exception as e:
                print(f"Error con pydub: {e}")

        # Método 3: ffplay
        try:
            subprocess.run(['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', mp3_file],
                         check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"Error con ffplay: {e}")

        # Método 4: winsound (Windows)
        if winsound:
            try:
                subprocess.run(['ffmpeg', '-y', '-i', mp3_file, '-acodec', 'pcm_s16le', 
                              '-ar', '16000', '-loglevel', 'quiet', wav_file],
                             check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                winsound.PlaySound(wav_file, winsound.SND_FILENAME)
                return True
            except Exception as e:
                print(f"Error con winsound: {e}")

        return False

    def _cleanup_audio_files(self, files_to_clean):
        """Limpia archivos temporales de audio"""
        for file_path in files_to_clean:
            self._safe_delete_file(file_path)
        
        # Limpiar archivos de la lista de temporales
        for file_path in files_to_clean:
            if file_path in self._temp_files:
                self._temp_files.remove(file_path)

    def _safe_delete_file(self, file_path):
        """Elimina un archivo de forma segura con reintentos"""
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"Archivo eliminado: {file_path}")
                return True
            except PermissionError:
                print(f"Intento {attempt + 1}: Archivo en uso, esperando... {file_path}")
                time.sleep(0.5)
            except Exception as e:
                print(f"Error al eliminar {file_path}: {e}")
                break
        
        print(f"No se pudo eliminar: {file_path}")
        return False

    def cleanup_all_temp_files(self):
        """Limpia todos los archivos temporales restantes"""
        for file_path in self._temp_files[:]:  # Crear copia de la lista
            if self._safe_delete_file(file_path):
                self._temp_files.remove(file_path)
        
        # Buscar y eliminar archivos temporales huérfanos
        script_dir = os.path.dirname(__file__)
        try:
            for filename in os.listdir(script_dir):
                if filename.startswith("temp_speech_") and (filename.endswith(".mp3") or filename.endswith(".wav")):
                    file_path = os.path.join(script_dir, filename)
                    # Eliminar archivos más antiguos que 1 minuto
                    if os.path.getctime(file_path) < time.time() - 60:
                        self._safe_delete_file(file_path)
        except Exception as e:
            print(f"Error al limpiar archivos huérfanos: {e}")

class VoiceCommandProcessor:
    def __init__(self, app_layout):
        self.app_layout = app_layout

    def process_command(self, command_text):
        """Procesa comandos de voz"""
        if not command_text:
            return

        command_lower = command_text.lower().strip()

        if "escanear" in command_lower:
            self._handle_qr_command()
        elif any(phrase in command_lower for phrase in ["describe lo que veo", "descripción de imagen", "describe lo que tengo al frente"]):
            self._handle_image_description_command()
        elif "cambia a cámara frontal" in command_lower or "pon la cámara selfie" in command_lower:
            self._handle_front_camera_command()
        elif "cambia a cámara trasera" in command_lower:
            self._handle_back_camera_command()
        elif "lee un texto" in command_lower or "lectura de texto" in command_lower:
            self._handle_text_reading_command()
        elif "describe a una persona" in command_lower or "descripción de persona" in command_lower:
            self._handle_person_description_command()
        elif "detección de objeto" in command_lower or "qué es esto" in command_lower:
            self._handle_object_detection_command()
        elif "detente" in command_lower or "para" in command_lower:
            self._handle_stop_command()
        elif "iniciar asistente" in command_lower or "empieza" in command_lower:
            self._handle_start_command()
        elif "salir" in command_lower or "adiós" in command_lower:
            self._handle_exit_command()
        else:
            self._handle_unknown_command(command_text)

    def _handle_qr_command(self):
        self.app_layout.change_mode('Lectura de QR')
        self.app_layout.speech_handler.speak_text("Pasando a escanear código QR.")

    def _handle_image_description_command(self):
        self.app_layout.change_mode('Descripción de Imagen')
        self.app_layout.speech_handler.speak_text("Describiendo lo que tiene al frente.")

    def _handle_front_camera_command(self):
        if self.app_layout.camera_manager.camera_index == 0:
            if self.app_layout.camera_manager.switch_camera():
                self.app_layout.change_mode('Descripción de Persona')
                self.app_layout.speech_handler.speak_text("Cambiando a cámara frontal.")
        else:
            self.app_layout.change_mode('Descripción de Persona')
            self.app_layout.speech_handler.speak_text("Ya está en la cámara frontal.")

    def _handle_back_camera_command(self):
        if self.app_layout.camera_manager.camera_index == 1:
            self.app_layout.camera_manager.switch_camera()
            self.app_layout.speech_handler.speak_text("Cambiando a cámara trasera.")
        else:
            self.app_layout.speech_handler.speak_text("Ya está en la cámara trasera.")

    def _handle_text_reading_command(self):
        self.app_layout.change_mode('Lectura de Texto (OCR)')
        self.app_layout.speech_handler.speak_text("Iniciando lectura de texto.")

    def _handle_person_description_command(self):
        self.app_layout.change_mode('Descripción de Persona')
        self.app_layout.speech_handler.speak_text("Preparando descripción de persona.")

    def _handle_object_detection_command(self):
        self.app_layout.change_mode('Detección de Objeto')
        self.app_layout.speech_handler.speak_text("Cambiando a detección de objeto.")

    def _handle_stop_command(self):
        if self.app_layout.processing_active:
            self.app_layout.toggle_processing()
        self.app_layout.speech_handler.speak_text("Asistente detenido.")

    def _handle_start_command(self):
        if not self.app_layout.processing_active:
            self.app_layout.toggle_processing()
        self.app_layout.speech_handler.speak_text("Asistente iniciado.")

    def _handle_exit_command(self):
        from kivy.app import App
        self.app_layout.speech_handler.speak_text(f"Adiós, {self.app_layout.user_name}. ¡Hasta la próxima!")
        # Limpiar archivos antes de salir
        self.app_layout.speech_handler.cleanup_all_temp_files()
        Clock.schedule_once(lambda dt: App.get_running_app().stop(), 3)

    def _handle_unknown_command(self, command):
        self.app_layout.speech_handler.speak_text(f"No entendí el comando. Intente de nuevo.")
        self.app_layout.update_result_label(f"Comando no reconocido: {command}")
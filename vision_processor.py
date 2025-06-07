"""
Procesamiento de visión con Gemini AI
"""
import requests
import json
from config import GEMINI_API_KEY

class GeminiClient:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"

    def get_response(self, prompt_text, image_data_base64=None):
        """Obtiene respuesta de Gemini AI"""
        parts = [{"text": prompt_text}]
        
        if image_data_base64:
            parts.append({
                "inlineData": {
                    "mimeType": "image/jpeg",
                    "data": image_data_base64
                }
            })

        payload = {"contents": [{"role": "user", "parts": parts}]}
        headers = {'Content-Type': 'application/json'}

        try:
            response = requests.post(self.api_url, headers=headers, 
                                   data=json.dumps(payload), timeout=20)
            response.raise_for_status()
            result = response.json()

            if (result.get("candidates") and len(result["candidates"]) > 0 and 
                result["candidates"][0].get("content") and 
                result["candidates"][0]["content"].get("parts") and 
                len(result["candidates"][0]["content"]["parts"]) > 0):
                
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            
            elif result.get("promptFeedback") and result["promptFeedback"].get("blockReason"):
                reason = result["promptFeedback"]["blockReason"]
                return f"Respuesta bloqueada por políticas de contenido: {reason}."
            
            else:
                return "No pude obtener información de Gemini (respuesta inesperada)."

        except requests.exceptions.Timeout:
            return "La operación tardó demasiado en responder."
        except requests.exceptions.HTTPError as http_err:
            error_details = "Error desconocido."
            try:
                error_json = response.json()
                if error_json.get("error") and error_json["error"].get("message"):
                    error_details = error_json["error"]["message"]
            except json.JSONDecodeError:
                error_details = response.text
            return f"Problema de comunicación con Gemini: {error_details[:100]}"
        except requests.exceptions.RequestException:
            return "Problema de red al procesar la solicitud."
        except Exception:
            return "Error inesperado al obtener respuesta de Gemini."

class VisionProcessor:
    def __init__(self):
        self.gemini_client = GeminiClient()

    def process_object_detection(self, base64_image):
        """Detecta objetos principales en la imagen"""
        prompt = ("Lista los objetos principales y más notables que puedas identificar "
                 "en esta imagen, sin dar descripciones. Solo los nombres de los objetos, "
                 "separados por comas.")
        
        response = self.gemini_client.get_response(prompt, base64_image)
        
        if (response and response.strip() != "" and 
            "no pude obtener información" not in response.lower() and 
            "error" not in response.lower()):
            
            cleaned_objects = response.replace("Objetos principales:", "").strip()
            if cleaned_objects.endswith('.'):
                cleaned_objects = cleaned_objects[:-1]
            return f"He detectado: {cleaned_objects}."
        
        return "No detecté objetos claros o hubo un problema al identificarlos."

    def process_qr_code(self, base64_image):
        """Detecta y extrae información de códigos QR"""
        prompt = ("¿Hay un código QR en esta imagen? Si es así, extrae el texto o la URL "
                 "que contiene. Si no hay, responde 'No se detectó código QR'.")
        
        response = self.gemini_client.get_response(prompt, base64_image)
        
        if (response and response.strip().lower() != "no se detectó código qr" and 
            "no pude obtener" not in response.lower()):
            
            cleaned_qr_data = (response.replace("El código QR contiene: ", "")
                             .replace("El código QR dice: ", "").strip())
            return f"Código QR detectado. Contenido: {cleaned_qr_data}"
        
        return "No se detectó ningún código QR. Asegúrese de que esté bien iluminado y enfocado."

    def process_text_recognition(self, base64_image):
        """Extrae y describe texto de la imagen"""
        # Primero extrae el texto
        extract_prompt = ("Extrae todo el texto visible de esta imagen. Si hay varios "
                         "bloques de texto, sepáralos con saltos de línea. Si no hay texto, "
                         "responde 'No se detectó texto'.")
        
        extracted_text = self.gemini_client.get_response(extract_prompt, base64_image)
        
        if (extracted_text and extracted_text.strip().lower() != "no se detectó texto" and 
            "no pude obtener" not in extracted_text.lower()):
            
            # Luego genera una descripción
            describe_prompt = (f"El siguiente texto ha sido extraído de una imagen: "
                             f"'{extracted_text.strip()}'. Proporciona una breve descripción "
                             f"o resumen de este texto en español, si es que el texto lo permite, "
                             f"o simplemente repite el texto si es muy corto.")
            
            description = self.gemini_client.get_response(describe_prompt)
            
            spoken_description = ""
            if description and description.strip() != "":
                spoken_description = f"La descripción es: {description.strip()}"
            else:
                spoken_description = "No pude generar una descripción para este texto."
            
            return {
                'text': extracted_text.strip(),
                'description': description,
                'spoken': f"He leído el siguiente texto: {extracted_text.strip()}. {spoken_description}"
            }
        
        return "No se detectó texto. Asegúrese de que esté bien iluminado y enfocado."

    def process_image_description(self, base64_image):
        """Genera una descripción detallada de la imagen"""
        prompt = "Describe detalladamente lo que ves en esta imagen. Sé conciso pero informativo."
        
        response = self.gemini_client.get_response(prompt, base64_image)
        
        if response and "no pude obtener" not in response.lower():
            return f"La imagen muestra: {response}"
        
        return "No pude generar una descripción para la imagen. Asegúrese de que sea clara."

    def process_person_description(self, base64_image):
        """Describe a una persona en la imagen"""
        prompt = ("Describe a la persona que aparece en esta imagen. "
                 "Incluye detalles sobre el color de piel, color y estilo de cabello, "
                 "color de ojos (si son visibles), vestimenta y accesorios que lleve, "
                 "basándote estrictamente en lo que es visualmente observable. "
                 "Evita hacer inferencias sobre raza, etnia, nacionalidad, religión, "
                 "orientación sexual o cualquier otro atributo protegido. "
                 "Si no hay persona, responde 'No hay persona'.")
        
        response = self.gemini_client.get_response(prompt, base64_image)
        
        if (response and response.strip().lower() != "no hay persona" and 
            "no pude obtener" not in response.lower()):
            return f"La persona que veo es: {response}"
        
        return ("No detecté una persona clara o no pude generar la descripción. "
               "Asegúrese de que la cámara apunte bien a una persona.")
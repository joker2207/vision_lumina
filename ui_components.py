def on_stop(self):
        """Limpia recursos al cerrar"""
        print("Iniciando limpieza de recursos...")
        
        # Detener procesamiento activo
        self.processing_active = False
        
        # Detener escucha pasiva
        self.speech_handler.stop_passive_listening()
        
        # Limpiar archivos temporales de audio
        self.speech_handler.cleanup_all_temp_files()
        
        # Esperar a que termine el hilo de inferencia
        if self.inference_thread and self.inference_thread.is_alive():
            print("Esperando que termine el hilo de inferencia...")
            self.inference_thread.join(timeout=2)
        
        # Liberar la cámara
        if self.camera_manager:
            print("Liberando cámara...")
            self.camera_manager.release()
        
        # Limpiar pygame si está disponible
        try:
            import pygame
            if pygame and pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                print("Pygame mixer limpiado.")
        except Exception as e:
            print(f"Error al limpiar pygame: {e}")
        
        print("Limpieza de recursos completada.")
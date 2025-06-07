#!/usr/bin/env python3
"""
Lúmina - Asistente Visual
Archivo principal de la aplicación
"""

from kivy.app import App
from kivy.core.window import Window
import pygame
from config import WINDOW_CLEAR_COLOR
from ui_components import LuminaLayout

class LuminaApp(App):
    def build(self):
        Window.clearcolor = WINDOW_CLEAR_COLOR
        if pygame:
            try:
                pygame.mixer.init()
            except Exception as e:
                print(f"Error al inicializar pygame.mixer: {e}")
        return LuminaLayout()

    def on_stop(self):
        if self.root:
            self.root.on_stop()

if __name__ == "__main__":
    LuminaApp().run()
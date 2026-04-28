import requests
from kivy.app import App
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.properties import BooleanProperty, StringProperty, ListProperty
from kivy.clock import Clock
import random
from datetime import datetime, timedelta
import requests
from core import request_http as request
from kivy.graphics import Color, Rectangle

from core import request_http
from core.main_interface import Interface
from core.main_interface import StartInterface
from core.main_interface import MainInterface


Window.size = 360, 702

class ScholarBridge(App):
	def build(self):
		return MainInterface()

if __name__ == "__main__":
	ScholarBridge().run()

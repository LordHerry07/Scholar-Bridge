from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.properties import BooleanProperty, StringProperty, ListProperty, NumericProperty, ColorProperty
from kivy.clock import Clock
import random
from datetime import datetime, timedelta
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
import json
import os

import requests
from core import request_http as request

# Assuming you combine the KV into one file for testing, 
# or keep your original Builder.load_file routing if you prefer them separated.
Builder.load_file('design/mini_interface.kv')

Builder.load_file('design/main_system.kv')

Builder.load_file('design/start_system.kv')

Builder.load_file('design/dynamic_box.kv') 

#-----------------------------------------------------------#
# Starting_Interface
#-----------------------------------------------------------#

class Data:
    user = {}
    product = {}

#Parent
class StartInterface(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

#Children
class Login(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def login_user(self, email, password):
        if email == '' or password == '':
            return
        response = request.log_user(email, password)
        if response.status_code == 200:
            data = response.json()
            Data.user = data.get('user', {})
            
            # --- NEW: Save the session to a local JSON file ---
            try:
                with open('local_state.json', 'w', encoding='utf-8') as f:
                    json.dump(Data.user, f)
            except Exception as e:
                print("Failed to save session:", e)
            # --------------------------------------------------
            
            # Use standard App execution to switch screens
            from kivy.app import App
            App.get_running_app().root.logged = True
            App.get_running_app().root.current = "main"

class Signup(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def sign_user(self, full_name, email, password, confirm_password):
        if password != confirm_password:
            return
        request.add_user(full_name, email, password)
        

# ---------------------------------------------------
# Custom Component Classes for KV
# ---------------------------------------------------
class MenuItem(BoxLayout):
    icon_source = StringProperty('')
    text = StringProperty('')
    text_color = ColorProperty((1, 1, 1, 1))
    icon_bg_color = ColorProperty((0.15, 0.12, 0.20, 1))

class ListTile(BoxLayout):
    icon_source = StringProperty('')
    title = StringProperty('')
    subtitle = StringProperty('')
    show_arrow = BooleanProperty(True)

class TransactionTile(BoxLayout):
    icon_source = StringProperty('')
    title = StringProperty('')
    date = StringProperty('')
    amount = StringProperty('')
    status = StringProperty('')
    is_positive = BooleanProperty(True)

class ChatBubble(BoxLayout):
    text = StringProperty('')
    time = StringProperty('')
    is_sender = BooleanProperty(False)

#-----------------------------------------------------------#
# Mini_Interface
#-----------------------------------------------------------#
class Profile(BoxLayout):
    pass

class ChatBox(BoxLayout):
    pass  

class Wallet(BoxLayout):
    pass

class UserSettings(BoxLayout):
    pass

class LogOut(FloatLayout):
    pass

#-----------------------------------------------------------#
# Dynamic_Box
#-----------------------------------------------------------#
class DynamicActivity(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
class DynamicProduct(Widget):
    initial = StringProperty('N.A')
    fullname = StringProperty('N.A')
    subject = StringProperty('N.A')
    rating = NumericProperty(0)
    title = StringProperty('N.A')
    price = NumericProperty(0)
    condition = StringProperty('N.A')
    product_type = StringProperty('N.A')
    review = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

class DynamicService(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

#-----------------------------------------------------------#
# System_Interface
#-----------------------------------------------------------#

#Parent
class MainInterface(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

#Children
class Dashboard(Widget):
    data = ListProperty([])
    MAX_BARS = 15  # number of visible bars

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.grouped = {}        # slot -> accumulated value
        self.current_slot = 0    # active bar index
        self.max_v = 10          # scaling reference
        self.interval = 5        # seconds per bar

        self.bind(size=self.on_resize, pos=self.on_resize)

    def add(self, dt):
        self.ids.dynamic_product.add_widget(DynamicProduct(size_hint=(1,0), height=200))
        
    def add_value(self, value=None):
        if value is None:
            value = 1
        self.grouped[self.current_slot] = (
            self.grouped.get(self.current_slot, 0) + value
        )
        self.recalculate()

    def next_slot(self, dt):
        self.current_slot += 1
        if len(self.grouped) > self.MAX_BARS:
            oldest = min(self.grouped.keys())
            del self.grouped[oldest]
        self.recalculate()

    def recalculate(self):
        slots = [
            self.current_slot - (self.MAX_BARS - 1 - i)
            for i in range(self.MAX_BARS)
        ]
        self.data = [self.grouped.get(s, 0) for s in slots]
        current_max = max(self.data + [10])
        BUFFER = 1.5
        target_scale = max(current_max * BUFFER, 50)
        self.max_v = self.max_v * 0.9 + target_scale * 0.1
        self.draw_graph()
        Clock.schedule_once(self.auto_scroll, 0)

    def draw_graph(self):
        chart = self.ids.chart
        chart.canvas.clear()
        chart.pos = (0, 0)

        if not self.data:
            return

        max_v = self.max_v
        bar_w = self.width / (self.MAX_BARS)
        spacing = bar_w * 0.3

        with chart.canvas:
            start_x = 0
            for i, v in enumerate(self.data):
                if i == len(self.data) - 1:
                    Color(0.2, 0.7, 0.9, 1)  # current
                elif i == 0:
                    Color(0.6, 0.6, 0.6, 1)  # no previous
                else:
                    prev = self.data[i - 1]
                    if v > prev:
                        Color(0.3, 0.9, 0.3, 1)  # increase
                    elif v < prev:
                        Color(0.9, 0.3, 0.3, 1)  # decrease
                    else:
                        Color(0.6, 0.6, 0.6, 1)  # same

                min_h = 5  
                if v == 0:
                    h = min_h
                else:
                    graph_height = self.height * 0.7
                    h = max((v / max_v) * graph_height, min_h)

                x = start_x + i * (bar_w + spacing)
                y = 0
                Rectangle(pos=(x, y), size=(bar_w, h))

        chart.width = len(self.data) * (bar_w + spacing)
        chart.x = 0

    def auto_scroll(self, dt):
        self.ids.scroll.scroll_x = 1

    def on_resize(self, *args):
        self.draw_graph()

class Product(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fetch products when the widget is first initialized
        Clock.schedule_once(self.get_products, 0.5)
    
    def get_products(self, dt=0):
        # GET request to API
        response = request.get_products()
        if response is None:
            print("Failed to fetch products.")
            return

        container = self.ids.dynamic_product
        container.clear_widgets() 
        
        for data in response:
            # Safely get values from the database row, providing fallbacks
            container.add_widget(DynamicProduct(
                fullname=data.get('full_name', 'Unknown Seller'), 
                initial=data.get('initial', 'U'), 
                title=data.get('title', 'No Title'), 
                rating=float(data.get('rate', 0)), 
                condition=data.get('condition_status', 'N/A'), 
                price=float(data.get('price', 0)), 
                review=int(data.get('review', 0)), 
                product_type=data.get('subject', 'General')
            ))

class Sell(Widget):
    def add_product(self):
        # 1. Grab inputs via the 'text_val' property defined in your custom FormInput
        title = self.ids.title_input.text_val
        description = self.ids.desc_input.text_val
        price = self.ids.price_input.text_val

        # 2. Get the active condition from the ToggleButtons
        condition = "New" # Default fallback
        for btn in self.ids.condition_group.children:
            if btn.state == "down":
                condition = btn.text.replace('[b]', '').replace('[/b]', '')
                break

        if not title or not price:
            print("Missing required fields")
            return

        # 3. Fetch the actual logged-in user dynamically
        user = Data.user or {}
        full_name = user.get('full_name', 'Guest User')
        # Generate initials from full name
        initial = "".join([x[0].upper() for x in full_name.split() if x])

        # 4. Construct the payload
        payload = {
            "initial": initial,
            "full_name": full_name,
            "title": title,
            "subject": "General", # You can add a subject dropdown later
            "rate": 0,            # New products start at 0
            "price": price,
            "review": description, # Mapping description to the review column
            "condition_status": condition,
            "escrow": True,
            "satisfied": False
        }

        # 5. POST to API
        res = request.add_product(payload)

        if res:
            print("✅ Product successfully published to database")
            # Clear the forms after successful submission
            self.ids.title_input.ids.internal_input.text = ""
            self.ids.desc_input.ids.internal_input.text = ""
            self.ids.price_input.ids.internal_input.text = ""
        else:
            print("❌ Failed to publish product")

class Service(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Status(Widget):
    initial = StringProperty("N.A")
    full_name = StringProperty("N.A")
    email = StringProperty("N.A")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Continuously check for user data updates
        Clock.schedule_interval(self.check_info, 1)

    def check_info(self, dt):
        user = Data.user or {}
        name = user.get('full_name', 'Guest User')
        
        # Update the properties bound to the KV file
        self.full_name = name
        self.email = user.get('email', 'Not Logged In')
        self.initial = "".join([x[0].upper() for x in name.split() if x])

class Interface(ScreenManager):
    logged = False
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.set_interface, 2)
        
    def set_interface(self, dt):
        # --- NEW: Read JSON session instead of logged.txt ---
        if os.path.exists('local_state.json'):
            try:
                with open('local_state.json', 'r', encoding='utf-8') as file:
                    session_data = json.load(file)
                    # Verify we actually have user data
                    if session_data and 'email' in session_data:
                        Data.user = session_data
                        self.logged = True
            except Exception as e:
                print("Error reading session:", e)
        # ----------------------------------------------------
        
        if self.logged:
            self.current = "main"
        else:
            self.current = "start"
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.properties import BooleanProperty, StringProperty, ListProperty, NumericProperty, DictProperty
from kivy.clock import Clock
import random
from datetime import datetime, timedelta
import requests
from core import request_http as request
from kivy.graphics import Color, Rectangle

import requests
from core import request_http as request

Builder.load_file('design/mini_interface.kv')
Builder.load_file('design/main_system.kv')
Builder.load_file('design/start_system.kv')
Builder.load_file('design/main_interface.kv')
Builder.load_file('design/dynamic_box.kv')

#-----------------------------------------------------------#
#-----------------------------------------------------------#
# Starting_Interface
#-----------------------------------------------------------#
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
            self.parent.parent.parent.parent.parent.current = "main"

class Signup(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def sign_user(self, full_name, email, password, confirm_password):
        if password != confirm_password:
            return
        request.add_user(full_name, email, password)
        
#-----------------------------------------------------------#
#-----------------------------------------------------------#
# Mini_Interface
#-----------------------------------------------------------#
#-----------------------------------------------------------# 
class Profile(Widget):
	pass
class ChatBox(Widget):
	pass  
class Wallet(Widget):
	pass
class Settings(Widget):
	pass
class LogOut(Widget):
	pass
#-----------------------------------------------------------#
#-----------------------------------------------------------#
# Dynamic_Box
#-----------------------------------------------------------#
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
#-----------------------------------------------------------#
# System_Interface
#-----------------------------------------------------------#
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
        self.interval = 5        # 🔥 seconds per bar (EDIT THIS)

        self.bind(size=self.on_resize, pos=self.on_resize)
        # 🔥 automatically move to next bar every interval
        #Clock.schedule_interval(self.next_slot, self.interval)
#-------------------------------------------------------------#
        #Clock.schedule_interval(self.add, 1)
#-------------------------------------------------------------#
    # ➕ add value (call this whenever you want to feed data)
    def add(self, dt):
        self.ids.dynamic_product.add_widget(DynamicProduct(size_hint=(1,0), height=200))
         
    def add_value(self, value=None):
        if value is None:
            value = 1

        # accumulate in current slot
        self.grouped[self.current_slot] = (
            self.grouped.get(self.current_slot, 0) + value
        )

        self.recalculate()

    # ⏱ move to next bar
    def next_slot(self, dt):
        self.current_slot += 1

        # keep only last MAX_BARS slots
        if len(self.grouped) > self.MAX_BARS:
            oldest = min(self.grouped.keys())
            del self.grouped[oldest]

        self.recalculate()

    # 📊 recompute visible data
    def recalculate(self):
        slots = [
            self.current_slot - (self.MAX_BARS - 1 - i)
            for i in range(self.MAX_BARS)
        ]

        self.data = [self.grouped.get(s, 0) for s in slots]

        # 🔥 stable scaling (no shrinking)
        current_max = max(self.data + [10])

        # 🔥 add buffer so nothing ever hits full height immediately
        BUFFER = 1.5

        target_scale = max(current_max * BUFFER, 50)

        # smooth scale transition (prevents jumping)
        self.max_v = self.max_v * 0.9 + target_scale * 0.1


        self.draw_graph()
        Clock.schedule_once(self.auto_scroll, 0)

    # 🎨 draw bars
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

                # 🎨 color logic
                if i == len(self.data) - 1:
                    Color(0.2, 0.7, 0.9, 1)  # 🔵 current (live)
                elif i == 0:
                    Color(0.6, 0.6, 0.6, 1)  # ⚪ no previous
                else:
                    prev = self.data[i - 1]
                    if v > prev:
                        Color(0.3, 0.9, 0.3, 1)  # 🟢 increase
                    elif v < prev:
                        Color(0.9, 0.3, 0.3, 1)  # 🔴 decrease
                    else:
                        Color(0.6, 0.6, 0.6, 1)  # ⚪ same

                # height calculation
                min_h = 5  # 🔥 minimum visible height (tweak this)
                if v == 0:
                    # show small bar even with no data
                    h = min_h
                else:
                    graph_height = self.height * 0.7
                    h = max((v / max_v) * graph_height, min_h)

                x = start_x + i * (bar_w + spacing)
                y = 0

                Rectangle(pos=(x, y), size=(bar_w, h))

        chart.width = len(self.data) * (bar_w + spacing)
        chart.x = 0

    # 📜 auto scroll to latest bar
    def auto_scroll(self, dt):
        self.ids.scroll.scroll_x = 1

    def on_resize(self, *args):
        self.draw_graph()

class Product(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        #Clock.schedule_interval(self.get_products, 1)
    
    def get_products(self, dt):
        response = request.get_products()  # make sure this is YOUR module
        container = self.ids.dynamic_product
        container.clear_widgets()  # ✅ clear old items
        for data in response:
            container.add_widget(DynamicProduct(fullname=data['full_name'], initial=data['initial'], title=data['title'], rating=data['rate'], condition=data['condition'], price=data['price'], review=data['review'], subject=data['subject']))

class Sell(Widget):

    initial = StringProperty("HCA")
    full_name = StringProperty("Heaven Ajlan")
    title = StringProperty("")
    subject = StringProperty("General")
    review = StringProperty("")
    price = StringProperty("")
    condition_status = StringProperty("")
    rate = NumericProperty(0)
    escrow = BooleanProperty(True)
    satisfied = BooleanProperty(False)

    def add_product(self):
        # ✅ collect inputs safely
        title = self.ids.title_input.text
        description = self.ids.desc_input.text
        price = self.ids.price_input.text

        # ✅ get selected condition
        condition = None
        for btn in self.ids.condition_group.children:
            if btn.state == "down":
                condition = btn.text.replace('[b]', '').replace('[/b]', '')
                break

        # ✅ basic validation
        if not title or not price:
            print("Missing required fields")
            return

        data = {
            "initial": self.initial,
            "full_name": self.full_name,
            "title": self.title,
            "subject": self.subject,
            "rate": self.rate,
            "price": self.price,
            "review": self.review,
            "condition_status": self.condition_status,
            "escrow": self.escrow,
            "satisfied": self.satisfied
        }

        res = request.add_product(data)

        if res:
            print("✅ Product added")
        else:
            print("❌ Failed")

class Service(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Status(Widget):
    initial = StringProperty("N.A")
    full_name = StringProperty("N.A")
    email = StringProperty("N.A")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_interval(self.check_info, 1)

    def check_info(self, dt):
        user = Data.user or {}

        name = user.get('full_name', 'N.A')

        self.full_name = name
        self.email = user.get('email', 'N.A')
        self.initial = "".join([x[0] for x in name.split() if x])
#-----------------------------------------------------------#
#-----------------------------------------------------------#
# Main_Interface
#-----------------------------------------------------------#
#-----------------------------------------------------------#
class Interface(ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
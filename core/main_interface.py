from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.properties import BooleanProperty, StringProperty, ListProperty, NumericProperty, ColorProperty
from kivy.clock import Clock
from kivy.app import App
from kivy.uix.modalview import ModalView
from kivy.uix.behaviors import ButtonBehavior
from datetime import datetime, timedelta
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
import json
import os

import requests
from core import request_http as request

Builder.load_string('''
<ProductDetailsModal>:
    size_hint: 0.85, 0.65
    background: '' 
    background_color: 0, 0, 0, 0 
    
    BoxLayout:
        orientation: 'vertical'
        padding: dp(20)
        spacing: dp(15)
        canvas.before:
            Color:
                rgba: 0.11, 0.12, 0.16, 1  
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [dp(20)]
                
        # Header: Title & Price
        BoxLayout:
            size_hint_y: None
            height: dp(60)
            orientation: 'vertical'
            Label:
                text: f'[b]{root.title}[/b]'
                markup: True
                font_size: sp(18)
                text_size: self.size
                halign: 'left'
                valign: 'bottom'
            Label:
                text: f'[color=#6b59e0]₱{root.price:,.2f}[/color] • Condition: {root.condition}'
                markup: True
                font_size: sp(14)
                color: 0.6, 0.6, 0.6, 1
                text_size: self.size
                halign: 'left'
                valign: 'top'

        # Scrollable Description
        ScrollView:
            do_scroll: False, True
            bar_width: dp(4)
            Label:
                text: root.description
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
                font_size: sp(14)
                color: 0.8, 0.8, 0.8, 1
                halign: 'left'
                valign: 'top'

        # Seller Info Block
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(10)
            canvas.before:
                Color:
                    rgba: 1, 1, 1, 0.05
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(10)]
            # Avatar
            FloatLayout:
                size_hint_x: None
                width: dp(50)
                canvas.before:
                    Color:
                        rgba: 0.43, 0.33, 0.85, 1
                    Ellipse:
                        pos: [self.center_x - dp(17.5), self.center_y - dp(17.5)]
                        size: dp(35), dp(35)
                Label:
                    text: f'[b]{root.initial}[/b]'
                    markup: True
                    font_size: sp(14)
            # Name & Status
            BoxLayout:
                orientation: 'vertical'
                padding: [0, dp(8), 0, dp(8)]
                Label:
                    text: f'[b]{root.fullname}[/b]'
                    markup: True
                    font_size: sp(14)
                    text_size: self.size
                    halign: 'left'
                Label:
                    text: '● Online Now'
                    color: 0.16, 0.67, 0.38, 1
                    font_size: sp(11)
                    text_size: self.size
                    halign: 'left'

        # Action Buttons
        BoxLayout:
            size_hint_y: None
            height: dp(45)
            spacing: dp(10)
            
            # Interested (Heart) Button
            ToggleButton:
                text: '❤ Interested'
                size_hint_x: 0.4
                font_size: sp(13)
                background_color: 0,0,0,0
                color: (1, 0.3, 0.3, 1) if self.state == 'down' else (1, 1, 1, 0.5)
                canvas.before:
                    Color:
                        rgba: (1, 0.3, 0.3, 0.2) if self.state == 'down' else (1, 1, 1, 0.1)
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(10)]
                        
            # Chat Now Button
            Button:
                text: '[b]Chat Now[/b]'
                markup: True
                size_hint_x: 0.6
                font_size: sp(14)
                background_color: 0,0,0,0
                on_release: root.go_to_chat()
                canvas.before:
                    Color:
                        rgba: 0.43, 0.33, 0.85, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(10)]

        # View Profile Button
        Button:
            size_hint_y: None
            height: dp(30)
            text: 'View Full Profile'
            font_size: sp(12)
            color: 0.5, 0.5, 0.5, 1
            background_color: 0,0,0,0
            on_release: root.view_profile()
''')
# --------------------------------------------------------

class ProductDetailsModal(ModalView):
    title = StringProperty("")
    description = StringProperty("")
    price = NumericProperty(0)
    fullname = StringProperty("")
    initial = StringProperty("")
    condition = StringProperty("")


#-----------------------------------------------------------#
# Dynamic_Box
#-----------------------------------------------------------#
class ProductDetailsModal(ModalView):
    title = StringProperty("")
    description = StringProperty("")
    price = NumericProperty(0)
    fullname = StringProperty("")
    initial = StringProperty("")
    condition = StringProperty("")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def go_to_chat(self):
        self.dismiss()
        app = App.get_running_app()
        # Navigate to the Status (info) tab
        app.root.current = 'main'
        main_interface = app.root.get_screen('main')
        main_interface.ids.screenmanager.current = 'info'
        
        # Navigate the inner screenmanager to the ChatBox
        status_screen = main_interface.ids.screenmanager.get_screen('info').children[0]
        status_screen.ids.screenmanager.current = 'chatbox'
        
        # Update Global Header
        main_interface.ids.label1.text = '[b]CHATBOX[/b]'
        main_interface.ids.label2.text = f'Negotiating with {self.fullname}'
        main_interface.ids.back_btn.opacity = 1
        main_interface.ids.back_btn.disabled = False
        
    def view_profile(self):
        self.dismiss()
        app = App.get_running_app()
        # Navigate to Profile
        main_interface = app.root.get_screen('main')
        main_interface.ids.screenmanager.current = 'info'
        status_screen = main_interface.ids.screenmanager.get_screen('info').children[0]
        status_screen.ids.screenmanager.current = 'profile'
        
        # Update Global Header
        main_interface.ids.label1.text = f'[b]{self.fullname.upper()}[/b]'
        main_interface.ids.label2.text = 'Seller Profile'
        main_interface.ids.back_btn.opacity = 1
        main_interface.ids.back_btn.disabled = False

class DynamicActivity(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
class DynamicProduct(ButtonBehavior, BoxLayout):
    initial = StringProperty('N.A')
    fullname = StringProperty('N.A')
    subject = StringProperty('N.A')
    rating = NumericProperty(0)
    title = StringProperty('N.A')
    price = NumericProperty(0)
    condition = StringProperty('N.A')
    product_type = StringProperty('N.A')
    description = StringProperty('No description provided.')
    review = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure description is safely pulled from kwargs if you mapped review -> description previously
        self.description = kwargs.get('description', 'This seller has not provided a description for this listing.')
    
    def on_release(self, *args):
        # Open the pop-up panel when the card is clicked
        modal = ProductDetailsModal(
            title=self.title,
            description=self.description,
            price=self.price,
            fullname=self.fullname,
            initial=self.initial,
            condition=self.condition
        )
        modal.open()

class DynamicService(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


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

        Clock.schedule_once(self.load_stats, 1)

    def load_stats(self, dt=0):
        # 1. Grab the active user
        user = Data.user or {}
        full_name = user.get('full_name')
        if not full_name: 
            return

        # 2. Fetch the data from our new API endpoint
        stats = request.get_user_stats(full_name)
        if stats:
            # 3. Update the Labels
            earnings = stats.get('total_earnings', 0)
            listings = stats.get('active_listings', 0)
            
            self.ids.earnings_label.text = f"[b]₱{earnings:,.2f}[/b]"
            self.ids.active_listings_label.text = f"[b]{listings}[/b]"

            # 4. Update the Bar Graph
            graph_data = stats.get('graph_data', [])
            
            # Pad the list with zeroes if the user has fewer than 15 sales
            while len(graph_data) < self.MAX_BARS:
                graph_data.insert(0, 0)
                
            self.data = graph_data
            
            # Recalculate graph heights based on the highest sale
            current_max = max(self.data + [10])
            BUFFER = 1.5
            self.max_v = max(current_max * BUFFER, 50)
            
            self.draw_graph()

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
        Clock.schedule_once(self.get_products, 0.5)
    
    def get_products(self, dt=0):
        response = request.get_products()
        if not response: 
            return

        container = self.ids.dynamic_product
        container.clear_widgets() 
        
        for data in response:
            # ONLY render if it's NOT a Service
            if data.get('subject') != 'Service':
                container.add_widget(DynamicProduct(
                    fullname=data.get('full_name', 'Unknown'), 
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
        title = self.ids.title_input.text_val
        description = self.ids.desc_input.text_val
        price = self.ids.price_input.text_val

        # 1. Determine the Listing Type based on the toggle buttons
        listing_type = "Textbook"  # Default fallback
        if self.ids.type_service.state == 'down':
            listing_type = "Service"
        elif self.ids.type_notes.state == 'down':
            listing_type = "Notes"

        # 2. Determine the Condition
        condition = "New"
        for btn in self.ids.condition_group.children:
            if btn.state == "down":
                condition = btn.text.replace('[b]', '').replace('[/b]', '')
                break

        if not title or not price:
            print("Missing required fields")
            return

        # 3. Grab the active user
        user = Data.user or {}
        full_name = user.get('full_name', 'Guest User')
        initial = "".join([x[0].upper() for x in full_name.split() if x])

        # 4. Construct payload with the dynamic listing_type
        payload = {
            "initial": initial,
            "full_name": full_name,
            "title": title,
            "subject": listing_type,  # <-- Injects 'Textbook', 'Notes', or 'Service'
            "rate": 0,            
            "price": price,
            "review": 0, 
            "condition_status": condition,
            "escrow": True,
            "satisfied": False
        }

        res = request.add_product(payload)

        if res:
            print(f"✅ {listing_type} successfully published")
            self.ids.title_input.ids.internal_input.text = ""
            self.ids.desc_input.ids.internal_input.text = ""
            self.ids.price_input.ids.internal_input.text = ""
        else:
            print("❌ Failed to publish")

class Service(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fetch services when the widget initializes
        Clock.schedule_once(self.get_services, 0.5)

    def get_services(self, dt=0):
        response = request.get_products()
        if not response: 
            return

        container = self.ids.dynamic_service
        container.clear_widgets() 
        
        for data in response:
            # ONLY render if it IS a Service
            if data.get('subject') == 'Service':
                container.add_widget(DynamicProduct( # Reusing your DynamicProduct UI component
                    fullname=data.get('full_name', 'Unknown'), 
                    initial=data.get('initial', 'U'), 
                    title=data.get('title', 'No Title'), 
                    rating=float(data.get('rate', 0)), 
                    condition=data.get('condition_status', 'N/A'), 
                    price=float(data.get('price', 0)), 
                    review=int(data.get('review', 0)), 
                    product_type=data.get('subject', 'Service')
                ))

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
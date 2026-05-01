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
from kivy.metrics import dp
import requests
from core import request_http as request


# Assuming you combine the KV into one file for testing, 
# or keep your original Builder.load_file routing if you prefer them separated.
Builder.load_file('design/mini_interface.kv')
Builder.load_file('design/main_system.kv')
Builder.load_file('design/start_system.kv')
Builder.load_file('design/dynamic_box.kv') 

#-----------------------------------------------------------#
# Dynamic_Box
#-----------------------------------------------------------#
class ReviewModal(ModalView):
    seller_name = StringProperty("")
    current_rating = NumericProperty(5) # Default to 5 stars
    
    def submit(self):
        my_email = Data.user.get('email')
        comment = self.ids.review_comment.text.strip()
        
        # Call the API
        success = request.submit_review(my_email, self.seller_name, self.current_rating, comment)
        if success:
            print("Review saved!")
            self.dismiss()
        else:
            print("Failed to save review.")
class TransactionTile(BoxLayout):
    def set_data(self, txn_type, amount, date, description):
        # We manually push the text into the IDs we created
        self.ids.desc_label.text = f'[b]{description}[/b]'
        self.ids.date_label.text = date
        
        # Decide the color
        color = "#2ECC71" if txn_type == "Deposit" else "#E74C3C"
        self.ids.amount_label.text = f'[color={color}]{amount}[/color]'

class PublicProfileModal(ModalView):
    target_user = StringProperty("")
    initial = StringProperty("")
    
    def load_profile(self, fullname, initial):
        self.target_user = fullname
        self.initial = initial
        
        # Fetch the data
        profile_data = request.get_user_profile(fullname)
        if not profile_data: return
        
        products = profile_data.get('products', [])
        rating = profile_data.get('rating', 5.0)
        
        # Update UI text
        self.ids.profile_name.text = f'[b]{fullname}[/b]'
        self.ids.profile_stats.text = f'⭐ {rating} Rating • {len(products)} Active Listings'
        
        # Populate the active listings using your existing DynamicProduct card!
        container = self.ids.active_listings
        container.clear_widgets()
        
        for data in products:
            card = DynamicProduct(
                product_id=data.get('id'),
                fullname=data.get('full_name'),
                initial=data.get('initial', 'U'),
                title=data.get('title'),
                price=float(data.get('price', 0)),
                condition=data.get('condition_status', 'Good'),
                product_type=data.get('subject', 'Product'),
                description=str(data.get('review', 'No description'))
            )
            # Make sure the nested cards can also open their own modals!
            card.bind(on_release=lambda instance, c=card: self.open_nested_product(c))
            container.add_widget(card)

    def open_nested_product(self, card):
        self.dismiss() # Close profile to look at the specific item
        card.on_release() # Trigger the standard product modal

class ProductDetailsModal(ModalView):
    product_id = NumericProperty(0)
    title = StringProperty("")
    description = StringProperty("")
    price = NumericProperty(0)
    fullname = StringProperty("")
    initial = StringProperty("")
    condition = StringProperty("")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def buy_item(self):
        my_email = Data.user.get('email')
        if not my_email: 
            print("Not logged in!")
            return
        
        # Call the API to process the transaction
        success = request.buy_product(self.product_id, my_email)
        
        if success:
            print(f"Successfully purchased {self.title}!")
            self.dismiss()
            # Refresh the product list so the bought item disappears
            app = App.get_running_app()
            app.root.get_screen('main').ids.screenmanager.get_screen('product').children[0].get_products()

            review_modal = ReviewModal(seller_name=self.fullname)
            review_modal.open()
        else:
            print("Transaction failed (insufficient funds or item already sold).")

    def go_to_chat(self):
        self.dismiss()
        app = App.get_running_app()
        main_interface = app.root.get_screen('main')
        main_interface.ids.screenmanager.current = 'info'
        status_screen = main_interface.ids.screenmanager.get_screen('info').children[0]
        status_screen.ids.screenmanager.current = 'chatbox'
        
        main_interface.ids.label1.text = '[b]CHATBOX[/b]'
        main_interface.ids.label2.text = f'Negotiating with {self.fullname}'
        main_interface.ids.back_btn.opacity = 1
        main_interface.ids.back_btn.disabled = False
        
        # --- NEW: Tell the ChatBox who we are chatting with and load history ---
        chatbox_widget = status_screen.ids.screenmanager.get_screen('chatbox').children[0]
        chatbox_widget.set_target_user(self.fullname)
        
    def view_profile(self):
        self.dismiss()
        profile_modal = PublicProfileModal()
        profile_modal.load_profile(self.fullname, self.initial)
        profile_modal.open()
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
    product_id = NumericProperty(0)
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
        print(f"DEBUG: Tapped Product ID: {self.product_id}")
        modal = ProductDetailsModal(
            title=self.title,
            description=self.description,
            price=self.price,
            fullname=self.fullname,
            initial=self.initial,
            condition=self.condition
        )
        modal.product_id = self.product_id
        modal.open()

class DynamicService(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

# -----------------------------------------------------------
# Inbox Components
# -----------------------------------------------------------
class InboxTile(ButtonBehavior, BoxLayout):
    partner_name = StringProperty("")
    last_message = StringProperty("")
    time = StringProperty("")

    def open_chat(self):
        app = App.get_running_app()
        main_interface = app.root.get_screen('main')
        status_screen = main_interface.ids.screenmanager.get_screen('info').children[0]
        
        # Navigate from the Inbox to the ChatBox
        status_screen.ids.screenmanager.current = 'chatbox'
        
        # Update headers
        main_interface.ids.label1.text = '[b]CHATBOX[/b]'
        main_interface.ids.label2.text = f'Chatting with {self.partner_name}'
        
        # Inject the partner name and load the messages
        chatbox_widget = status_screen.ids.screenmanager.get_screen('chatbox').children[0]
        chatbox_widget.set_target_user(self.partner_name)

class InboxScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def load_inbox(self, dt=0):
        my_name = Data.user.get('full_name')
        if not my_name: 
            return

        inbox_data = request.get_inbox(my_name)
        container = self.ids.inbox_list
        container.clear_widgets()

        for convo in inbox_data:
            container.add_widget(InboxTile(
                partner_name=convo['partner_name'],
                last_message=convo['last_message'],
                time=convo['timestamp']
            ))

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
    target_user = StringProperty("")
    
    def set_target_user(self, full_name):
        self.target_user = full_name
        self.ids.chat_header_name.text = f'[b]{full_name}[/b]'
        self.load_messages()
        
    def load_messages(self, dt=0):
        if not self.target_user: return
        
        my_name = Data.user.get('full_name', '')
        history = request.get_messages(my_name, self.target_user)
        
        # Clear old dummy messages
        chat_container = self.ids.chat_history
        chat_container.clear_widgets()
        
        for msg in history:
            # If the sender is me, is_sender is True (purple bubble right side)
            is_me = (msg['sender_name'] == my_name)
            chat_container.add_widget(ChatBubble(
                text=msg['message_text'],
                time=msg['timestamp'],
                is_sender=is_me
            ))
            
    def send_new_message(self):
        text_input = self.ids.chat_input
        message_text = text_input.text.strip()
        
        if not message_text or not self.target_user:
            return
            
        my_name = Data.user.get('full_name', '')
        
        # Send to DB
        success = request.send_message(my_name, self.target_user, message_text)
        
        if success:
            text_input.text = "" # Clear the input box
            self.load_messages() # Reload to show the new message

class Wallet(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def load_balance(self):
        my_email = Data.user.get('email')
        if not my_email: return
        
        # 1. Load Balance
        balance = request.get_wallet_balance(my_email)
        self.ids.balance_label.text = f'[b]₱{balance:,.2f}[/b]'
        
        # 2. Load History (NEW)
        history = request.get_wallet_history(my_email)
        container = self.ids.history_list
        container.clear_widgets()

        print(f"🚨 DEBUG: Found {len(history)} transactions! Building tiles...")
        container.height = len(history) * dp(75)
        for item in history:
            sign = "+" if item['type'] == 'Deposit' else "-"
            formatted_amount = f"{sign} ₱{float(item['amount']):,.2f}"
            
            tile = TransactionTile()
            tile.ids.desc_label.text = f'[b]{item["description"]}[/b]'
            tile.ids.date_label.text = item['date']
            
            color = "#2ECC71" if item['type'] == "Deposit" else "#E74C3C"
            tile.ids.amount_label.text = f'[color={color}]{formatted_amount}[/color]'
            
            container.add_widget(tile)
        
        
    def process_transaction(self, action):
        my_email = Data.user.get('email')
        amount_text = self.ids.amount_input.text.strip()
        
        if not my_email or not amount_text:
            return
            
        try:
            amount = float(amount_text)
        except ValueError:
            print("Invalid amount")
            return
            
        success = request.process_wallet_transaction(my_email, amount, action)
        if success:
            self.ids.amount_input.text = "" # Clear input
            self.load_balance() # Refresh UI
        else:
            print(f"Failed to {action} funds.")

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
    current_category = StringProperty('All')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.all_products = [] # Cache to hold data so we don't spam the API
        Clock.schedule_once(self.get_products, 0.5)

    def set_category(self, cat):
        self.current_category = cat
        self.filter_products() # Re-filter instantly when a button is clicked

    def get_products(self, dt=0):
        response = request.get_products(satisfied=0)
        if not response: 
            return

        # Save the master list to memory
        self.all_products = response 
        
        # Trigger the initial render
        self.filter_products() 

    def filter_products(self, *args):
        # 1. Grab the search text
        search_text = self.ids.search_bar.text.lower()
        
        container = self.ids.dynamic_product
        container.clear_widgets() 
        
        for data in self.all_products:
            item_subject = data.get('subject', '')
            
            # 2. Skip Services (They belong on the Service screen)
            if item_subject == 'Service':
                continue
                
            # 3. Apply Category Filter
            if self.current_category != 'All' and item_subject != self.current_category:
                continue
                
            # 4. Apply Search Bar Filter (Checks both Title and Description)
            title = data.get('title', '').lower()
            desc = str(data.get('review', '')).lower()
            if search_text and (search_text not in title and search_text not in desc):
                continue
                
            # 5. If it passes all filters, draw the widget!
            container.add_widget(DynamicProduct(
                product_id=data.get('id'), 
                fullname=data.get('full_name'), 
                initial=data.get('initial'), 
                title=data.get('title'), 
                price=float(data.get('price', 0)),
                condition=data.get('condition_status'),
                product_type=item_subject,
                description=str(data.get('review'))
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
    current_category = StringProperty('All')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.all_services = [] # Cache to hold data
        Clock.schedule_once(self.get_services, 0.5)

    def set_category(self, cat):
        self.current_category = cat
        self.filter_services() # Re-filter instantly when a button is clicked

    def get_services(self, dt=0):
        response = request.get_products(satisfied=0)
        if not response: 
            return

        # Save the master list to memory
        self.all_services = response 
        self.filter_services() 

    def filter_services(self, *args):
        search_text = self.ids.search_bar.text.lower()
        container = self.ids.dynamic_service
        container.clear_widgets() 
        
        for data in self.all_services:
            item_subject = data.get('subject', '')
            
            # 1. ONLY process items explicitly marked as 'Service' in the DB
            if item_subject != 'Service':
                continue
                
            title = data.get('title', '').lower()
            desc = str(data.get('review', '')).lower()
            
            # 2. Smart Category Filter (Checks if sub-category word is in title/desc)
            cat = self.current_category.lower()
            if cat != 'all' and cat not in title and cat not in desc:
                continue
                
            # 3. Search Bar Filter
            if search_text and (search_text not in title and search_text not in desc):
                continue
                
            # 4. If it passes all filters, draw the widget!
            container.add_widget(DynamicProduct(
                product_id=data.get('id'),
                fullname=data.get('full_name', 'Unknown'), 
                initial=data.get('initial', 'U'), 
                title=data.get('title', 'No Title'), 
                rating=float(data.get('rate', 0)), 
                condition=data.get('condition_status', 'N/A'), 
                price=float(data.get('price', 0)), 
                product_type=item_subject,
                description=str(data.get('review', 'No description'))
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
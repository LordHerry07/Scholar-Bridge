from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
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
from kivy.animation import Animation
from core import request_http as request
import threading
from kivy.core.window import Window
from kivy.clock import mainthread
from kivy.uix.relativelayout import RelativeLayout
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.togglebutton import ToggleButton
import calendar
from kivy.factory import Factory

Builder.load_file('design/modal_interface.kv')
Builder.load_file('design/main_system.kv')
Builder.load_file('design/start_system.kv')
Builder.load_file('design/dynamic_box.kv') 
Builder.load_file('design/animations.kv') 

IS_OFFLINE_MODE = False
CACHE_FILE = "scholarbridge_offline_data.json"


class LoadingOverlay(FloatLayout):
    angle = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Rotates continuously
        self.anim = Animation(angle=-360, duration=1.0)
        self.anim.repeat = True
        
    def start(self):
        self.opacity = 1
        self.anim.start(self)
        
    def stop(self):
        self.anim.stop(self)
        self.opacity = 0
        self.angle = 0

def save_to_cache(key, data):
    """Saves API data to the local offline file."""
    # 1. Read the existing file so we don't overwrite other tabs
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
        except: pass 
        
    # 2. Update the specific key (like 'products' or 'dashboard')
    cache[key] = data
    
    # 3. Save it back to the phone
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def load_from_cache(key):
    """Loads backup data if the server is unreachable."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                return cache.get(key, []) # Return the data, or an empty list
        except: pass
    return []

class OfflineBanner(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 1. Start completely off-screen at the very top
        self.size_hint = (1, None)
        self.y = Window.height 
        
    def show(self):
        # 2. Slide down into view smoothly
        anim = Animation(y=Window.height - self.height, duration=0.3, t='out_quad')
        anim.start(self)
        
        # 3. Wait 3 seconds, then trigger the hide animation
        Clock.schedule_once(self.hide, 3)

    def hide(self, *args):
        anim = Animation(opacity=0, duration=0.4)
        # Use Window.remove_widget to clean up properly
        anim.bind(on_complete=lambda *x: Window.remove_widget(self) if self.parent else None)
        anim.start(self)

# Global helper function to spawn the banner from anywhere
def show_offline_warning(*args):
    from kivy.metrics import dp
    banner = OfflineBanner()
    banner.height = dp(35) # Height of the banner
    Window.add_widget(banner) # Attach globally to the absolute top layer
    banner.show()
#-----------------------------------------------------------#
# Modal_Interface
#-----------------------------------------------------------#
class SimulatedNotification(RelativeLayout):
    message_text = StringProperty("")

    def show(self):
        self.opacity = 0
        # Simple fade in animation
        anim = Animation(opacity=1, duration=0.4)
        anim.start(self)
        # Auto-hide after 5 seconds
        Clock.schedule_once(self.hide, 5)

    def hide(self, *args):
        anim = Animation(opacity=0, duration=0.4)
        # Cleanup: remove from Window safely
        anim.bind(on_complete=lambda *x: Window.remove_widget(self) if self.parent else None)
        anim.start(self)

# Add this helper to your main StartInterface or App class

class ResetPasswordModal(ModalView):
    user_email = StringProperty('')
    def verify_otp(self, raw_code):
        code = str(raw_code).strip()
        if len(code) != 6:
            # FIX: Use your existing NotificationModal instead of self.show_error
            NotificationModal().show("Input Error", "Please enter the 6-digit code.", is_error=True)
            return

        # Use the property we stored
        result = request.verify_reset_otp(self.user_email, code)
        
        if result.get("success"):
            self.dismiss()
            # This is the hand-off to the next modal
            NewPasswordModal(user_email=self.user_email).open()
            # Success notification
            NotificationModal().show("Success", "Identity Verified! You can now reset your password.", is_error=False)
            print("Access Granted! Identity Verified.")
        else:
            # Handle server-side errors (like incorrect/expired codes)
            error_msg = result.get('error', 'Invalid code')
            NotificationModal().show("Verification Failed", error_msg, is_error=True)

        # Use the property we stored
        result = request.verify_reset_otp(self.user_email, code)
        
        if result.get("success"):
            self.dismiss()
            # Logic for success (e.g., opening the password change modal)
            print("Access Granted! Identity Verified.")
        else:
            print(f"Verification Failed: {result.get('error')}")
            # Trigger your notification popup here

def finalize_password_reset(email, new_password):
    url = f"{BASE_URL}/reset_password"
    payload = {"email": email, "password": new_password}
    response = safe_request(requests.post, url, json=payload)
    
    if response and response.status_code == 200:
        return {"success": True}
    
    return {"success": False, "error": "Could not update password"}

class NewPasswordModal(ModalView):
    user_email = StringProperty('')

    def change_password(self, pwd, confirm):
        # Strip invisible trailing spaces
        clean_pwd = str(pwd).strip()
        clean_confirm = str(confirm).strip()

        if not clean_pwd or clean_pwd != clean_confirm:
            NotificationModal().show("Error", "Passwords do not match!", is_error=True)
            return

        result = request.finalize_password_reset(self.user_email, clean_pwd)
        
        if result.get("success"):
            self.dismiss()
            NotificationModal().show("Success", "Password changed! You can now log in.", is_error=False)
        else:
            NotificationModal().show("Error", "Server update failed.", is_error=True)

class ServerSelectorModal(ModalView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Pre-fill the input box with the current saved IP
        Clock.schedule_once(self.populate_input, 0.1)

    def set_online_mode(self, ip_address):
        """Called when the user enters an IP and clicks Connect"""
        global IS_OFFLINE_MODE
        IS_OFFLINE_MODE = False
        
        # ... your existing logic to update the request URL with the new IP ...
        print(f"🌍 Switching to ONLINE mode at {ip_address}")
        self.dismiss() # Close the modal

    def set_offline_mode(self):
        global IS_OFFLINE_MODE
        IS_OFFLINE_MODE = True
        print("📴 Switching to OFFLINE mode. Network bypassed.")
        
        self.dismiss() # Close the modal
        
        # --- THE INSTANT JUMP ---
        app = App.get_running_app()
        
        # Fake the login state so the app knows we are allowed in
        app.root.logged = True 
        
        # Teleport directly to your main interface!
        app.root.current = "main"

    def populate_input(self, dt):
        # Strip the http:// for a cleaner user experience
        clean_ip = request.BASE_URL.replace("http://", "").replace("https://", "")
        self.ids.server_ip_input.text = clean_ip

    def save_server(self):
        ip_text = self.ids.server_ip_input.text.strip()
        if ip_text:
            request.set_base_url(ip_text)
            print(f"🚨 SERVER REROUTED TO: {request.BASE_URL}")
            NotificationModal().show("Server Updated", f"App is now pointing to:\n{request.BASE_URL}", is_error=False)
        self.dismiss()

class NotificationModal(ModalView):
    def show(self, title, message, is_error=False):
        self.ids.notif_title.text = f'[b]{title}[/b]'
        if is_error:
            self.ids.notif_title.color = (0.88, 0.25, 0.25, 1) # Red for errors
        else:
            self.ids.notif_title.color = (0.16, 0.67, 0.38, 1) # Green for success
        self.ids.notif_message.text = message
        self.open()
class ReviewModal(ModalView):
    seller_name = StringProperty("")
    current_rating = NumericProperty(0) # Default to 0 stars
    
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
#-----------------------------------------------------------#
# Dynamic_Box
#-----------------------------------------------------------#
class ActivityTile(BoxLayout):
    activity_type = StringProperty("")
    item_title = StringProperty("")
    amount = StringProperty("")
    time_ago = StringProperty("")
    
    icon_bg_color = ColorProperty([0, 0, 0, 0]) 
    text_color = ColorProperty([1, 1, 1, 1])
    icon_source = StringProperty("")
    
    # Bypass auto-binding and manually set everything securely
    def setup_tile(self, act_type, title, amt, time_str):
        self.activity_type = act_type
        self.item_title = title
        self.time_ago = time_str
        
        # --- 1. SOLD (Green) ---
        if act_type.lower() == 'sold':
            self.icon_bg_color = [0.18, 0.77, 0.41, 0.15] 
            self.text_color = [0.18, 0.77, 0.41, 1]      
            self.icon_source = "assets/trend_up.png"                        
            self.amount = f"+{amt}"
               
        # --- 2. PURCHASED (Red) ---
        elif act_type.lower() == 'purchased':
            self.icon_bg_color = [0.85, 0.26, 0.33, 0.15] 
            self.text_color = [0.85, 0.26, 0.33, 1]      
            self.icon_source = "assets/trend_down.png"                        
            self.amount = f"-{amt}"
            
        # --- 3. SUBSCRIBED (Purple) ---
        elif act_type.lower() == 'subscribed':
            self.icon_bg_color = [0.42, 0.35, 0.88, 0.15] 
            self.text_color = [0.6, 0.4, 0.95, 1]      
            self.icon_source = "assets/subscribed.png"                        
            self.amount = f"-{amt}"
            
        # --- 4. UNSUBSCRIBED (Gray) ---
        elif act_type.lower() == 'unsubscribed':
            self.icon_bg_color = [0.5, 0.5, 0.5, 0.15] 
            self.text_color = [0.6, 0.6, 0.6, 1]      
            self.icon_source = "assets/unsubscribed.png" # Great reuse of the logout icon                        
            self.amount = "Ended"
            
        elif act_type.lower() == 'listed':
            self.icon_bg_color = [0.2, 0.6, 0.9, 0.15] 
            self.text_color = [0.2, 0.6, 0.9, 1]      
            self.icon_source = "assets/sell.png" # Nice reuse of your sell icon                        
            self.amount = "New"
            
        else:
            self.amount = amt

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
        rating = profile_data.get('rating', 0)
        
        # Update UI text
        self.ids.profile_name.text = f'[b]{fullname}[/b]'
        self.ids.profile_stats.text = f'⭐ {rating} Rating • {len(products)} Active Listings'
        
        # Populate the active listings using existing DynamicProduct card
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
                description=str(data.get('review', 'No description')),
                # --- NEW LINE: Use the seller rating! ---
                rating=round(float(data.get('seller_rating', rating)), 1)
            )
            # Make sure the nested cards can also open their own modals
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
        my_name = Data.user.get('full_name')
        if not my_email: 
            print("Not logged in!")
            return
        
        if my_name == self.fullname:
            NotificationModal().show("Action Blocked", "You cannot buy your own listing.", is_error=True)
            return

        result = request.buy_product(self.product_id, my_email)
        
        # Safely check success
        is_success = result.get("success") if isinstance(result, dict) else bool(result)
        
        if is_success:
            # 1. Destroy the modal instantly
            self.dismiss()
            
            # --- 2. THE DEEP SCAN RADAR REFRESH ---
            app = App.get_running_app()
            
            if app.root and app.root.has_screen('main'):
                main_screen = app.root.get_screen('main')
                
                try:
                    # Dive explicitly into the ScreenManager to scan EVERY tab
                    sm = main_screen.ids.screenmanager
                    for screen in sm.screens: 
                        for widget in screen.walk():
                            # Use the raw string name to bypass any Python class confusion
                            widget_name = type(widget).__name__
                            
                            if widget_name == 'Product':
                                widget.get_products()
                            elif widget_name == 'Service':
                                widget.get_services()
                            elif widget_name == 'Dashboard':
                                widget.load_stats()
                            elif widget_name == 'Wallet':
                                widget.load_balance()
                except Exception as e:
                    print(f"Radar Refresh Error: {e}")
                        
            # 3. Show Success Popup
            try:
                
                notif = NotificationModal()
                notif.ids.notif_title.text = "[color=#2ecc71]Transaction Successful[/color]"
                notif.ids.notif_message.text = "Funds have been safely moved to Escrow."
                notif.open()
            except Exception as e:
                print(f"Could not open success notification: {e}")

        else:
            # 4. Show Error Popup
            try:
                notif = NotificationModal()
                notif.ids.notif_title.text = "[color=#e74c3c]Transaction Failed[/color]"
                error_msg = result.get("error", "An unknown error occurred.") if isinstance(result, dict) else "Transaction failed."
                notif.ids.notif_message.text = error_msg
                notif.open()
            except Exception as e:
                print(f"Could not open error notification: {e}")

    def go_to_chat(self):
        self.dismiss()
        app = App.get_running_app()
        app.root.get_screen('main').toggle_footer(False)
        main_interface = app.root.get_screen('main')
        main_interface.ids.screenmanager.current = 'info'
        status_screen = main_interface.ids.screenmanager.get_screen('info').children[0]
        status_screen.ids.screenmanager.current = 'chatbox'
        
        main_interface.ids.label1.text = '[b]CHATBOX[/b]'
        main_interface.ids.label2.text = f'Negotiating with {self.fullname}'
        main_interface.ids.back_btn.opacity = 1
        main_interface.ids.back_btn.disabled = False
        
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

class BookingCalendarModal(ModalView):
    selected_date = NumericProperty(0)
    service_title = StringProperty("Service")
    service_id = NumericProperty(0) # <--- The Receiver
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.build_calendar, 0.1)
        
    def build_calendar(self, dt):
        if not hasattr(self.ids, 'calendar_grid'): return
        grid = self.ids.calendar_grid
        grid.clear_widgets()
        
        now = datetime.now()
        first_day = now.replace(day=1)
        offset = (first_day.weekday() + 1) % 7
        
        days = ['S', 'M', 'T', 'W', 'T', 'F', 'S']
        for day in days:
            grid.add_widget(Label(text=f'[b]{day}[/b]', markup=True, color=(0.5, 0.5, 0.5, 1)))
            
        for _ in range(offset): 
            grid.add_widget(Label(text=''))
            
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        for i in range(1, days_in_month + 1):
            btn = ToggleButton(
                text=str(i),
                group='dates',
                background_normal='',
                background_down='',
                background_color=(0.15, 0.16, 0.22, 1)
            )
            btn.bind(state=self.on_date_select)
            grid.add_widget(btn)
            
    def on_date_select(self, instance, value):
        if value == 'down':
            instance.background_color = (0.42, 0.35, 0.88, 1) 
            self.selected_date = int(instance.text)
        else:
            instance.background_color = (0.15, 0.16, 0.22, 1)

    def confirm_booking(self):
        if self.selected_date == 0:
            NotificationModal().show("Action Blocked", "Please select a date.", is_error=True)
            return
            
        now = datetime.now()
        selected_dt = now.replace(day=self.selected_date)
        weekday_str = selected_dt.strftime("%A") 
        
        n = self.selected_date
        suffix = "th" if 11 <= n <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        day_str = f"{n}{suffix} {weekday_str}"
        
        my_email = Data.user.get('email')
        
        print(f"🚀 FIRING TO API: Subscribing to Service #{self.service_id}")
        
        success = request.subscribe_service(self.service_id, my_email, day_str)
        
        if success:
            NotificationModal().show("Subscription Active", f"Your subscription starts on {day_str}.", is_error=False)
            self.dismiss()
            
            # Deep Scan Refresh
            app = App.get_running_app()
            if app.root and app.root.has_screen('main'):
                try:
                    sm = app.root.get_screen('main').ids.screenmanager
                    for screen in sm.screens: 
                        for widget in screen.walk():
                            if type(widget).__name__ == 'Service':
                                widget.get_services() 
                except: pass
        else:
            NotificationModal().show("Error", "Could not complete booking.", is_error=True)

class ServiceDetailsModal(ModalView):
    service_id = NumericProperty(0)
    title = StringProperty("")
    description = StringProperty("")
    price = NumericProperty(0)
    fullname = StringProperty("")
    rate_type = StringProperty("")

    def subscribe_service(self):
        my_name = Data.user.get('full_name')
        if my_name == self.fullname:
            NotificationModal().show("Action Blocked", "You cannot subscribe to your own service.", is_error=True)
            return
        self.dismiss()
        modal = BookingCalendarModal()
        modal.service_title = self.title
        modal.service_id = self.service_id 
        modal.open()

#-----------------------------------------------------------#
# Dynamic_Box
#-----------------------------------------------------------#
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
        self.description = kwargs.get('description', 'This seller has not provided a description for this listing.')

    def on_press(self):
        anim = Animation(opacity=0.5, duration=0.05)
        anim.start(self)

    def on_release(self, *args):
        anim = Animation(opacity=1.0, duration=0.15)
        anim.start(self)
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

class DynamicService(ButtonBehavior, BoxLayout):
    service_id = NumericProperty(0)
    initial = StringProperty('N.A')
    fullname = StringProperty('N.A')
    subject = StringProperty('N.A')
    rating = StringProperty('0.0')
    review_count = NumericProperty(0)
    title = StringProperty('N.A')
    price = NumericProperty(0)
    rate_type = StringProperty('hr') 
    schedule = StringProperty('Mon-Fri')
    description = StringProperty('No description provided.')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_press(self):
        anim = Animation(opacity=0.5, duration=0.05)
        anim.start(self)

    def on_release(self, *args):
        anim = Animation(opacity=1.0, duration=0.15)
        anim.start(self)
        
        modal = ServiceDetailsModal(
            service_id=self.service_id,
            title=self.title,
            description=self.description,
            price=self.price,
            fullname=self.fullname,
            rate_type=self.rate_type
        )
        modal.open()

    def open_booking(self):
        modal = BookingCalendarModal()
        modal.service_title = self.title 
        modal.service_id = self.service_id 
        modal.open()

# -----------------------------------------------------------
# Inbox Components (Hub)
# -----------------------------------------------------------
class InboxTile(ButtonBehavior, BoxLayout):
    partner_name = StringProperty("")
    last_message = StringProperty("")
    time = StringProperty("")

    def on_press(self):
        anim = Animation(opacity=0.5, duration=0.05)
        anim.start(self)
        
    def on_release(self, *args):
        anim = Animation(opacity=1.0, duration=0.15)
        anim.start(self)
        self.open_chat()

    def open_chat(self):
        app = App.get_running_app()
        main_interface = app.root.get_screen('main')
        status_screen = main_interface.ids.screenmanager.get_screen('info').children[0]
        status_screen.ids.screenmanager.current = 'chatbox'
        
        main_interface.ids.label1.text = '[b]CHATBOX[/b]'
        main_interface.ids.label2.text = f'Chatting with {self.partner_name}'
        
        chatbox_widget = status_screen.ids.screenmanager.get_screen('chatbox').children[0]
        chatbox_widget.set_target_user(self.partner_name)

class InboxScreen(BoxLayout):
    current_tab = StringProperty('chats')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def switch_tab(self, tab_name):
        self.current_tab = tab_name
        self.load_hub_data()

    def load_hub_data(self, dt=0):
        my_name = Data.user.get('full_name')
        my_email = Data.user.get('email')
        if not my_name or not my_email: return

        container = self.ids.hub_list
        container.clear_widgets()

        if self.current_tab == 'chats':
            inbox_data = request.get_inbox(my_name)
            for convo in inbox_data:
                container.add_widget(InboxTile(
                    partner_name=convo['partner_name'],
                    last_message=convo['last_message'],
                    time=convo['timestamp']
                ))
                
        elif self.current_tab == 'products':
            hub_data = request.get_my_hub(my_email)
            for prod in hub_data.get('products', []):
                tile = Factory.OwnedItemTile()
                tile.title = prod['title']
                tile.subtitle = f"Purchased from {prod['full_name']}"
                tile.seller_name = prod['full_name'] # <--- NEW LINE
                tile.icon_bg = (0.16, 0.67, 0.38, 1) 
                container.add_widget(tile)
                
        elif self.current_tab == 'subs':
            hub_data = request.get_my_hub(my_email)
            for sub in hub_data.get('subscriptions', []):
                tile = Factory.SubscriptionItemTile()
                tile.title = sub['title']
                tile.schedule = sub.get('booked_schedule', 'Pending')
                tile.service_id = sub['id']
                # Subscriptions need a slight API tweak to return 'full_name' too, 
                # assuming it does, pass it here:
                tile.seller_name = sub.get('full_name', 'Unknown Seller') # <--- NEW LINE
                container.add_widget(tile)

    def unsubscribe(self, service_id):
        success = request.unsubscribe_service(service_id)
        if success:
            NotificationModal().show("Unsubscribed", "You have ended this subscription.", is_error=False)
            self.load_hub_data() 
            
            app = App.get_running_app()
            try:
                sm = app.root.get_screen('main').ids.screenmanager
                for screen in sm.screens: 
                    for widget in screen.walk():
                        if type(widget).__name__ == 'Service':
                            widget.get_services() 
            except: pass
    def open_review(self, seller_name):

        modal = ReviewModal()
        modal.seller_name = seller_name
        modal.open()

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

    def open_server_settings(self):
        ServerSelectorModal().open()

    def trigger_otp_notification(self, otp_code):
        # We create the notification widget
        notif = SimulatedNotification()
        notif.message_text = f"ScholarBridge: Your code is {otp_code}"
        
        # FIX: We add it to the Window directly. 
        # This bypasses the ScreenManager's "Screens only" rule.
        Window.add_widget(notif) 
        
        # Since Window doesn't use relative coordinates like layouts,
        # we ensure it stays at the top of the screen.
        notif.y = Window.height - notif.height - dp(10)
        
        notif.show()
    def switch_tab(self, tab_name):
        sm = self.ids.screenmanager
        
        # Change direction securely without creating new transition objects
        if tab_name == 'login':
            sm.transition.direction = 'right'
        else:
            sm.transition.direction = 'left'
            
        sm.current = tab_name

#Children
class Login(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def open_reset_modal(self, email):
        # The result now contains the 'debug_otp' from the server
        result = request.request_password_reset(email)
        
        if result.get("success"):
            # 1. Catch the code that the bridge just extracted
            otp_to_show = result.get("debug_otp", "ERROR")
            
            # 2. Trigger the slide-down notification with that code
            self.trigger_otp_notification(otp_to_show)
            
            # 3. Open the entry modal
            ResetPasswordModal(user_email=email).open()
        else:
            # Handle user not found or server errors
            error = result.get("error", "Unknown error")
            print(f"Error: {error}")

    def trigger_otp_notification(self, otp_code):
        # 1. Create the notification instance
        notif = SimulatedNotification()
        notif.message_text = f"ScholarBridge: Your code is {otp_code}"
        
        # 2. Add it to the Window directly (bypasses ScreenManager restrictions)
        Window.add_widget(notif) 
        
        # 3. Position it manually at the top of the Window
        # We subtract the notification's height and a small margin from the Window height
        notif.y = Window.height - notif.height - dp(10)
        
        # 4. Start the entry animation
        notif.show()

    def login_user(self, email, password):
        global IS_OFFLINE_MODE
        if IS_OFFLINE_MODE:
            print("📴 Offline Mode Active: Faking login and bypassing server!")
            App.get_running_app().root.logged = True
            App.get_running_app().root.current = "main"
            return 
            
        if email == '' or password == '':
            return
            
        # 1. Start the Spinner!
        self.ids.loading_overlay.start()
        
        # 2. Fire the Background Thread so UI doesn't freeze
        threading.Thread(target=self._thread_login, args=(email, password), daemon=True).start()

    def _thread_login(self, email, password):
        try:
            response = request.log_user(email, password)
            # Use Clock.schedule_once to safely jump back to the Main UI Thread
            Clock.schedule_once(lambda dt: self._process_login(response), 0)
        except Exception as e:
            print(f"Login Thread Error: {e}")
            Clock.schedule_once(lambda dt: self._process_login(None), 0)

    def _process_login(self, response):
        # 3. Stop the Spinner!
        self.ids.loading_overlay.stop()
        
        if response and response.status_code == 200:
            data = response.json()
            Data.user = data.get('user', {})
            
            try:
                import json 
                with open('local_state.json', 'w', encoding='utf-8') as f:
                    json.dump(Data.user, f)
            except Exception as e:
                print("Failed to save session:", e)
            
            app = App.get_running_app()
            app.root.logged = True
            app.root.current = "main"
        else:
            NotificationModal().show("Login Failed", "Invalid email or password.", is_error=True)

class Signup(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def sign_user(self, full_name, email, password, confirm_password):
        # 0. Clean up accidental trailing spaces from the inputs
        full_name = full_name.strip()
        email = email.strip()
        password = password.strip()
        confirm_password = confirm_password.strip()

        # 1. Constraint: Must fill up everything
        if not full_name or not email or not password or not confirm_password:
            NotificationModal().show("Action Blocked", "Please fill up all fields.", is_error=True)
            return

        # 2. Constraint: Fullname must have > 3 elements (4 or more words)
        name_elements = full_name.split()
        if len(name_elements) < 3:
            NotificationModal().show("Invalid Name", "Please enter your complete full name (First, Middle, Last, etc).", is_error=True)
            return

        # --- UPDATED 3. Constraint: Any valid .edu.ph email ---
        if "@" not in email or not email.endswith(".edu.ph"):
            NotificationModal().show(
                "Invalid Email", 
                "You must use a valid Philippine university email ending in '.edu.ph' (e.g., student@up.edu.ph).", 
                is_error=True
            )
            return

        # 4. Constraint: Password must be greater than 7 characters
        if len(password) <= 7:
            NotificationModal().show("Weak Password", "Password must be at least 8 characters long.", is_error=True)
            return

        # 5. Constraint: Passwords must match
        if password != confirm_password:
            NotificationModal().show("Error", "Passwords do not match.", is_error=True)
            return
            
        # --- ALL CHECKS PASSED: FIRE THE ENGINE ---
        
        # 1. Start the Spinner!
        self.ids.loading_overlay.start()
        
        # 2. Fire the Background Thread
        threading.Thread(target=self._thread_signup, args=(full_name, email, password), daemon=True).start()

    def _thread_signup(self, full_name, email, password):
        try:
            response = request.add_user(full_name, email, password)
            Clock.schedule_once(lambda dt: self._process_signup(response), 0)
        except Exception as e:
            print(f"Signup Thread Error: {e}")
            Clock.schedule_once(lambda dt: self._process_signup(None), 0)

    def _process_signup(self, response):
        # 3. Stop the Spinner!
        self.ids.loading_overlay.stop()
        
        # In request_http, add_user returns a JSON dict directly, not a response object
        if response and "error" not in response:
            self.ids.sign_name.text = ''
            self.ids.sign_mail.text = ''
            self.ids.sign_pass.text = ''
            self.ids.sign_confirm_pass.text = ''
            NotificationModal().show("Success", "Account created! Please log in.", is_error=False)
            
            # Auto-switch the toggle button to Login mode
            app = App.get_running_app()
            try:
                start_screen = app.root.ids.start
                start_screen.ids.login.state = 'down'
                start_screen.ids.signup.state = 'normal'
                start_screen.switch_tab('login')
            except: pass
        else:
            error_msg = response.get("error", "Could not create account.") if response else "Server offline."
            NotificationModal().show("Signup Failed", error_msg, is_error=True)
        

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
# =========================================================== #
#                   1B. EDIT PROFILE MODAL                    #
# =========================================================== #
class EditProfileModal(ModalView):
    def __init__(self, profile_screen_ref, **kwargs):
        super().__init__(**kwargs)
        self.profile_screen_ref = profile_screen_ref
        from kivy.clock import Clock
        Clock.schedule_once(self.load_modal_info, 0.1)

    def load_modal_info(self, dt=0):
        user = Data.user or {}
        full_name = user.get('full_name', 'Guest User')
        
        if hasattr(self.ids, 'modal_display_name_label'):
            self.ids.modal_display_name_label.text = f"[b]{full_name}[/b]"
            self.ids.modal_initial_label.text = f"[b]{''.join([x[0].upper() for x in full_name.split() if x])}[/b]"

        # Populate all text boxes with current data
        if hasattr(self.ids, 'name_input'):
            self.ids.name_input.ids.internal_input.text = full_name
            self.ids.role_input.ids.internal_input.text = user.get('role', '')
            self.ids.age_input.ids.internal_input.text = str(user.get('age', ''))
            self.ids.birthday_input.ids.internal_input.text = user.get('birthday', '')
            self.ids.location_input.ids.internal_input.text = user.get('location', '')
            
            self.ids.password_input.ids.internal_input.password = True
            self.ids.confirm_password_input.ids.internal_input.password = True

    def auto_locate(self):
        # 1. Update UI to show we are searching
        if hasattr(self.ids, 'location_input'):
            self.ids.location_input.ids.internal_input.text = "Locating..."
            self.ids.location_input.ids.internal_input.foreground_color = (0.43, 0.33, 0.85, 1) # Purple text
        
        # 2. Fire the background thread so Kivy doesn't freeze!
        threading.Thread(target=self._fetch_osm_location, daemon=True).start()

    def _fetch_osm_location(self):
        try:
            # STEP A: Try ip-api.com (Higher success rate on Linux/Desktops)
            # This returns JSON with 'lat', 'lon', 'city', and 'regionName'
            response = requests.get('http://ip-api.com/json/', timeout=5)
            ip_data = response.json()

            if ip_data.get('status') == 'success':
                lat = ip_data.get('lat')
                lon = ip_data.get('lon')
                
                # We can actually get the city directly from this API!
                city = ip_data.get('city', '')
                region = ip_data.get('regionName', '')
                
                # Try to refine it with OpenStreetMap for better accuracy
                try:
                    headers = {'User-Agent': 'ScholarBridgeApp/1.0'}
                    osm_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=14"
                    osm_res = requests.get(osm_url, headers=headers, timeout=5).json()
                    
                    addr = osm_res.get('address', {})
                    # OSM is more specific (can find neighborhood or town)
                    refined_city = addr.get('city') or addr.get('town') or addr.get('village') or city
                    refined_region = addr.get('state') or region
                    
                    final_location = f"{refined_city}, {refined_region}".strip(", ")
                except:
                    # Fallback to the basic IP data if OSM fails
                    final_location = f"{city}, {region}".strip(", ")

                if final_location and "None" not in final_location:
                    self._update_location_ui(final_location, False)
                else:
                    self._update_location_ui("Location not found", True)
            else:
                self._update_location_ui("GPS Detection Failed", True)

        except Exception as e:
            print(f"Location Error: {e}")
            self._update_location_ui("Network Error", True)

    @mainthread
    def _update_location_ui(self, result_text, is_error):
        # 3. Safely update the Kivy UI back on the main thread
        if hasattr(self.ids, 'location_input'):
            self.ids.location_input.ids.internal_input.text = result_text
            # Revert color back to white if successful, or red if failed
            color = (0.88, 0.25, 0.25, 1) if is_error else (1, 1, 1, 1)
            self.ids.location_input.ids.internal_input.foreground_color = color

    def save_profile(self):
        user = Data.user or {}
        email = user.get('email')
        old_name = user.get('full_name')

        if hasattr(self.ids, 'name_input'):
            # Grab all the fresh inputs
            new_name = self.ids.name_input.ids.internal_input.text.strip()
            new_role = self.ids.role_input.ids.internal_input.text.strip()
            new_age = self.ids.age_input.ids.internal_input.text.strip()
            new_birthday = self.ids.birthday_input.ids.internal_input.text.strip()
            new_location = self.ids.location_input.ids.internal_input.text.strip()
            
            new_password = self.ids.password_input.ids.internal_input.text.strip()
            confirm_password = self.ids.confirm_password_input.ids.internal_input.text.strip()
            
            if not new_name:
                NotificationModal().show("Action Blocked", "Your full name cannot be empty.", is_error=True)
                return
                
            if new_password != confirm_password:
                NotificationModal().show("Action Blocked", "Passwords do not match.", is_error=True)
                return

            # Call API with the expanded variables
            result = request.update_profile(
                email, old_name, new_name, new_password, 
                new_role, new_age, new_birthday, new_location
            )
            
            is_success = result.get("success") if isinstance(result, dict) else bool(result)

            if is_success:
                # Save to Local Session
                Data.user['full_name'] = new_name
                Data.user['role'] = new_role
                Data.user['age'] = new_age
                Data.user['birthday'] = new_birthday
                Data.user['location'] = new_location
                
                import json
                try:
                    with open('local_state.json', 'w', encoding='utf-8') as f:
                        json.dump(Data.user, f)
                except: pass

                # Close Modal & Refresh Screen
                self.dismiss()
                self.profile_screen_ref.load_info()
                
                # Wake up Status Bar
                from kivy.app import App
                app = App.get_running_app()
                if app.root and app.root.has_screen('main'):
                    try:
                        sm = app.root.get_screen('main').ids.screenmanager
                        for screen in sm.screens: 
                            for widget in screen.walk():
                                if type(widget).__name__ == 'Status':
                                    widget.check_info(0) 
                    except: pass

                NotificationModal().show("Profile Updated", "Your changes have been saved.", is_error=False)
            else:
                error_msg = result.get("error", "An unknown error occurred.") if isinstance(result, dict) else "Update failed."
                NotificationModal().show("Update Failed", error_msg, is_error=True)


# =========================================================== #
#                  1A. READ-ONLY PROFILE                      #
# =========================================================== #
class Profile(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from kivy.clock import Clock
        Clock.schedule_once(self.load_info, 0.5)

    def load_info(self, dt=0):
        user = Data.user or {}
        full_name = user.get('full_name', 'Guest User')
        
        if hasattr(self.ids, 'display_name_label'):
            self.ids.display_name_label.text = f"[b]{full_name}[/b]"
            self.ids.display_email_label.text = user.get('email', '')
            self.ids.initial_label.text = f"[b]{''.join([x[0].upper() for x in full_name.split() if x])}[/b]"

        # Inject Data into Read-Only Tiles
        if hasattr(self.ids, 'tile_email'):
            self.ids.tile_email.ids.subtitle_lbl.text = user.get('email', 'Not set')
            self.ids.tile_role.ids.subtitle_lbl.text = user.get('role', 'Not set')
            self.ids.tile_age.ids.subtitle_lbl.text = str(user.get('age', 'Not set'))
            self.ids.tile_birthday.ids.subtitle_lbl.text = user.get('birthday', 'Not set')
            self.ids.tile_location.ids.subtitle_lbl.text = user.get('location', 'Not set')

    def open_edit_modal(self):
        EditProfileModal(profile_screen_ref=self).open()
class ChatBox(BoxLayout):

    target_user = StringProperty("")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Check the database for new messages every 2 seconds!
        Clock.schedule_interval(self.load_messages, 2.0)

    def set_target_user(self, full_name):
        self.target_user = full_name
        self.ids.chat_header_name.text = f'[b]{full_name}[/b]'
        initials = "".join([x[0].upper() for x in full_name.split() if x])[:2]
        if hasattr(self.ids, 'chat_header_initials'):
            self.ids.chat_header_initials.text = f'[b]{initials}[/b]'
        self.ids.chat_history.clear_widgets()
        self.load_messages()
        
    def load_messages(self, dt=0):
        if not self.target_user: return
        if self.parent and self.parent.manager and self.parent.manager.current != 'chatbox':
            return
        my_name = Data.user.get('full_name', '')
        history = request.get_messages(my_name, self.target_user)
        
        # Clear old dummy messages
        chat_container = self.ids.chat_history
        if len(chat_container.children) == len(history):
            return
        chat_container.clear_widgets()
        
        for msg in history:
            # If the sender is me, is_sender is True (purple bubble right side)
            is_me = (msg['sender_name'] == my_name)
            chat_container.add_widget(ChatBubble(
                text=msg['message_text'],
                time=msg['timestamp'],
                is_sender=is_me
            ))
        if hasattr(self.ids, 'chat_scroll'):
            Clock.schedule_once(lambda dt: setattr(self.ids.chat_scroll, 'scroll_y', 0), 0.1)
            
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class LogOut(FloatLayout):
    def perform_logout(self):
        # 1. Clear the active session memory
        Data.user = {}
        
        # 2. Delete the saved token file
        if os.path.exists('local_state.json'):
            try: 
                os.remove('local_state.json')
            except: 
                pass
                
        # 3. Boot the user back to the login screen
        app = App.get_running_app()
        app.root.logged = False
        app.root.current = "start"
        
        # 4. Reset the Main Interface silently in the background
        try:
            app.root.get_screen('main').switch_tab('dashboard')
        except: 
            pass

#-----------------------------------------------------------#
# System_Interface
#-----------------------------------------------------------#

#Parent
class MainInterface(Screen):
    # This property will hold our live notification count
    #unread_count = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Check for notifications every 3 seconds
        Clock.schedule_interval(self.poll_notifications, 3.0)
        
    def poll_notifications(self, dt):
        name = Data.user.get('full_name')
        if name:
            app = App.get_running_app()
            if app:
                app.unread_count = request.get_unread_count(name)
    def toggle_footer(self, show=True):
        if not hasattr(self.ids, 'footer_nav'): return
        
        if show:
            self.ids.footer_nav.opacity = 1
            self.ids.footer_nav.disabled = False
            self.ids.footer_nav.size_hint_y = 0.1
        else:
            self.ids.footer_nav.opacity = 0
            self.ids.footer_nav.disabled = True
            self.ids.footer_nav.size_hint_y = None
            self.ids.footer_nav.height = 0

    def switch_tab(self, tab_name):
        sm = self.ids.screenmanager
        current_tab = sm.current

        # 1. Define the logical left-to-right order of the footer tabs
        tab_order = ['dashboard', 'product', 'sell', 'service', 'info']

        # 2. Modify the EXISTING transition direction (The Kivy Fix!)
        if current_tab in tab_order and tab_name in tab_order:
            current_idx = tab_order.index(current_tab)
            target_idx = tab_order.index(tab_name)

            if target_idx > current_idx:
                sm.transition.direction = 'left'
            elif target_idx < current_idx:
                sm.transition.direction = 'right'

        # 3. Switch the Screen
        sm.current = tab_name

        # 4. Centralized UI Updates
        label1 = self.ids.label1
        label2 = self.ids.label2
        back_btn = self.ids.back_btn

        back_btn.opacity = 0
        back_btn.disabled = True

        if tab_name == 'dashboard':
            label1.text = '[b]DASHBOARD[/b]'
            label2.text = 'your activity overview'
            sm.get_screen('dashboard').children[0].load_stats()
            
        elif tab_name == 'product':
            label1.text = '[b]PRODUCT[/b]'
            label2.text = 'textbooks, notes & materials'
            sm.get_screen('product').children[0].get_products(0)
            
        elif tab_name == 'sell':
            label1.text = '[b]CREATE LISTING[/b]'
            label2.text = 'publish your products & services'
            
        elif tab_name == 'service':
            label1.text = '[b]SERVICE[/b]'
            label2.text = 'tutoring, review & freelance help'
            sm.get_screen('service').children[0].get_services(0)
            
        elif tab_name == 'info':
            label1.text = '[b]MENU[/b]'
            label2.text = 'manage your account'
            info_screen = sm.get_screen('info').children[0]
            info_screen.load_user_stats()
            info_screen.ids.screenmanager.current = 'menu'

#Children
class Dashboard(Widget):
    MAX_BARS = 15

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []
        self.max_v = 50
        
        # Bind to screen resize so the graph always scales perfectly
        self.bind(size=self.on_resize, pos=self.on_resize)
        Clock.schedule_once(self.load_stats, 1)
        Clock.schedule_once(self.load_recent_activity, 0.5)
    def load_recent_activity(self, dt=0):
        user = Data.user or {}
        
        # THE FIX: Grab the email instead of full_name!
        email = user.get('email')
        
        if not email: 
            Clock.schedule_once(self.load_recent_activity, 1)
            return

        container = self.ids.recent_activity_list
        container.clear_widgets()
        
        try:
            # Pass the email to the API
            activities = request.get_recent_activity(email)
        except Exception as e:
            print(f"Dashboard Activity Error: {e}")
            activities = []

        if not activities:
            empty_label = Label(
                text="No recent transactions yet.",
                color=(1, 1, 1, 0.4),
                size_hint_y=None,
                height=dp(50)
            )
            container.add_widget(empty_label)
            return

        for act in activities:
            tile = ActivityTile()
            tile.setup_tile(
                act_type=act.get("type", "Unknown"),
                title=act.get("title", "Item"),
                amt=str(act.get("amount", "0.00")),
                time_str=act.get("time", "Just now")
            )
            container.add_widget(tile)

    def load_stats(self, dt=0):
        user = Data.user or {}
        full_name = user.get('full_name')
        
        if not full_name: 
            Clock.schedule_once(self.load_stats, 1)
            return

        stats = request.get_user_stats(full_name)
        
        profile_data = request.get_user_profile(full_name)
        real_rating = profile_data.get('rating', 0.0) if profile_data else 0.0
        
        if stats:
            # 1. Update the Main Large Labels
            if hasattr(self.ids, 'earnings_label'):
                self.ids.earnings_label.text = f"[b]₱{stats.get('total_earnings', 0):,.2f}[/b]"
            if hasattr(self.ids, 'active_listings_label'):
                self.ids.active_listings_label.text = f"[b]{stats.get('active_listings', 0)}[/b]"
            if hasattr(self.ids, 'items_sold_label'):
                self.ids.items_sold_label.text = f"[b]{stats.get('items_sold', 0)}[/b]"
            if hasattr(self.ids, 'rating_label'):
                self.ids.rating_label.text = f"[b]{float(real_rating):.1f}[/b]"

            # 2. Update the Tiny Trend Badges dynamically!
            e_pct = stats.get('earnings_pct', 0)
            e_color = "2ECC71" if e_pct >= 0 else "E74C3C" # Green if up, Red if down
            e_sign = "+" if e_pct > 0 else ""

            s_pct = stats.get('sold_pct', 0)
            s_color = "2ECC71" if s_pct >= 0 else "E74C3C"
            s_sign = "+" if s_pct > 0 else ""

            l_pct = stats.get('listings_pct', 0)
            l_color = "2ECC71" if l_pct >= 0 else "E74C3C"
            l_sign = "+" if l_pct > 0 else ""

            if hasattr(self.ids, 'earnings_trend'):
                self.ids.earnings_trend.text = f"[color=#{e_color}]{e_sign}{e_pct}%[/color]"
                
            if hasattr(self.ids, 'listings_trend'):
                self.ids.listings_trend.text = f"[color=#{l_color}]{l_sign}{l_pct}%[/color]"
                
            if hasattr(self.ids, 'sold_trend'):
                self.ids.sold_trend.text = f"[color=#{s_color}]{s_sign}{s_pct}%[/color]"
                
            if hasattr(self.ids, 'rating_trend'):
                self.ids.rating_trend.text = f"[b]{stats.get('top_percentage', 'Top 1%')}[/b]"

            # Set Graph Data
            graph_data = stats.get('graph_data', [])
            while len(graph_data) < self.MAX_BARS:
                graph_data.insert(0, 0)
                
            self.data = graph_data
            current_max = max(self.data + [10])
            self.max_v = max(current_max * 1.5, 50)
            
            self.draw_graph()
            self.load_recent_activity()

    def draw_graph(self):
        chart = self.ids.chart
        
        # Clear previous renders without deleting the KV background color
        chart.canvas.after.clear()

        if not self.data:
            return

        max_v = self.max_v
        bar_w = self.width / self.MAX_BARS
        spacing = bar_w * 0.3

        with chart.canvas.after:
            for i, v in enumerate(self.data):
                
                # Dynamic Color Logic
                if i == len(self.data) - 1 and v > 0:
                    Color(0.16, 0.67, 0.38, 1)  # Newest sale is Green!
                elif i == len(self.data) - 1:
                    Color(0.2, 0.7, 0.9, 1) 
                elif i == 0:
                    Color(0.6, 0.6, 0.6, 1)  
                else:
                    prev = self.data[i - 1]
                    if v > prev:
                        Color(0.3, 0.9, 0.3, 1)  
                    elif v < prev:
                        Color(0.9, 0.3, 0.3, 1)  
                    else:
                        Color(0.6, 0.6, 0.6, 1)  

                min_h = dp(5)  
                if v == 0:
                    h = min_h
                else:
                    graph_height = chart.height * 0.8
                    h = max((v / max_v) * graph_height, min_h)

                # Anchor bars securely to the chart widget
                x = chart.x + (i * (bar_w + spacing))
                y = chart.y 
                
                Rectangle(pos=(x, y), size=(bar_w, h))

        # Adjust width for smooth scrolling
        chart.width = len(self.data) * (bar_w + spacing)

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
        # 1. Trigger: Show skeletons instantly
        container = self.ids.dynamic_product
        container.clear_widgets()
        for _ in range(5):
            container.add_widget(ProductSkeleton())
            
        # 2. Spawn a background thread so the UI never freezes!
        threading.Thread(target=self._thread_fetch_products, daemon=True).start()

    def _thread_fetch_products(self):
        global IS_OFFLINE_MODE
        
        # --- THE BYPASS: Intentional Offline Mode ---
        if IS_OFFLINE_MODE:
            response = load_from_cache('marketplace_products')
            Clock.schedule_once(lambda dt: self._on_products_fetched(response), 0)
            return # Stop here! Don't even try to hit the network.
            
        # --- NORMAL ONLINE MODE ---
        try:
            response = request.get_products(satisfied=0)
            if response:
                save_to_cache('marketplace_products', response)
                
        except Exception as e:
            # Unintentional Network Error (Only shows if they WANTED to be online)
            print(f"🚨 Network Error: {e} | Falling back to Offline Mode...")
            Clock.schedule_once(show_offline_warning, 0)
            response = load_from_cache('marketplace_products')

        Clock.schedule_once(lambda dt: self._on_products_fetched(response), 0)

    def _on_products_fetched(self, response):
        if response:
            self.all_products = response
        self.filter_products()

    def filter_products(self, *args):
        search_text = self.ids.search_bar.text.lower()
        container = self.ids.dynamic_product
        container.clear_widgets() 
        
        for data in self.all_products:
            # 1. Safe extraction to prevent NoneType crashes
            item_type = str(data.get('product_type') or data.get('subject') or '')
            item_subject = str(data.get('subject') or 'General')
            
            # Skip Services (They belong on the Service screen)
            if item_type == 'Service':
                continue
                
            # 2. Legacy Name Safetynet! (If an old DB entry says "Textbook", treat it as "Textbooks")
            if self.current_category == 'Textbooks' and item_type == 'Textbook':
                item_type = 'Textbooks'
            if self.current_category == 'Guidelines' and (item_type == 'Guides' or item_type == 'Guide'):
                item_type = 'Guidelines'
                
            # 3. Apply Category Filter
            if self.current_category != 'All' and item_type != self.current_category:
                continue
                
            # 4. Apply Search Bar Filter (Checks both Title and Description)
            title = str(data.get('title') or '').lower()
            desc = str(data.get('review') or '').lower()
            if search_text and (search_text not in title and search_text not in desc):
                continue
                
            # 5. Bulletproof Widget Rendering
            try:
                p_id = int(data.get('id') or 0)
                price_val = float(data.get('price') or 0.0)
                seller_rating = float(data.get('seller_rating') or 0.0)
                
                container.add_widget(DynamicProduct(
                    product_id=p_id, 
                    fullname=data.get('full_name') or 'Unknown', 
                    initial=data.get('initial') or 'U', 
                    title=data.get('title') or 'No Title', 
                    price=price_val,
                    condition=data.get('condition_status') or 'Good',
                    product_type=item_type,
                    subject=item_subject,
                    description=str(data.get('review') or 'No description provided.'),
                    rating=round(seller_rating, 1)
                ))
            except Exception as e:
                # If a specific card fails, Kivy prints the error here instead of crashing the whole screen!
                print(f"🚨 CRASH AVERTED: Skipping a corrupt product card because: {e}")

class Sell(Widget):
    # This Boolean controls the entire UI state automatically!
    is_service_mode = BooleanProperty(False)

    def add_product(self):
        # 1. Safely extract core fields
        title = self.ids.title_input.ids.internal_input.text.strip() if 'title_input' in self.ids else ""
        subject_name = self.ids.subject_input.ids.internal_input.text.strip() if 'subject_input' in self.ids else ""
        description = self.ids.desc_input.ids.internal_input.text.strip() if 'desc_input' in self.ids else ""
        price_text = self.ids.price_input.ids.internal_input.text.strip() if 'price_input' in self.ids else ""

        # 2. DYNAMIC VALIDATION
        missing_fields = []
        if not title: missing_fields.append("Title")
        if not subject_name: missing_fields.append("Subject")
        if not price_text: missing_fields.append("Price")
        
        if missing_fields:
            fields_str = " and ".join(missing_fields)
            NotificationModal().show("Missing Information", f"Please enter a {fields_str} to list your item.", is_error=True)
            return

        # 3. Strict Price Validation
        try:
            price = float(price_text)
            if price <= 0: raise ValueError
        except ValueError:
            NotificationModal().show("Invalid Price", "Please enter a valid amount greater than 0.", is_error=True)
            return

        # 4. Grab User Data
        user = Data.user or {}
        full_name = user.get('full_name', 'Guest User')
        initial = "".join([x[0].upper() for x in full_name.split() if x])

        # 5. DUAL-MODE ROUTING TO DATABASE
        if not self.is_service_mode:
            # ==========================================
            # ROUTE A: PRODUCT UPLOAD
            # ==========================================
            listing_type = "Textbook"
            if 'product_type_group' in self.ids:
                for btn in self.ids.product_type_group.children:
                    if btn.state == "down":
                        listing_type = btn.text.replace('[b]', '').replace('[/b]', '')
                        break
            
            condition = "New"
            if 'condition_group' in self.ids:
                for btn in self.ids.condition_group.children:
                    if btn.state == "down":
                        condition = btn.text.replace('[b]', '').replace('[/b]', '')
                        break

            payload = {
                "initial": initial,
                "full_name": full_name,
                "title": title,
                "subject": subject_name,
                "product_type": listing_type, 
                "price": price,
                "review": description, 
                "condition_status": condition,
                "rate": 0, 
                "escrow": True, 
                "satisfied": False
            }
            # SEND TO PRODUCT TABLE
            res = request.add_product(payload)
            success_type = listing_type

        else:
            # ==========================================
            # ROUTE B: SERVICE UPLOAD
            # ==========================================
            category = "Tutoring"
            if 'service_type_group' in self.ids:
                for btn in self.ids.service_type_group.children:
                    if btn.state == "down":
                        category = btn.text.replace('[b]', '').replace('[/b]', '')
                        break
            
            rate_format = "hr"
            if 'rate_group' in self.ids:
                for btn in self.ids.rate_group.children:
                    if btn.state == "down":
                        # Extracts "hr", "week", or "month" 
                        rate_format = btn.text.replace('[b]', '').replace('[/b]', '').replace('/', '').strip()
                        break

            payload = {
                "initial": initial,
                "full_name": full_name,
                "title": title,
                "subject": subject_name,
                "category": category, 
                "rate": price,
                "rate_format": rate_format, 
                "description": description, 
                "schedule": "Flexible", 
                "escrow": True
            }
            # SEND TO SERVICE TABLE (NEW ENDPOINT!)
            res = request.add_service(payload) 
            success_type = category

        # 6. Check Response
        if res:
            NotificationModal().show("Success!", f"Your {success_type} is now live.", is_error=False)
            if 'title_input' in self.ids: self.ids.title_input.ids.internal_input.text = ""
            if 'subject_input' in self.ids: self.ids.subject_input.ids.internal_input.text = ""
            if 'desc_input' in self.ids: self.ids.desc_input.ids.internal_input.text = ""
            if 'price_input' in self.ids: self.ids.price_input.ids.internal_input.text = ""
        else:
            NotificationModal().show("Upload Failed", "Something went wrong.", is_error=True)

class Service(Widget):
    current_category = StringProperty('All')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.all_services = [] 
        Clock.schedule_once(self.get_services, 0.5)

    def set_category(self, cat):
        self.current_category = cat
        self.filter_services() 

    def get_services(self, dt=0):
        container = self.ids.dynamic_service
        container.clear_widgets()
        for _ in range(5):
            container.add_widget(ProductSkeleton())
        
        # FIX: Point to the correct thread function
        threading.Thread(target=self._thread_fetch_services, daemon=True).start()

    def _thread_fetch_services(self):
        global IS_OFFLINE_MODE
        
        if IS_OFFLINE_MODE:
            response = load_from_cache('marketplace_services')
            Clock.schedule_once(lambda dt: self._on_services_fetched(response), 0)
            return 
            
        try:
            # FIX: Fetch from the new Services API!
            response = request.get_services()
            if response:
                save_to_cache('marketplace_services', response)
                
        except Exception as e:
            print(f"🚨 Network Error: {e} | Falling back to Offline Mode...")
            Clock.schedule_once(show_offline_warning, 0)
            response = load_from_cache('marketplace_services')

        Clock.schedule_once(lambda dt: self._on_services_fetched(response), 0)

    def _on_services_fetched(self, response):
        if response:
            self.all_services = response 
        self.filter_services()

    def filter_services(self, *args):
        search_text = self.ids.search_bar.text.lower()
        container = self.ids.dynamic_service
        container.clear_widgets() 
        
        for data in self.all_services:
            # 1. Safe extraction (prevent 'NoneType' crashes)
            item_category = data.get('category') or ''
            
            # Apply Category Filter
            if self.current_category != 'All' and item_category != self.current_category:
                continue
                
            # Apply Search Filter
            title = str(data.get('title') or '').lower()
            desc = str(data.get('description') or '').lower()
            if search_text and (search_text not in title and search_text not in desc):
                continue
                
            try:
                # 2. Strict Type Formatting to guarantee Kivy doesn't break
                s_id = int(data.get('id') or 0)
                rate_val = float(data.get('rate') or 0.0)
                seller_rating = float(data.get('seller_rating') or 5.0)
                
                # 3. Draw Widget
                container.add_widget(DynamicService(
                    service_id=s_id,
                    fullname=data.get('full_name') or 'Unknown', 
                    initial=data.get('initial') or 'U', 
                    title=data.get('title') or 'No Title', 
                    subject=data.get('subject') or 'General',
                    rating=f"{seller_rating:.1f}", 
                    price=rate_val, 
                    rate_type=data.get('rate_format') or 'hr',
                    description=str(data.get('description') or 'No description'),
                    schedule=data.get('schedule') or 'Flexible'
                ))
            except Exception as e:
                # If a specific card fails, Kivy will print it here instead of crashing the whole screen!
                print(f"🚨 CRASH AVERTED: Skipping a corrupt service card because: {e}")

class Status(Widget):
    initial = StringProperty("N.A")
    full_name = StringProperty("N.A")
    email = StringProperty("N.A")
    rating = StringProperty("0")

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
    def load_user_stats(self, dt=0):
        name = Data.user.get('full_name')
        if name:
            profile = request.get_user_profile(name)
            if profile:
                # Update the string property to instantly refresh the UI
                self.rating = str(profile.get('rating', '0'))

class ProfileInterface(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class SettingsInterface(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def clear_local_cache(self):
        """Deletes the offline JSON file to free up space."""
        cache_file = "scholarbridge_offline_data.json"
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
                print("🗑️ Offline cache successfully cleared!")
                # Optional: Show a Kivy popup confirming it was cleared
            except Exception as e:
                print(f"Failed to clear cache: {e}")
        else:
            print("Cache is already empty.")

    def logout_user(self):
        """Clears local session state and returns to login."""
        # 1. Delete local login token/state
        if os.path.exists('local_state.json'):
            try:
                os.remove('local_state.json')
            except: pass
            
        # 2. Tell the app we are logged out
        app = App.get_running_app()
        app.root.logged = False
        
        # 3. Jump back to the StartInterface
        app.root.current = "start"
# -----------------------------------------------------------
# Animation Components
# -----------------------------------------------------------
class ProductSkeleton(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Start the pulsing animation the moment the skeleton is born
        Clock.schedule_once(self.animate_pulse, 0)
        
    def animate_pulse(self, dt):
        # Fades to 40% opacity, then back to 100%, and repeats infinitely
        anim = Animation(opacity=0.4, duration=0.6) + Animation(opacity=1.0, duration=0.6)
        anim.repeat = True
        anim.start(self)


# -----------------------------------------------------------
# Root
# -----------------------------------------------------------
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


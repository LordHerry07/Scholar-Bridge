from kivy.app import App
from kivy.core.window import Window
from kivy.properties import NumericProperty
from kivy.utils import platform
from core.main_interface import Interface

# -------------------------------
# APP: Window Configuration
# -------------------------------
Window.size = 360, 702

class ScholarBridge(App):
    unread_count = NumericProperty(0)
    
    def build(self):
        return Interface()

if platform == 'android':
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.WRITE_EXTERNAL_STORAGE])

if __name__ == "__main__":
    ScholarBridge().run()

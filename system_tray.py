"""
PowerStatus System Tray Integration

Provides system tray icon and context menu for PowerStatus monitoring.
"""

import pystray
from PIL import Image, ImageDraw
import threading
import time
from typing import Optional, Callable, Dict, Any


class PowerStatusTray:
    """System tray interface for PowerStatus monitoring"""
    
    def __init__(self, get_status_callback: Callable = None, control_state: Dict = None, stop_event = None):
        self.icon: Optional[pystray.Icon] = None
        self.running = False
        self.get_status_callback = get_status_callback
        self.control_state = control_state or {}
        self.current_power_state = "Unknown"
        self.app_running = True
        self.stop_event = stop_event
        
    def create_icon_image(self, power_state: str = "Unknown") -> Image.Image:
        """Create icon image based on power state"""
        # Use 32x32 for better visibility
        size = (32, 32)
        # Start with solid background for maximum visibility
        if "AC" in power_state:
            # Solid bright green for AC Power
            image = Image.new('RGBA', size, (0, 255, 0, 255))
        elif "Battery" in power_state:
            # Solid bright red for Battery  
            image = Image.new('RGBA', size, (255, 0, 0, 255))
        else:
            # Solid bright blue for Unknown
            image = Image.new('RGBA', size, (0, 0, 255, 255))
        
        # Add a thick white border for maximum contrast
        draw = ImageDraw.Draw(image)
        draw.rectangle([0, 0, size[0]-1, size[1]-1], outline=(255, 255, 255, 255), width=3)
        
        return image
    
    def get_tooltip_text(self) -> str:
        """Generate tooltip text with current status"""
        if self.get_status_callback:
            try:
                status_info = self.get_status_callback()
                if isinstance(status_info, dict):
                    power = status_info.get('power_state', 'Unknown')
                    runtime = status_info.get('total_runtime', 'Unknown')
                    return f"PowerStatus Monitor\nPower: {power}\nRuntime: {runtime}"
                else:
                    return f"PowerStatus Monitor\nPower: {status_info}"
            except Exception:
                pass
        return f"PowerStatus Monitor\nPower: {self.current_power_state}"
    
    def on_show_status(self, icon, item):
        """Show current status"""
        if self.control_state:
            self.control_state['say_current'] = True
    
    def on_toggle_repeat(self, icon, item):
        """Toggle repeat mode"""
        if self.control_state:
            self.control_state['repeat'] = not self.control_state.get('repeat', False)
            # Trigger repeat enable announcement if turning ON
            if self.control_state['repeat']:
                self.control_state['announce_on_repeat_enable'] = True
    
    def on_toggle_timer(self, icon, item):
        """Toggle timer display"""
        if self.control_state:
            self.control_state['show_timer'] = not self.control_state.get('show_timer', False)
    
    def on_toggle_system_stats(self, icon, item):
        """Toggle system stats display"""
        if self.control_state:
            self.control_state['show_system_stats'] = not self.control_state.get('show_system_stats', True)
    
    def on_polling_slower(self, icon, item):
        """Make polling slower"""
        if self.control_state:
            self.control_state['interval'] = min(60, self.control_state.get('interval', 2) + 0.5)
    
    def on_polling_faster(self, icon, item):
        """Make polling faster"""
        if self.control_state:
            self.control_state['interval'] = max(0.5, self.control_state.get('interval', 2) - 0.5)
    
    def on_polling_reset(self, icon, item):
        """Reset polling to default"""
        if self.control_state:
            self.control_state['interval'] = 2.0
    
    def on_exit(self, icon, item):
        """Exit the application"""
        print("Exiting PowerStatus from system tray...")
        self.app_running = False
        if self.stop_event:
            self.stop_event.set()
        self.stop()
    
    def create_menu(self) -> pystray.Menu:
        """Create a simplified context menu for testing"""
        return pystray.Menu(
            pystray.MenuItem("PowerStatus Monitor", None, enabled=False),  # Title
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Current Status", self.on_show_status),
            pystray.MenuItem("Toggle Repeat", self.on_toggle_repeat),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self.on_exit)
        )
    
    def update_power_state(self, power_state: str):
        """Update the power state and refresh icon"""
        if power_state != self.current_power_state:
            self.current_power_state = power_state
            if self.icon:
                # Update icon image
                new_image = self.create_icon_image(power_state)
                self.icon.icon = new_image
                # Update tooltip
                self.icon.title = self.get_tooltip_text()
                # Update menu to reflect current states
                self.update_menu()
    
    def update_menu(self):
        """Update the context menu to reflect current states"""
        if self.icon:
            self.icon.menu = self.create_menu()
    
    def start(self):
        """Start the system tray icon"""
        if self.running:
            print("System tray already running")
            return
        
        print("Creating system tray icon...")
        
        # Create initial icon image
        image = self.create_icon_image(self.current_power_state)
        print(f"Icon image created for state: {self.current_power_state}")
        
        # Create the icon
        self.icon = pystray.Icon(
            "PowerStatus",
            image,
            title=self.get_tooltip_text(),
            menu=self.create_menu()
        )
        
        self.running = True
        print("System tray icon created, starting...")
        
        # Run the icon (this blocks)
        try:
            self.icon.run()
            print("System tray icon stopped")
        except Exception as e:
            print(f"System tray error: {e}")
        finally:
            self.running = False
    
    def start_threaded(self):
        """Start the system tray icon in a separate thread"""
        if self.running:
            return None
        
        def run_tray():
            try:
                print("Tray thread starting...")
                self.start()
                print("Tray thread finished")
            except Exception as e:
                print(f"System tray thread error: {e}")
                import traceback
                traceback.print_exc()
        
        # Use daemon=False to ensure tray persists
        tray_thread = threading.Thread(target=run_tray, daemon=False, name="SystemTray")
        tray_thread.start()
        
        # Give it time to initialize
        time.sleep(2.0)
        print(f"Tray thread started, alive: {tray_thread.is_alive()}")
        
        return tray_thread
    
    def stop(self):
        """Stop the system tray icon"""
        if self.icon:
            self.icon.stop()
        self.running = False
    
    def is_running(self) -> bool:
        """Check if tray is running"""
        return self.running


# Test function for standalone testing
def test_system_tray():
    """Test the system tray functionality"""
    def mock_status_callback():
        return {
            'power_state': 'AC Power',
            'total_runtime': '01:23:45'
        }
    
    print("Testing PowerStatus System Tray...")
    print("Right-click the tray icon to see the menu.")
    print("Click 'Exit' to quit the test.")
    
    tray = PowerStatusTray(get_status_callback=mock_status_callback)
    
    # Simulate power state changes
    def simulate_changes():
        time.sleep(3)
        print("Simulating power state change to Battery...")
        tray.update_power_state("Battery")
        
        time.sleep(3)
        print("Simulating power state change to AC Power...")
        tray.update_power_state("AC Power")
    
    # Start simulation in background
    sim_thread = threading.Thread(target=simulate_changes, daemon=True)
    sim_thread.start()
    
    # Start tray (this will block until exit)
    tray.start()
    
    print("System tray test completed.")


if __name__ == "__main__":
    test_system_tray()
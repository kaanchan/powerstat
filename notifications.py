"""
PowerStatus Notification System

Multi-channel notification manager for power state changes and events.
"""

import json
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

try:
    from plyer import notification as plyer_notification
    PLYER_AVAILABLE = True
except ImportError:
    PLYER_AVAILABLE = False

try:
    from win10toast import ToastNotifier
    WIN10TOAST_AVAILABLE = True
except ImportError:
    WIN10TOAST_AVAILABLE = False


class NotificationChannel(ABC):
    """Abstract base class for notification channels"""
    
    def __init__(self, name: str, config: Dict):
        self.name = name
        self.config = config
        self.enabled = config.get('enabled', False)
        
    @abstractmethod
    def send(self, title: str, message: str, **kwargs) -> bool:
        """Send notification. Returns True if successful."""
        pass
        
    def is_enabled(self) -> bool:
        """Check if this channel is enabled"""
        return self.enabled


class ToastNotificationChannel(NotificationChannel):
    """Windows Toast Notification Channel"""
    
    def __init__(self, config: Dict):
        super().__init__("toast", config)
        self.use_plyer = PLYER_AVAILABLE
        self.use_win10toast = WIN10TOAST_AVAILABLE and not self.use_plyer
        
        if self.use_win10toast:
            self.toaster = ToastNotifier()
        
    def send(self, title: str, message: str, **kwargs) -> bool:
        """Send Windows toast notification"""
        if not self.enabled:
            return False
            
        duration = self.config.get('duration', 10)
        
        # Try plyer first (more reliable)
        if self.use_plyer:
            try:
                plyer_notification.notify(
                    title=title,
                    message=message,
                    timeout=duration,
                    app_name="PowerStatus"
                )
                return True
            except Exception as e:
                print(f"Plyer notification failed: {e}")
                # Fall back to win10toast if plyer fails
                if WIN10TOAST_AVAILABLE:
                    self.use_plyer = False
                    self.use_win10toast = True
                    self.toaster = ToastNotifier()
        
        # Fallback to win10toast
        if self.use_win10toast:
            try:
                icon_path = kwargs.get('icon_path', None)
                
                self.toaster.show_toast(
                    title=title,
                    msg=message,
                    duration=duration,
                    icon_path=icon_path,
                    threaded=True
                )
                return True
            except Exception as e:
                print(f"Win10toast notification failed: {e}")
                return False
        
        print("No notification libraries available")
        return False


class NotificationManager:
    """Central notification management system"""
    
    def __init__(self, config_path: str = "notification_config.json"):
        self.config_path = config_path
        self.channels: Dict[str, NotificationChannel] = {}
        self.load_config()
        self.initialize_channels()
        
    def load_config(self):
        """Load notification configuration from file"""
        default_config = {
            "notifications": {
                "enabled": True,
                "channels": {
                    "toast": {
                        "enabled": True,
                        "duration": 10
                    }
                },
                "events": {
                    "power_change": True,
                    "repeat_mode_toggle": False,
                    "service_start": True,
                    "service_stop": True
                }
            }
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
                self.config = default_config
        else:
            self.config = default_config
            self.save_config()
            
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
            
    def initialize_channels(self):
        """Initialize notification channels based on configuration"""
        channels_config = self.config.get('notifications', {}).get('channels', {})
        
        # Initialize Toast notifications
        if 'toast' in channels_config:
            self.channels['toast'] = ToastNotificationChannel(channels_config['toast'])
            
    def send_notification(self, event_type: str, title: str, message: str, **kwargs) -> List[str]:
        """
        Send notification through enabled channels for specified event type
        Returns list of channels that successfully sent the notification
        """
        if not self.config.get('notifications', {}).get('enabled', True):
            return []
            
        # Check if this event type should trigger notifications
        events_config = self.config.get('notifications', {}).get('events', {})
        if not events_config.get(event_type, False):
            return []
            
        successful_channels = []
        
        for channel_name, channel in self.channels.items():
            if channel.is_enabled():
                try:
                    if channel.send(title, message, **kwargs):
                        successful_channels.append(channel_name)
                except Exception as e:
                    print(f"Error sending notification via {channel_name}: {e}")
                    
        return successful_channels
        
    def test_channel(self, channel_name: str) -> bool:
        """Test a specific notification channel"""
        if channel_name not in self.channels:
            print(f"Channel {channel_name} not found")
            return False
            
        channel = self.channels[channel_name]
        if not channel.is_enabled():
            print(f"Channel {channel_name} is disabled")
            return False
            
        return channel.send(
            "PowerStatus Test", 
            f"Test notification from {channel_name} channel",
            test=True
        )
        
    def get_channel_status(self) -> Dict[str, Dict]:
        """Get status of all notification channels"""
        status = {}
        for name, channel in self.channels.items():
            status[name] = {
                'enabled': channel.is_enabled(),
                'config': channel.config
            }
        return status


# Convenience functions for power monitoring integration
def create_notification_manager() -> NotificationManager:
    """Create and return a notification manager instance"""
    return NotificationManager()


def send_power_change_notification(manager: NotificationManager, power_state: str):
    """Send notification for power state change"""
    title = "PowerStatus Monitor"
    message = f"Power state changed to: {power_state}"
    
    # Determine icon based on power state
    icon_kwargs = {}
    if "AC" in power_state:
        icon_kwargs['icon_path'] = None  # Use default for now
    elif "Battery" in power_state:
        icon_kwargs['icon_path'] = None  # Use default for now
        
    return manager.send_notification('power_change', title, message, **icon_kwargs)


def send_service_notification(manager: NotificationManager, event: str, message: str):
    """Send notification for service events"""
    title = "PowerStatus Service"
    return manager.send_notification(event, title, message)
import sys
import threading
import time
import psutil
import argparse
import os
import pyttsx3
from datetime import datetime
try:
    import msvcrt
except ImportError:
    msvcrt = None

# Import notification system
try:
    from notifications import create_notification_manager, send_power_change_notification, send_service_notification
    NOTIFICATIONS_AVAILABLE = True
except ImportError:
    NOTIFICATIONS_AVAILABLE = False
    print("Notifications not available. Install win10toast for notification support.")

# Import system tray
try:
    from system_tray import PowerStatusTray
    SYSTEM_TRAY_AVAILABLE = True
except ImportError:
    SYSTEM_TRAY_AVAILABLE = False
    print("System tray not available. Install pystray for system tray support.")

def format_timestamp() -> str:
    """Format current time as: hh:mm:ss - dd-mm-yyyy"""
    return datetime.now().strftime("%H:%M:%S - %d-%m-%Y")


class PowerMonitor:
    """Power monitoring class that can be used by both console app and service"""
    
    def __init__(self, control_state=None, notification_manager=None, stop_event=None, 
                 voice_enabled=True, console_output=True, system_tray=None):
        self.control_state = control_state or {}
        self.notification_manager = notification_manager
        self.stop_event = stop_event or threading.Event()
        self.voice_enabled = voice_enabled
        self.console_output = console_output
        self.system_tray = system_tray
        self.voice_ready = False
        self.start_time = time.time()
        self.current_state_start_time = self.start_time
        self.last_status = None
        self.last_repeat_time = 0
        self.running = False
        
    def initialize(self):
        """Initialize the power monitor"""
        # Initialize voice if enabled
        if self.voice_enabled:
            self.voice_ready = initialize_voice_engine()
            if not self.voice_ready and self.console_output:
                print("Warning: Voice engine not available. Continuing with console output only.")
        
        # Get initial power status
        self.last_status = get_power_status()
        if self.last_status:
            if self.console_output:
                print(f"Current power state: {self.last_status}")
            if self.voice_ready:
                announce(f"Power monitoring started. Current state: {self.last_status}", self.voice_ready)
            # Send startup notification
            if self.notification_manager:
                send_service_notification(self.notification_manager, 'service_start', 
                                        f"PowerStatus monitoring started. Current state: {self.last_status}")
        else:
            if self.console_output:
                print("No battery information available.")
            return False
        return True
        
    def get_power_status(self):
        """Get current power status - wrapper for external access"""
        return get_power_status()
        
    def get_total_runtime(self):
        """Get total runtime as formatted string"""
        total_seconds = int(time.time() - self.start_time)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
    def run(self):
        """Main monitoring loop"""
        if not self.initialize():
            return
            
        if self.console_output:
            help_text = "ESC/Q: Quit | H: Help | < or ,: Slower | > or .: Faster | R: Toggle Repeat | C: Say Current Status | S: Toggle System Stats | T: Toggle Timer"
            print(f"\n{help_text}")
            print("Starting power monitoring...")
        
        self.running = True
        
        while not self.stop_event.is_set() and self.running:
            current_time = time.time()
            status = get_power_status()
            
            # Handle power state changes
            if status and status != self.last_status:
                # Print timestamped console message
                timestamp = format_timestamp()
                if self.console_output:
                    print(f"\nPower state changed: {status} @ {timestamp}")
                
                if self.voice_ready:
                    announce(f"Power state changed: {status}", self.voice_ready)
                # Send notification for power state change
                if self.notification_manager:
                    send_power_change_notification(self.notification_manager, status)
                # Update system tray icon
                if self.system_tray:
                    self.system_tray.update_power_state(status)
                self.last_status = status
                self.current_state_start_time = current_time  # Reset current state timer
            
            # Handle manual current status request
            if self.control_state.get('say_current', False):
                self.control_state['say_current'] = False
                if status and self.voice_ready:
                    announce(f"Current power state: {status}", self.voice_ready)
            
            # Handle repeat mode announcement
            if self.control_state.get('announce_on_repeat_enable', False):
                self.control_state['announce_on_repeat_enable'] = False
                repeat_modes = ['disabled', 'all power states', 'AC only', 'battery only']
                repeat_mode_text = repeat_modes[self.control_state.get('repeat', 0)]
                if self.voice_ready:
                    announce(f"Repeat mode {repeat_mode_text}", self.voice_ready)
                    if self.control_state.get('repeat', 0) > 0:
                        self.last_repeat_time = current_time  # Reset repeat timer
            
            # Handle repeat mode announcements
            repeat_mode = self.control_state.get('repeat', 0)
            if repeat_mode > 0 and status and self.voice_ready:
                should_repeat = False
                if repeat_mode == 1:  # AC/BAT - always repeat
                    should_repeat = True
                elif repeat_mode == 2 and status == 'AC Power':  # AC only
                    should_repeat = True
                elif repeat_mode == 3 and status == 'Battery':  # BAT only
                    should_repeat = True
                
                if should_repeat:
                    repeat_interval = self.control_state.get('repeat_interval', 5)
                    if (current_time - self.last_repeat_time) >= repeat_interval:
                        announce(f"Current power state: {status}", self.voice_ready)
                        self.last_repeat_time = current_time
            
            # Check if tray requested exit
            if self.system_tray and not self.system_tray.app_running:
                self.stop_event.set()
                break
                
            if self.console_output:
                print_resource_usage(self.control_state, self.start_time, self.current_state_start_time)
            
            sleep_interval = self.control_state.get('interval', 2.0)
            time.sleep(sleep_interval)
        
        self.running = False
        
    def stop(self):
        """Stop the monitor"""
        self.running = False
        self.stop_event.set()

def control_listener(stop_event, control_state):
    help_text = "ESC/Q: Quit | H: Help | < or ,: Slower | > or .: Faster | R: Toggle Repeat | C: Say Current Status | S: Toggle System Stats | T: Toggle Timer"
    if msvcrt:
        while not stop_event.is_set():
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if not key:
                    continue
                k = key.decode(errors='ignore').lower()
                if k == '\x1b' or k == 'q':  # ESC or Q
                    stop_event.set()
                    print(f"\n{'ESC' if k == '\x1b' else 'Q'} pressed. Exiting...")
                    break
                elif k == 'h':
                    print(f"\n{help_text}")
                elif k in ['<', ',']:
                    control_state['interval'] = min(60, control_state['interval'] + 0.5)
                    print(f"\nPolling interval: {control_state['interval']}s")
                elif k in ['>', '.']:
                    control_state['interval'] = max(0.5, control_state['interval'] - 0.5)
                    print(f"\nPolling interval: {control_state['interval']}s")
                elif k == 'r':
                    # Cycle through repeat modes: 0 (OFF) -> 1 (AC/BAT) -> 2 (AC only) -> 3 (BAT only) -> 0
                    repeat_modes = ['OFF', 'AC/BAT', 'AC only', 'BAT only']
                    control_state['repeat'] = (control_state['repeat'] + 1) % 4
                    repeat_mode_name = repeat_modes[control_state['repeat']]
                    print(f"\nRepeat mode: {repeat_mode_name}")
                    if control_state['repeat'] > 0:
                        control_state['announce_on_repeat_enable'] = True
                elif k == 'c':
                    control_state['say_current'] = True
                elif k == 's':
                    control_state['show_system_stats'] = not control_state.get('show_system_stats', True)
                    print(f"\nSystem stats: {'ON' if control_state['show_system_stats'] else 'OFF'}")
                elif k == 't':
                    control_state['show_timer'] = not control_state.get('show_timer', False)
                    print(f"\nTimer display: {'ON' if control_state['show_timer'] else 'OFF'}")

def announce(text, use_voice=True):
    print(f"\n{text}")
    if use_voice:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()

def get_power_status():
    battery = psutil.sensors_battery()
    if battery is None:
        return None
    return 'AC Power' if battery.power_plugged else 'Battery'

import os

def print_resource_usage(control_state=None, start_time=None, current_state_start_time=None):
    def format_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    # Get power status
    power_status = get_power_status()
    power_text = f"Power: {power_status}" if power_status else "Power: Unknown"
    
    # Build status line components in new order: Power → Current/Total → Polling → Mem → CPU → Repeat → Help
    status_parts = [power_text]
    
    # Add Current/Total runtime
    if start_time and current_state_start_time:
        current_time = time.time()
        current_runtime = current_time - current_state_start_time
        total_runtime = current_time - start_time
        status_parts.append(f"Current/Total: {format_time(current_runtime)}/{format_time(total_runtime)}")
    
    # Add polling interval
    if control_state:
        polling_interval = control_state.get('interval', 2.0)
        status_parts.append(f"Polling: {polling_interval}s")
        
        # Add system stats if enabled
        if control_state.get('show_system_stats', True):
            pid = os.getpid()
            p = psutil.Process(pid)
            cpu = p.cpu_percent(interval=None)
            mem = p.memory_info().rss / (1024 * 1024)  # MB
            status_parts.extend([f"Mem: {mem:.1f} MB", f"CPU: {cpu:.1f}%"])
        
        # Add repeat mode
        repeat_modes = ['OFF', 'AC/BAT', 'AC only', 'BAT only']
        repeat_mode = repeat_modes[control_state.get('repeat', 0)]
        status_parts.append(f"Repeat: {repeat_mode}")
    
    # Add help prompt
    status_parts.append("<H> for menu")
    
    print(" | ".join(status_parts), end='\r')

def initialize_voice_engine():
    print("Initializing voice engine...")
    try:
        engine = pyttsx3.init()
        engine.say("Voice engine ready")
        engine.runAndWait()
        print("Voice engine initialized successfully.")
        return True
    except Exception as e:
        print(f"Voice engine initialization failed: {e}")
        return False

def main():
    stop_event = threading.Event()
    parser = argparse.ArgumentParser(description="PowerStatus App")
    parser.add_argument('--interval', type=float, default=2, help='Polling interval in seconds (default: 2)')
    parser.add_argument('--no-notifications', action='store_true', help='Disable notifications')
    parser.add_argument('--tray', action='store_true', help='Run with system tray icon')
    parser.add_argument('--no-console', action='store_true', help='Hide console window (use with --tray)')
    parser.add_argument('--service', choices=['install', 'uninstall', 'start', 'stop', 'status', 'run'], 
                        help='Service management commands')
    parser.add_argument('--no-tray', action='store_true', help='Disable system tray (use with --service)')
    args = parser.parse_args()
    
    # Handle service commands first
    if args.service:
        try:
            from service import run_service_command
            enable_tray = not args.no_tray  # Tray enabled by default unless --no-tray specified
            success = run_service_command(args.service, enable_tray)
            sys.exit(0 if success else 1)
        except ImportError:
            print("Service functionality not available. Install pywin32 for Windows service support.")
            sys.exit(1)
    control_state = {'interval': args.interval, 'repeat': 0, 'repeat_duration': 0, 'say_current': False, 'announce_on_repeat_enable': False, 'repeat_interval': 5, 'show_timer': False, 'show_system_stats': True}
    
    # Initialize notification manager
    notification_manager = None
    if NOTIFICATIONS_AVAILABLE and not args.no_notifications:
        try:
            notification_manager = create_notification_manager()
            print("Notification system initialized.")
        except Exception as e:
            print(f"Failed to initialize notifications: {e}")
    
    # Get initial power state before system tray initialization
    initial_power_state = get_power_status()
    
    # Initialize system tray
    system_tray = None
    tray_thread = None
    if args.tray and SYSTEM_TRAY_AVAILABLE:
        try:
            def get_status_info():
                current_status = get_power_status()
                return {
                    'power_state': current_status or 'Unknown',
                    'total_runtime': 'Running...'  # We'll improve this later
                }
            
            system_tray = PowerStatusTray(
                get_status_callback=get_status_info,
                control_state=control_state,
                stop_event=stop_event
            )
            
            # Set the correct initial power state before starting
            if initial_power_state:
                system_tray.current_power_state = initial_power_state
            
            print("Starting system tray...")
            tray_thread = system_tray.start_threaded()
            print("System tray initialized. Look for icon in system tray area.")
        except Exception as e:
            print(f"Failed to initialize system tray: {e}")
            system_tray = None
    elif args.tray:
        print("System tray requested but not available. Install pystray for system tray support.")
    
    # Only start keyboard listener if not in tray-only mode
    if not args.no_console:
        listener_thread = threading.Thread(target=control_listener, args=(stop_event, control_state), daemon=True)
        listener_thread.start()

    print("Initializing psutil.cpu...")
    psutil.cpu_percent(interval=0)
    print("CPU monitoring initialized.")
    
    # Create and run power monitor
    monitor = PowerMonitor(
        control_state=control_state,
        notification_manager=notification_manager,
        stop_event=stop_event,
        voice_enabled=True,
        console_output=not args.no_console,
        system_tray=system_tray
    )
    
    # Run the monitor
    monitor.run()
    
    # Cleanup system tray
    if system_tray:
        system_tray.stop()
    
    # Wait for tray thread to finish if running
    if tray_thread and tray_thread.is_alive():
        print("Waiting for system tray to close...")
        tray_thread.join(timeout=2)

if __name__ == "__main__":
    main()

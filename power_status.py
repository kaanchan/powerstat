import sys
import threading
import time
import psutil
import argparse
import os
import pyttsx3
try:
    import msvcrt
except ImportError:
    msvcrt = None

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
                    control_state['repeat'] = not control_state['repeat']
                    print(f"\nRepeat mode: {'ON' if control_state['repeat'] else 'OFF'}")
                    if control_state['repeat']:
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
        repeat_mode = "ON" if control_state.get('repeat', False) else "OFF"
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
    args = parser.parse_args()
    control_state = {'interval': args.interval, 'repeat': False, 'repeat_duration': 0, 'say_current': False, 'announce_on_repeat_enable': False, 'repeat_interval': 5, 'show_timer': False, 'show_system_stats': True}
    listener_thread = threading.Thread(target=control_listener, args=(stop_event, control_state), daemon=True)
    listener_thread.start()

    print("Initializing psutil.cpu...")
    psutil.cpu_percent(interval=0)
    print("CPU monitoring initialized.")
    
    voice_ready = initialize_voice_engine()
    if not voice_ready:
        print("Warning: Voice engine not available. Continuing with console output only.")
    
    print("Starting power monitoring...")
    start_time = time.time()  # Track application start time
    current_state_start_time = start_time  # Track when current power state began
    last_status = get_power_status()
    if last_status:
        print(f"Current power state: {last_status}")
        if voice_ready:
            announce(f"Power monitoring started. Current state: {last_status}", voice_ready)
    else:
        print("No battery information available.")
        return
    help_text = "ESC/Q: Quit | H: Help | < or ,: Slower | > or .: Faster | R: Toggle Repeat | C: Say Current Status | S: Toggle System Stats | T: Toggle Timer"
    print(f"\n{help_text}")
    
    # Initialize repeat timing
    last_repeat_time = 0
    
    while not stop_event.is_set():
        current_time = time.time()
        status = get_power_status()
        
        # Handle power state changes
        if status and status != last_status:
            if voice_ready:
                announce(f"Power state changed: {status}", voice_ready)
            last_status = status
            current_state_start_time = current_time  # Reset current state timer
        
        # Handle manual current status request
        if control_state.get('say_current', False):
            control_state['say_current'] = False
            if status and voice_ready:
                announce(f"Current power state: {status}", voice_ready)
        
        # Handle repeat mode enable announcement
        if control_state.get('announce_on_repeat_enable', False):
            control_state['announce_on_repeat_enable'] = False
            if status and voice_ready:
                announce(f"Repeat mode enabled. Current power state: {status}", voice_ready)
                last_repeat_time = current_time  # Reset repeat timer
        
        # Handle repeat mode announcements
        if control_state['repeat'] and status and voice_ready:
            if (current_time - last_repeat_time) >= control_state['repeat_interval']:
                announce(f"Current power state: {status}", voice_ready)
                last_repeat_time = current_time
        
        print_resource_usage(control_state, start_time, current_state_start_time)
        time.sleep(control_state['interval'])

if __name__ == "__main__":
    main()

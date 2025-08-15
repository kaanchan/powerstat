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
    help_text = "ESC: Quit | H: Help | < or ,: Slower | > or .: Faster | R: Toggle Repeat | S: Say Current Status"
    if msvcrt:
        while not stop_event.is_set():
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if not key:
                    continue
                k = key.decode(errors='ignore').lower()
                if k == '\x1b':  # ESC
                    stop_event.set()
                    print("\nESC pressed. Exiting...")
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
                elif k == 's':
                    control_state['say_current'] = True

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

def print_resource_usage(control_state=None):
    pid = os.getpid()
    p = psutil.Process(pid)
    cpu = p.cpu_percent(interval=None)
    mem = p.memory_info().rss / (1024 * 1024)  # MB
    repeat_status = ""
    if control_state:
        repeat_mode = "ON" if control_state.get('repeat', False) else "OFF"
        repeat_status = f" | Repeat: {repeat_mode}"
    print(f"Script CPU: {cpu:.1f}% | Memory: {mem:.1f} MB{repeat_status}", end='\r')

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
    control_state = {'interval': args.interval, 'repeat': False, 'repeat_duration': 0, 'say_current': False, 'announce_on_repeat_enable': False, 'repeat_interval': 5}
    listener_thread = threading.Thread(target=control_listener, args=(stop_event, control_state), daemon=True)
    listener_thread.start()

    print("Initializing psutil.cpu...")
    psutil.cpu_percent(interval=0)
    print("CPU monitoring initialized.")
    
    voice_ready = initialize_voice_engine()
    if not voice_ready:
        print("Warning: Voice engine not available. Continuing with console output only.")
    
    print("Starting power monitoring...")
    last_status = get_power_status()
    if last_status:
        print(f"Current power state: {last_status}")
        if voice_ready:
            announce(f"Power monitoring started. Current state: {last_status}", voice_ready)
    else:
        print("No battery information available.")
        return
    help_text = "ESC: Quit | H: Help | < or ,: Slower | > or .: Faster | R: Toggle Repeat | S: Say Current Status"
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
        
        print_resource_usage(control_state)
        time.sleep(control_state['interval'])

if __name__ == "__main__":
    main()

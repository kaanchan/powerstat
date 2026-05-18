"""
PowerStatus Windows Service Implementation

Provides Windows service functionality for PowerStatus monitoring.
"""

import sys
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any

try:
    import win32serviceutil
    import win32service
    import win32event
    import win32api
    import servicemanager
    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False
    print("Warning: pywin32 not available. Service functionality disabled.")

from power_status import PowerMonitor
from system_tray import PowerStatusTray
from notifications import NotificationManager


class PowerStatusService(win32serviceutil.ServiceFramework):
    """Windows service for PowerStatus monitoring"""
    
    _svc_name_ = "PowerStatusService"
    _svc_display_name_ = "PowerStatus Monitor Service"
    _svc_description_ = "Monitors power state changes and provides notifications"
    _svc_deps_ = []  # No dependencies
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        # Create event to signal service stop
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_alive = True
        self.monitor: Optional[PowerMonitor] = None
        self.tray: Optional[PowerStatusTray] = None
        self.tray_thread: Optional[threading.Thread] = None
        self.enable_tray = True  # Default to tray enabled
        
        # Setup logging
        self.setup_logging()
        
    def setup_logging(self):
        """Setup service logging"""
        log_file = Path(__file__).parent / "service.log"
        logging.basicConfig(
            filename=str(log_file),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
    def SvcStop(self):
        """Stop the service"""
        self.logger.info("Service stop requested")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        
        # Signal main thread to stop
        win32event.SetEvent(self.hWaitStop)
        self.is_alive = False
        
        # Stop monitor and tray
        if self.monitor:
            self.monitor.stop()
            
        if self.tray:
            self.tray.stop()
            
        self.logger.info("Service stopped")
        
    def SvcDoRun(self):
        """Run the service"""
        try:
            self.logger.info("PowerStatus Service starting...")
            
            # Log to Windows Event Log
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            
            # Start the main service logic
            self.main()
            
            self.logger.info("PowerStatus Service stopped")
            
        except Exception as e:
            self.logger.error(f"Service error: {e}", exc_info=True)
            servicemanager.LogErrorMsg(f"Service error: {e}")
            
    def main(self):
        """Main service logic"""
        self.logger.info("Initializing PowerStatus monitoring...")
        
        # Create shared state for communication
        control_state = {
            'repeat': False,
            'interval': 2.0,
            'show_timer': False,
            'show_system_stats': True
        }
        
        # Initialize notification manager
        notification_manager = NotificationManager()
        
        # Send service start notification
        notification_manager.send_notification(
            "service_start",
            "PowerStatus Service Started",
            "PowerStatus monitoring service is now running"
        )
        
        # Initialize power monitor
        self.monitor = PowerMonitor(
            control_state=control_state,
            notification_manager=notification_manager
        )
        
        # Start system tray if enabled
        if self.enable_tray:
            self.start_system_tray(control_state)
            
        # Start monitoring in separate thread
        monitor_thread = threading.Thread(
            target=self.run_monitor,
            name="PowerMonitor",
            daemon=True
        )
        monitor_thread.start()
        
        self.logger.info("PowerStatus Service running. Waiting for stop signal...")
        
        # Wait for stop signal
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
        
        self.logger.info("Stop signal received, shutting down...")
        
    def start_system_tray(self, control_state: Dict[str, Any]):
        """Start system tray in separate thread"""
        try:
            self.logger.info("Starting system tray...")
            
            # Create stop event for tray
            stop_event = threading.Event()
            
            # Create tray with service-specific callbacks
            self.tray = PowerStatusTray(
                get_status_callback=self.get_service_status,
                control_state=control_state,
                stop_event=stop_event
            )
            
            # Start tray in separate thread
            self.tray_thread = self.tray.start_threaded()
            
            self.logger.info("System tray started")
            
        except Exception as e:
            self.logger.error(f"Failed to start system tray: {e}", exc_info=True)
            
    def get_service_status(self) -> Dict[str, str]:
        """Get current service status for tray display"""
        try:
            if self.monitor:
                power_state = self.monitor.get_power_status()
                runtime = self.monitor.get_total_runtime()
                return {
                    'power_state': power_state,
                    'total_runtime': runtime,
                    'service_status': 'Running'
                }
        except Exception as e:
            self.logger.error(f"Error getting service status: {e}")
            
        return {
            'power_state': 'Unknown',
            'total_runtime': 'Unknown',
            'service_status': 'Error'
        }
        
    def run_monitor(self):
        """Run the power monitor"""
        try:
            if self.monitor:
                self.monitor.run()
        except Exception as e:
            self.logger.error(f"Monitor error: {e}", exc_info=True)


class ServiceManager:
    """Manages Windows service operations"""
    
    @staticmethod
    def is_service_installed() -> bool:
        """Check if service is installed"""
        if not PYWIN32_AVAILABLE:
            return False
            
        try:
            import win32service
            scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
            try:
                service = win32service.OpenService(
                    scm, 
                    PowerStatusService._svc_name_, 
                    win32service.SERVICE_QUERY_STATUS
                )
                win32service.CloseServiceHandle(service)
                return True
            except win32service.error:
                return False
            finally:
                win32service.CloseServiceHandle(scm)
        except Exception:
            return False
            
    @staticmethod
    def is_service_running() -> bool:
        """Check if service is running"""
        if not PYWIN32_AVAILABLE or not ServiceManager.is_service_installed():
            return False
            
        try:
            import win32service
            scm = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ENUMERATE_SERVICE)
            try:
                service = win32service.OpenService(
                    scm, 
                    PowerStatusService._svc_name_, 
                    win32service.SERVICE_QUERY_STATUS
                )
                try:
                    status = win32service.QueryServiceStatus(service)
                    return status[1] == win32service.SERVICE_RUNNING
                finally:
                    win32service.CloseServiceHandle(service)
            finally:
                win32service.CloseServiceHandle(scm)
        except Exception:
            return False
            
    @staticmethod
    def install_service() -> bool:
        """Install the service"""
        if not PYWIN32_AVAILABLE:
            print("Error: pywin32 not available. Cannot install service.")
            return False
            
        try:
            # Get current script path
            script_path = Path(__file__).absolute()
            
            # Install service
            win32serviceutil.InstallService(
                PowerStatusService._svc_reg_class_,
                PowerStatusService._svc_name_,
                PowerStatusService._svc_display_name_,
                description=PowerStatusService._svc_description_,
                startType=win32service.SERVICE_AUTO_START,
                exeName=str(script_path)
            )
            
            print(f"Service '{PowerStatusService._svc_display_name_}' installed successfully")
            return True
            
        except Exception as e:
            print(f"Failed to install service: {e}")
            return False
            
    @staticmethod
    def uninstall_service() -> bool:
        """Uninstall the service"""
        if not PYWIN32_AVAILABLE:
            print("Error: pywin32 not available. Cannot uninstall service.")
            return False
            
        try:
            # Stop service if running
            if ServiceManager.is_service_running():
                ServiceManager.stop_service()
                
            # Uninstall service
            win32serviceutil.RemoveService(PowerStatusService._svc_name_)
            print(f"Service '{PowerStatusService._svc_display_name_}' uninstalled successfully")
            return True
            
        except Exception as e:
            print(f"Failed to uninstall service: {e}")
            return False
            
    @staticmethod
    def start_service() -> bool:
        """Start the service"""
        if not PYWIN32_AVAILABLE:
            print("Error: pywin32 not available. Cannot start service.")
            return False
            
        try:
            win32serviceutil.StartService(PowerStatusService._svc_name_)
            print(f"Service '{PowerStatusService._svc_display_name_}' started successfully")
            return True
            
        except Exception as e:
            print(f"Failed to start service: {e}")
            return False
            
    @staticmethod
    def stop_service() -> bool:
        """Stop the service"""
        if not PYWIN32_AVAILABLE:
            print("Error: pywin32 not available. Cannot stop service.")
            return False
            
        try:
            win32serviceutil.StopService(PowerStatusService._svc_name_)
            print(f"Service '{PowerStatusService._svc_display_name_}' stopped successfully")
            return True
            
        except Exception as e:
            print(f"Failed to stop service: {e}")
            return False
            
    @staticmethod
    def get_service_status() -> str:
        """Get service status"""
        if not PYWIN32_AVAILABLE:
            return "Not Available (pywin32 missing)"
            
        if not ServiceManager.is_service_installed():
            return "Not Installed"
            
        if ServiceManager.is_service_running():
            return "Running"
        else:
            return "Stopped"


def run_service_command(command: str, enable_tray: bool = True) -> bool:
    """Run service command"""
    if command == "install":
        return ServiceManager.install_service()
    elif command == "uninstall":
        return ServiceManager.uninstall_service()
    elif command == "start":
        if not ServiceManager.is_service_installed():
            print("Service is not installed.")
            print("To install the service, run:")
            print("  python power_status.py --service install")
            print()
            print("Or to run without installation:")
            print("  python power_status.py --service run")
            return False
        return ServiceManager.start_service()
    elif command == "stop":
        return ServiceManager.stop_service()
    elif command == "status":
        status = ServiceManager.get_service_status()
        print(f"Service Status: {status}")
        return True
    elif command == "run":
        # Run service directly without installation
        print("Running PowerStatus service directly...")
        print("Press Ctrl+C to stop the service.")
        
        try:
            # Create shared state
            control_state = {
                'repeat': False,
                'interval': 2.0,
                'show_timer': False,
                'show_system_stats': True
            }
            
            # Initialize components
            from power_status import PowerMonitor
            notification_manager = NotificationManager()
            
            # Send start notification
            notification_manager.send_notification(
                "service_start",
                "PowerStatus Service Started",
                "PowerStatus monitoring service is now running (direct mode)"
            )
            
            monitor = PowerMonitor(
                control_state=control_state,
                notification_manager=notification_manager
            )
            
            # Start system tray if enabled
            tray = None
            if enable_tray:
                print("Starting system tray...")
                tray = PowerStatusTray(
                    get_status_callback=lambda: {
                        'power_state': monitor.get_power_status(),
                        'total_runtime': monitor.get_total_runtime()
                    },
                    control_state=control_state
                )
                tray.start_threaded()
                time.sleep(1)  # Give tray time to initialize
                
            print("PowerStatus service running...")
            print("Press Ctrl+C to stop.")
            
            # Run monitor
            monitor.run()
            
        except KeyboardInterrupt:
            print("\nShutting down PowerStatus service...")
            if tray:
                tray.stop()
        except Exception as e:
            print(f"Service error: {e}")
            return False
            
        return True
    else:
        print(f"Unknown service command: {command}")
        print("Available commands: install, uninstall, start, stop, status, run")
        return False


if __name__ == '__main__':
    if len(sys.argv) == 1:
        # Run as Windows service
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(PowerStatusService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Handle command line arguments
        win32serviceutil.HandleCommandLine(PowerStatusService)
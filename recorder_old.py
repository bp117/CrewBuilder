import cv2
import numpy as np
import time
import json
from datetime import datetime
import threading
from PIL import Image
import platform
import os
import mouse
import keyboard
import win32gui
import win32ui
import win32con
import win32api
from ctypes import windll
import pystray
import sys
from win32api import GetSystemMetrics
from win32con import (
    SM_CXSCREEN, SM_CYSCREEN,
    SM_CXVIRTUALSCREEN, SM_CYVIRTUALSCREEN,
    SM_XVIRTUALSCREEN, SM_YVIRTUALSCREEN,
    SRCCOPY
)

class WindowsScreenRecorder:
    def __init__(self):
        
        try:
            windll.user32.SetProcessDPIAware()
        except Exception as e:
            print(f"DPI awareness error: {e}")

        
        self.width = GetSystemMetrics(SM_CXSCREEN)
        self.height = GetSystemMetrics(SM_CYSCREEN)
        
        
        self.virtual_width = GetSystemMetrics(SM_CXVIRTUALSCREEN)
        self.virtual_height = GetSystemMetrics(SM_CYVIRTUALSCREEN)
        
        
        self.width = max(self.width, self.virtual_width)
        self.height = max(self.height, self.virtual_height)
        
        
        self.width = self.width - (self.width % 2)
        self.height = self.height - (self.height % 2)
        
        print(f"Recording screen at resolution: {self.width}x{self.height}")

    def capture_screen(self):
        try:
            
            hwnd = win32gui.GetDesktopWindow()
            
            
            window_dc = win32gui.GetWindowDC(hwnd)
            img_dc = win32ui.CreateDCFromHandle(window_dc)
            mem_dc = img_dc.CreateCompatibleDC()
            
            
            screenshot = win32ui.CreateBitmap()
            screenshot.CreateCompatibleBitmap(img_dc, self.width, self.height)
            mem_dc.SelectObject(screenshot)
            
            
            mem_dc.BitBlt((0, 0), (self.width, self.height), 
                         img_dc, (0, 0), SRCCOPY)
            
            
            bmp_str = screenshot.GetBitmapBits(True)
            img = np.frombuffer(bmp_str, dtype='uint8')
            img.shape = (self.height, self.width, 4)
            
            
            mem_dc.DeleteDC()
            win32gui.DeleteObject(screenshot.GetHandle())
            img_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, window_dc)
            
            
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img
            
        except Exception as e:
            print(f"Screen capture error: {e}")
            return None

class SystemTrayHandler:
    def __init__(self, stop_callback, app_window):
        self.stop_callback = stop_callback
        self.app_window = app_window
        self.tray_app = None
        self._running = False

    def create_tray_icon(self):
        try:
            
            icon_size = (64, 64)
            icon_image = Image.new('RGB', icon_size, color='red')

            
            def safe_stop(icon, item):
                self._running = False
                icon.stop()
                self.app_window.after(100, self.stop_callback)

            menu = pystray.Menu(
                pystray.MenuItem("Stop Recording", safe_stop)
            )

            
            self.tray_app = pystray.Icon(
                "screen_recorder",
                icon_image,
                "Screen Recorder (Recording in Progress)",
                menu=menu
            )

            self._running = True
            
            threading.Thread(target=self._run_tray, daemon=True).start()
            
        except Exception as e:
            print(f"Error creating tray icon: {e}")

    def _run_tray(self):
        try:
            if self.tray_app and self._running:
                self.tray_app.run()
        except Exception as e:
            print(f"Tray icon error: {e}")

    def stop(self):
        try:
            self._running = False
            if self.tray_app and self.tray_app.visible:
                self.tray_app.stop()
        except Exception as e:
            print(f"Error stopping tray: {e}")

class CrossPlatformScreenRecorder:
    def __init__(self, app_reference):
        self.recording = False
        self.frames = []
        self.interactions = []
        self.app = app_reference
        self.last_scroll_time = time.time()
        self.scroll_cooldown = 0.5
        self.windows_recorder = WindowsScreenRecorder()
        self.initial_state = None
        self.recording_thread = None
        
    def get_element_under_cursor(self):
        try:
            x, y = mouse.get_position()
            hwnd = win32gui.WindowFromPoint((x, y))
            class_name = win32gui.GetClassName(hwnd)
            window_text = win32gui.GetWindowText(hwnd)
            return {
                "class": class_name,
                "text": window_text,
                "window_handle": hwnd,
                "position": {"x": x, "y": y}
            }
        except Exception:
            return {
                "position": {"x": x, "y": y}
            }

    def handle_mouse_event(self, event):
        try:
            if isinstance(event, mouse.ButtonEvent):
                if event.event_type in ['down', 'click']:
                    element = self.get_element_under_cursor()
                    self.interactions.append({
                        "timestamp": datetime.now().isoformat(),
                        "type": "click",
                        "button": event.button,
                        "element": element
                    })
            elif isinstance(event, mouse.WheelEvent):
                current_time = time.time()
                if current_time - self.last_scroll_time >= self.scroll_cooldown:
                    x, y = mouse.get_position()
                    self.interactions.append({
                        "timestamp": datetime.now().isoformat(),
                        "type": "scroll",
                        "direction": "down" if event.delta < 0 else "up",
                        "position": {"x": x, "y": y}
                    })
                    self.last_scroll_time = current_time
        except Exception as e:
            print(f"Mouse event error: {e}")

    def handle_keyboard_event(self, event):
        try:
            if event.event_type == keyboard.KEY_DOWN:
                self.interactions.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "keypress",
                    "key": event.name
                })
        except Exception as e:
            print(f"Keyboard event error: {e}")

    def minimize_window(self):
        """Store window state before minimizing"""
        try:
            
            self.initial_state = {
                'geometry': self.app.root.geometry(),
                'state': self.app.root.state(),
                'width': self.app.root.winfo_width(),
                'height': self.app.root.winfo_height(),
                'x': self.app.root.winfo_x(),
                'y': self.app.root.winfo_y()
            }
            print(f"Stored window state: {self.initial_state}")
            self.app.root.withdraw()
        except Exception as e:
            print(f"Error storing window state: {e}")


    def restore_window(self):
        """Restore window with improved reliability"""
        try:
            print("Starting window restoration...")
            
            
            self.app.root.deiconify()
            self.app.root.update()
            
            
            self.app.root.attributes('-topmost', True)
            self.app.root.update()
            
            
            if self.initial_state:
                print(f"Restoring window geometry: {self.initial_state['geometry']}")
                self.app.root.geometry(self.initial_state['geometry'])
                
                if 'zoomed' in self.initial_state['state']:
                    self.app.root.state('zoomed')
            
            
            self.app.root.lift()
            self.app.root.focus_force()
            
            
            self.app.root.attributes('-topmost', False)
            
            
            self.app.root.update_idletasks()
            self.app.root.update()
            
            print("Window restoration completed")
            
        except Exception as e:
            print(f"Error in primary window restoration: {e}")
            try:
                
                self.app.root.deiconify()
                self.app.root.attributes('-topmost', True)
                self.app.root.update()
                self.app.root.attributes('-topmost', False)
                self.app.root.lift()
                self.app.root.update()
            except Exception as e2:
                print(f"Fallback window restoration failed: {e2}")



    def record_screen(self):
        while self.recording:
            try:
                frame = self.windows_recorder.capture_screen()
                if frame is not None:
                    self.frames.append(frame)
                time.sleep(0.1)  
            except Exception as e:
                print(f"Recording error: {e}")
                continue

    def start_recording(self):
        
        self.recording = False
        self.frames = []
        self.interactions = []
        
        try:
            
            self.tray_handler = SystemTrayHandler(self.stop_recording, self.app.root)
            self.tray_handler.create_tray_icon()
            
            
            mouse.hook(self.handle_mouse_event)
            keyboard.on_press(self.handle_keyboard_event)
            
            
            self.minimize_window()
            
            
            self.recording = True
            self.recording_thread = threading.Thread(target=self.record_screen, daemon=True)
            self.recording_thread.start()
            
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.stop_recording()



    def stop_recording(self):
        """Stop recording with improved window restoration"""
        try:
            print("Stopping recording process...")
            
            self.recording = False
            time.sleep(0.5)  

            
            try:
                print("Unhooking input monitors...")
                mouse.unhook_all()
                keyboard.unhook_all()
            except Exception as e:
                print(f"Error unhooking input: {e}")

            try:
                print("Stopping tray icon...")
                if hasattr(self, 'tray_handler'):
                    self.tray_handler.stop()
            except Exception as e:
                print(f"Error stopping tray: {e}")

            
            print("Saving video file...")
            output_path = self.save_video_file()
            if not output_path:
                raise Exception("Failed to save video file")

            print("Saving interactions file...")
            interactions_path = self.save_interactions_file()
            if not interactions_path:
                raise Exception("Failed to save interactions file")

            
            print("Restoring window...")
            self.restore_window()

            print(f"Recording stopped. Files saved: {output_path}, {interactions_path}")
            return output_path, interactions_path

        except Exception as e:
            print(f"Error in stop_recording: {e}")
            
            try:
                self.restore_window()
            except:
                pass
            return None, None
    def save_video_file(self):
        """Save recorded frames to video file"""
        if not self.frames:
            return None

        output_path = "recorded_video.mp4"
        try:
            height, width = self.frames[0].shape[:2]
            out = cv2.VideoWriter(
                output_path,
                cv2.VideoWriter_fourcc(*'mp4v'),
                10,  
                (width, height)
            )

            for frame in self.frames:
                out.write(frame)
            out.release()

            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            return None

        except Exception as e:
            print(f"Error saving video: {e}")
            return None

    def save_interactions_file(self):
        """Save recorded interactions to JSON file"""
        interactions_path = 'interactions.json'
        try:
            interaction_data = {
                "recording_data": {
                    "start_time": self.interactions[0]["timestamp"] if self.interactions else None,
                    "end_time": self.interactions[-1]["timestamp"] if self.interactions else None,
                    "total_frames": len(self.frames),
                    "platform": "Windows",
                    "interactions": self.interactions
                }
            }

            with open(interactions_path, 'w') as f:
                json.dump(interaction_data, f, indent=2)

            
            if os.path.exists(interactions_path) and os.path.getsize(interactions_path) > 0:
                return interactions_path
            return None

        except Exception as e:
            print(f"Error saving interactions: {e}")
            return None
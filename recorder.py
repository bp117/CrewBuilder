import cv2
import numpy as np
import time
import json
from datetime import datetime
import threading
import platform
import os
import mouse
import keyboard
import sounddevice as sd
import subprocess
from PIL import Image
import pystray
import sys
from pathlib import Path
from scipy.io import wavfile

# Platform specific imports
if platform.system() == 'Windows':
    import win32gui
    import win32ui
    import win32con
    import win32api
    from ctypes import windll
    from win32api import GetSystemMetrics
elif platform.system() == 'Darwin':  # macOS
    from Quartz import (CGWindowListCreateImage, CGRectInfinite,
                       kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
    from CoreFoundation import CFRelease
    import Cocoa
    import AppKit

class ScreenRecorder:
    """Base class for screen recording functionality"""
    def __init__(self):
        self.width = 0
        self.height = 0
        self.initialize_dimensions()

    def initialize_dimensions(self):
        raise NotImplementedError("Subclasses must implement initialize_dimensions")

    def capture_screen(self):
        raise NotImplementedError("Subclasses must implement capture_screen")

class WindowsScreenRecorder(ScreenRecorder):
    """Windows-specific screen recorder implementation"""
    def initialize_dimensions(self):
        try:
            # Set DPI awareness
            windll.user32.SetProcessDPIAware()
            
            # Get screen dimensions
            self.width = GetSystemMetrics(win32con.SM_CXSCREEN)
            self.height = GetSystemMetrics(win32con.SM_CYSCREEN)
            
            # Ensure even dimensions for video encoding
            self.width = self.width - (self.width % 2)
            self.height = self.height - (self.height % 2)
            
            print(f"Windows screen dimensions: {self.width}x{self.height}")
        except Exception as e:
            print(f"Error initializing Windows screen recorder: {e}")
            raise

    def capture_screen(self):
        try:
            # Get handle to desktop window
            hwnd = win32gui.GetDesktopWindow()
            
            # Create device contexts and bitmap
            window_dc = win32gui.GetWindowDC(hwnd)
            img_dc = win32ui.CreateDCFromHandle(window_dc)
            mem_dc = img_dc.CreateCompatibleDC()
            
            screenshot = win32ui.CreateBitmap()
            screenshot.CreateCompatibleBitmap(img_dc, self.width, self.height)
            mem_dc.SelectObject(screenshot)
            
            # Copy screen to bitmap
            mem_dc.BitBlt((0, 0), (self.width, self.height), 
                         img_dc, (0, 0), win32con.SRCCOPY)
            
            # Convert bitmap to numpy array
            bmp_str = screenshot.GetBitmapBits(True)
            img = np.frombuffer(bmp_str, dtype='uint8')
            img.shape = (self.height, self.width, 4)
            
            # Cleanup
            mem_dc.DeleteDC()
            win32gui.DeleteObject(screenshot.GetHandle())
            img_dc.DeleteDC()
            win32gui.ReleaseDC(hwnd, window_dc)
            
            # Convert from BGRA to BGR
            return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            
        except Exception as e:
            print(f"Error capturing screen on Windows: {e}")
            return None

class MacScreenRecorder(ScreenRecorder):
    """macOS-specific screen recorder implementation"""
    def initialize_dimensions(self):
        try:
            # Get main screen dimensions
            screen = Cocoa.NSScreen.mainScreen()
            frame = screen.frame()
            self.width = int(frame.size.width)
            self.height = int(frame.size.height)
            
            # Ensure even dimensions
            self.width = self.width - (self.width % 2)
            self.height = self.height - (self.height % 2)
            
            print(f"macOS screen dimensions: {self.width}x{self.height}")
        except Exception as e:
            print(f"Error initializing macOS screen recorder: {e}")
            raise

    def capture_screen(self):
        try:
            # Capture screen content
            screenshot = CGWindowListCreateImage(
                CGRectInfinite,
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID,
                0
            )
            
            if screenshot:
                # Convert to numpy array
                width = self.width
                height = self.height
                
                # Get raw data
                dataProvider = screenshot.dataProvider()
                data = dataProvider.data()
                
                # Convert to numpy array
                array = np.frombuffer(data, dtype=np.uint8)
                array = array.reshape((height, width, 4))
                
                # Release CoreFoundation objects
                CFRelease(screenshot)
                
                # Convert RGBA to BGR
                return cv2.cvtColor(array, cv2.COLOR_RGBA2BGR)
                
        except Exception as e:
            print(f"Error capturing screen on macOS: {e}")
            return None

class AudioRecorder:
    """Handles audio recording functionality"""
    def __init__(self):
        self.audio_frames = []
        self.recording = False
        self.sample_rate = 44100
        self.start_time = None

    def start_recording(self):
        self.recording = True
        self.audio_frames = []
        self.start_time = time.time()
        
        # Start audio recording thread
        threading.Thread(target=self._record_audio, daemon=True).start()

    def stop_recording(self):
        self.recording = False
    def _record_audio(self):
        try:
            with sd.InputStream(channels=2, callback=self._audio_callback,
                              samplerate=self.sample_rate,
                              blocksize=int(self.sample_rate/10)):  # 100ms blocks
                while self.recording:
                    time.sleep(0.001)  # Tiny sleep to prevent CPU overuse
        except Exception as e:
            print(f"Error recording audio: {e}")



    def _audio_callback(self, indata, frames, time, status):
        if status:
            print(status)
        self.audio_frames.append(indata.copy())

    def save_audio(self, filename):
        if not self.audio_frames:
            return False
            
        try:
            audio_data = np.concatenate(self.audio_frames, axis=0)
            wavfile.write(filename, self.sample_rate, audio_data)
            return True
        except Exception as e:
            print(f"Error saving audio: {e}")
            return False

class InteractionRecorder:
    """Records mouse and keyboard interactions"""
    def __init__(self):
        self.interactions = []
        self.mouse_positions = []
        self.last_mouse_time = time.time()
        self.mouse_sample_rate = 0.05  # 50ms
        self.recording = False

    def start_recording(self):
        self.recording = True
        self.interactions = []
        self.mouse_positions = []
        
        # Hook mouse and keyboard events
        mouse.hook(self._mouse_callback)
        keyboard.hook(self._keyboard_callback)
        
        # Start mouse position tracking thread
        threading.Thread(target=self._track_mouse, daemon=True).start()

    def stop_recording(self):
        self.recording = False
        mouse.unhook_all()
        keyboard.unhook_all()

    def _mouse_callback(self, event):
        if not self.recording:
            return
            
        try:
            if isinstance(event, mouse.ButtonEvent):
                x, y = mouse.get_position()
                self.interactions.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": f"mouse_{event.event_type}",
                    "button": event.button,
                    "position": {"x": x, "y": y}
                })
            elif isinstance(event, mouse.WheelEvent):
                x, y = mouse.get_position()
                self.interactions.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "scroll",
                    "direction": "down" if event.delta < 0 else "up",
                    "position": {"x": x, "y": y}
                })
        except Exception as e:
            print(f"Error in mouse callback: {e}")

    def _keyboard_callback(self, event):
        if not self.recording:
            return
            
        if event.event_type == keyboard.KEY_DOWN:
            self.interactions.append({
                "timestamp": datetime.now().isoformat(),
                "type": "keypress",
                "key": event.name
            })

    def _track_mouse(self):
        while self.recording:
            current_time = time.time()
            if current_time - self.last_mouse_time >= self.mouse_sample_rate:
                try:
                    x, y = mouse.get_position()
                    self.mouse_positions.append({
                        "timestamp": datetime.now().isoformat(),
                        "type": "mouse_move",
                        "position": {"x": x, "y": y}
                    })
                    self.last_mouse_time = current_time
                except Exception as e:
                    print(f"Error tracking mouse: {e}")
            time.sleep(0.01)

    def save_interactions(self, filename):
        try:
            # Combine and sort all interactions
            all_interactions = sorted(
                self.interactions + self.mouse_positions,
                key=lambda x: x['timestamp']
            )
            
            data = {
                "recording_data": {
                    "start_time": all_interactions[0]["timestamp"] if all_interactions else None,
                    "end_time": all_interactions[-1]["timestamp"] if all_interactions else None,
                    "platform": platform.system(),
                    "interactions": all_interactions
                }
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving interactions: {e}")
            return False

class CrossPlatformScreenRecorder:
    """Main screen recorder class that coordinates all recording functionality"""
    def __init__(self, app_reference):
        self.app = app_reference
        self.recording = False
        self.frames = []
        self.frame_times = []  # Store frame timestamps
        self.start_time = None
        
        # Initialize recorders
        if platform.system() == 'Windows':
            self.screen_recorder = WindowsScreenRecorder()
        elif platform.system() == 'Darwin':
            self.screen_recorder = MacScreenRecorder()
        else:
            raise NotImplementedError(f"Platform {platform.system()} not supported")
            
        self.audio_recorder = AudioRecorder()
        self.interaction_recorder = InteractionRecorder()
        
        # Create output directory
        self.output_dir = Path("recordings")
        self.output_dir.mkdir(exist_ok=True)

    def _record_screen(self):
        """Record screen frames with timestamps"""
        frame_interval = 1/30  # Target 30 FPS
        next_frame_time = time.time()

        while self.recording:
            current_time = time.time()
            if current_time >= next_frame_time:
                frame = self.screen_recorder.capture_screen()
                if frame is not None:
                    self.frames.append(frame)
                    self.frame_times.append(current_time - self.start_time)
                next_frame_time = current_time + frame_interval
            else:
                time.sleep(0.001)

    def start_recording(self):
        """Start all recording processes"""
        try:
            self.recording = True
            self.frames = []
            self.frame_times = []
            self.start_time = time.time()
            
            # Start audio first
            self.audio_recorder.start_recording()
            
            # Start screen recording
            threading.Thread(target=self._record_screen, daemon=True).start()
            
            # Start interaction recording
            self.interaction_recorder.start_recording()
            
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.stop_recording()

    def _save_video_with_audio(self, video_path, audio_path):
        """Combine video frames with audio ensuring sync"""
        try:
            if not self.frames:
                return False
                
            temp_video = str(video_path.with_suffix('.temp.mp4'))
            
            # Calculate actual achieved FPS
            if len(self.frame_times) > 1:
                actual_fps = len(self.frame_times) / (self.frame_times[-1] - self.frame_times[0])
            else:
                actual_fps = 30
            
            # Save video frames
            height, width = self.frames[0].shape[:2]
            out = cv2.VideoWriter(
                temp_video,
                cv2.VideoWriter_fourcc(*'mp4v'),
                actual_fps,
                (width, height)
            )
            
            for frame in self.frames:
                out.write(frame)
            out.release()
            
            # Combine video and audio using ffmpeg with explicit sync
            if os.path.exists(audio_path):
                command = [
                    'ffmpeg', '-y',
                    '-i', temp_video,
                    '-i', audio_path,
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-map', '0:v:0',
                    '-map', '1:a:0',
                    '-vsync', '1',
                    '-async', '1',
                    str(video_path)
                ]
                subprocess.run(command, check=True)
                os.remove(temp_video)
            else:
                os.rename(temp_video, video_path)
            
            return True
            
        except Exception as e:
            print(f"Error saving video with audio: {e}")
            return False
    def stop_recording(self):
        """Stop all recording processes and save files"""
        if not self.recording:
            return None, None
            
        try:
            self.recording = False
            
            # Stop all recorders
            self.audio_recorder.stop_recording()
            self.interaction_recorder.stop_recording()
            
            # Generate filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_path = self.output_dir / f"recording_{timestamp}.mp4"
            audio_path = self.output_dir / f"audio_{timestamp}.wav"
            interactions_path = self.output_dir / f"interactions_{timestamp}.json"
            
            # Save interactions
            self.interaction_recorder.save_interactions(interactions_path)
            
            # Save audio
            self.audio_recorder.save_audio(audio_path)
            
            # Save video with audio
            self._save_video_with_audio(video_path, audio_path)
            
            # Clean up
            if os.path.exists(audio_path):
                os.remove(audio_path)
            
            return str(video_path), str(interactions_path)
            
        except Exception as e:
            print(f"Error stopping recording: {e}")
            return None, None


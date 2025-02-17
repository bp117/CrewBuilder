from Quartz import (
    CGWindowListCreateImage,
    CGRectInfinite,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID,
    CGMainDisplayID,
    CGDisplayPixelsHigh,
    CGDisplayPixelsWide,
    CGImageGetWidth,
    CGImageGetHeight,
    CGImageGetBytesPerRow,
    CGImageGetBitsPerPixel,
    CGImageGetDataProvider,
    CGDataProviderCopyData,
    CGImageGetBitsPerComponent
)
from CoreFoundation import CFDataGetBytePtr, CFDataGetLength
import numpy as np
import cv2

class MacScreenRecorder(ScreenRecorder):
    """macOS-specific screen recorder implementation"""
    def initialize_dimensions(self):
        try:
            # Get main display ID
            main_display_id = CGMainDisplayID()
            
            # Get screen dimensions
            self.width = CGDisplayPixelsWide(main_display_id)
            self.height = CGDisplayPixelsHigh(main_display_id)
            
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
                # Get image dimensions
                width = CGImageGetWidth(screenshot)
                height = CGImageGetHeight(screenshot)
                bytes_per_row = CGImageGetBytesPerRow(screenshot)
                bits_per_pixel = CGImageGetBitsPerPixel(screenshot)
                bits_per_component = CGImageGetBitsPerComponent(screenshot)
                
                # Get image data
                data_provider = CGImageGetDataProvider(screenshot)
                data = CGDataProviderCopyData(data_provider)
                
                # Convert to numpy array
                buf_length = CFDataGetLength(data)
                buf_pointer = CFDataGetBytePtr(data)
                
                # Create numpy array from buffer
                array = np.frombuffer(
                    buffer=buf_pointer,
                    dtype=np.uint8,
                    count=buf_length
                ).reshape(height, bytes_per_row//(bits_per_pixel//bits_per_component), bits_per_pixel//bits_per_component)
                
                # Convert BGRA to BGR
                if array.shape[2] == 4:  # If BGRA
                    array = array[:, :, :3]  # Keep only BGR channels
                
                return array
                
        except Exception as e:
            print(f"Error capturing screen on macOS: {e}")
            return None


import cv2
import numpy as np
import time
import json
from datetime import datetime
import threading
import platform
import os
from pynput import mouse, keyboard
import subprocess
from PIL import Image
import pystray
import sys
from pathlib import Path

# Platform specific imports
if platform.system() == 'Windows':
    import win32gui
    import win32ui
    import win32con
    import win32api
    from ctypes import windll
    from win32api import GetSystemMetrics
elif platform.system() == 'Darwin':  # macOS
    from Quartz import (
        CGWindowListCreateImage,
        CGRectInfinite,
        kCGWindowListOptionOnScreenOnly,
        kCGNullWindowID,
        CGMainDisplayID,
        CGDisplayPixelsHigh,
        CGDisplayPixelsWide,
        CGImageGetWidth,
        CGImageGetHeight,
        CGImageGetBytesPerRow,
        CGImageGetBitsPerPixel,
        CGImageGetDataProvider,
        CGDataProviderCopyData,
        CGImageGetBitsPerComponent
    )
    from CoreFoundation import CFDataGetBytePtr, CFDataGetLength

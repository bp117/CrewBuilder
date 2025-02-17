import threading
import time
from datetime import datetime
import json
from pathlib import Path
import platform
from pynput import mouse, keyboard

class MacInteractionRecorder:
    def __init__(self):
        # Initialize state variables
        self.recording = False
        self.interactions = []
        self.mouse_positions = []
        self.last_mouse_time = time.time()
        self.mouse_sample_rate = 0.05  # Sample mouse position every 50ms
        
        # Initialize listeners as None
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # Track modifier keys state
        self.modifiers = {
            'cmd': False,
            'shift': False,
            'alt': False,
            'ctrl': False
        }
        
        # Special key mappings for macOS
        self.key_mapping = {
            keyboard.Key.cmd: 'cmd',
            keyboard.Key.shift: 'shift',
            keyboard.Key.alt: 'alt',
            keyboard.Key.ctrl: 'ctrl',
            keyboard.Key.space: 'space',
            keyboard.Key.enter: 'return',
            keyboard.Key.backspace: 'delete',
            keyboard.Key.tab: 'tab',
            keyboard.Key.caps_lock: 'caps_lock',
            keyboard.Key.esc: 'escape',
            keyboard.Key.up: 'up_arrow',
            keyboard.Key.down: 'down_arrow',
            keyboard.Key.left: 'left_arrow',
            keyboard.Key.right: 'right_arrow',
            keyboard.Key.page_up: 'page_up',
            keyboard.Key.page_down: 'page_down',
            keyboard.Key.home: 'home',
            keyboard.Key.end: 'end',
        }

    def start_recording(self):
        """Start recording with error handling"""
        try:
            # Reset state
            self.recording = True
            self.interactions = []
            self.mouse_positions = []
            self.modifiers = {key: False for key in self.modifiers}

            # Initialize listeners
            self.mouse_listener = mouse.Listener(
                on_move=self._safe_mouse_move,
                on_click=self._safe_mouse_click,
                on_scroll=self._safe_mouse_scroll
            )

            self.keyboard_listener = keyboard.Listener(
                on_press=self._safe_key_press,
                on_release=self._safe_key_release
            )

            # Start listeners in separate threads
            mouse_thread = threading.Thread(target=self._start_mouse_listener)
            keyboard_thread = threading.Thread(target=self._start_keyboard_listener)

            mouse_thread.daemon = True
            keyboard_thread.daemon = True

            mouse_thread.start()
            keyboard_thread.start()

            # Wait for threads to initialize
            mouse_thread.join(timeout=1.0)
            keyboard_thread.join(timeout=1.0)

            if not (self.mouse_listener and self.keyboard_listener):
                raise Exception("Failed to initialize listeners")

            print("Recording started successfully")

        except Exception as e:
            print(f"Error starting recording: {e}")
            self.recording = False
            self.cleanup()
            raise

    def _start_mouse_listener(self):
        """Start mouse listener with error handling"""
        try:
            if self.mouse_listener and not self.mouse_listener.running:
                self.mouse_listener.start()
                print("Mouse listener started")
        except Exception as e:
            print(f"Error starting mouse listener: {e}")
            self.mouse_listener = None

    def _start_keyboard_listener(self):
        """Start keyboard listener with error handling"""
        try:
            if self.keyboard_listener and not self.keyboard_listener.running:
                self.keyboard_listener.start()
                print("Keyboard listener started")
        except Exception as e:
            print(f"Error starting keyboard listener: {e}")
            self.keyboard_listener = None

    def stop_recording(self):
        """Stop recording and cleanup"""
        self.recording = False
        self.cleanup()

    def cleanup(self):
        """Clean up listeners"""
        try:
            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None

            if self.keyboard_listener:
                self.keyboard_listener.stop()
                self.keyboard_listener = None
        except Exception as e:
            print(f"Error during cleanup: {e}")

    def _safe_mouse_move(self, x, y):
        """Handle mouse movement with error handling"""
        if not self.recording:
            return

        try:
            current_time = time.time()
            if current_time - self.last_mouse_time >= self.mouse_sample_rate:
                self.mouse_positions.append({
                    'timestamp': datetime.now().isoformat(),
                    'type': 'mouse_move',
                    'position': {'x': x, 'y': y},
                    'modifiers': self._get_active_modifiers()
                })
                self.last_mouse_time = current_time
        except Exception as e:
            print(f"Error recording mouse movement: {e}")

    def _safe_mouse_click(self, x, y, button, pressed):
        """Handle mouse clicks with error handling"""
        if not self.recording:
            return

        try:
            button_name = {
                mouse.Button.left: 'left',
                mouse.Button.right: 'right',
                mouse.Button.middle: 'middle'
            }.get(button, str(button))

            self.interactions.append({
                'timestamp': datetime.now().isoformat(),
                'type': f'mouse_{"down" if pressed else "up"}',
                'button': button_name,
                'position': {'x': x, 'y': y},
                'modifiers': self._get_active_modifiers()
            })
        except Exception as e:
            print(f"Error recording mouse click: {e}")

    def _safe_mouse_scroll(self, x, y, dx, dy):
        """Handle mouse scroll with error handling"""
        if not self.recording:
            return

        try:
            self.interactions.append({
                'timestamp': datetime.now().isoformat(),
                'type': 'scroll',
                'direction': 'down' if dy < 0 else 'up',
                'position': {'x': x, 'y': y},
                'amount': abs(dy),
                'modifiers': self._get_active_modifiers()
            })
        except Exception as e:
            print(f"Error recording scroll: {e}")

    def _safe_key_press(self, key):
        """Handle key press with error handling"""
        if not self.recording:
            return

        try:
            key_name = self._get_key_name(key)
            
            # Update modifier state
            if key_name in self.modifiers:
                self.modifiers[key_name] = True

            self.interactions.append({
                'timestamp': datetime.now().isoformat(),
                'type': 'key_down',
                'key': key_name,
                'modifiers': self._get_active_modifiers()
            })
        except Exception as e:
            print(f"Error recording key press: {e}")

    def _safe_key_release(self, key):
        """Handle key release with error handling"""
        if not self.recording:
            return

        try:
            key_name = self._get_key_name(key)
            
            # Update modifier state
            if key_name in self.modifiers:
                self.modifiers[key_name] = False

            self.interactions.append({
                'timestamp': datetime.now().isoformat(),
                'type': 'key_up',
                'key': key_name,
                'modifiers': self._get_active_modifiers()
            })
        except Exception as e:
            print(f"Error recording key release: {e}")

    def _get_key_name(self, key):
        """Get the name of a key"""
        try:
            # Check if it's a special key
            if key in self.key_mapping:
                return self.key_mapping[key]
            
            # Try to get character
            if hasattr(key, 'char'):
                return key.char or f'unknown_key_{key}'
            
            # Fallback
            return str(key)
        except:
            return 'unknown_key'

    def _get_active_modifiers(self):
        """Get currently active modifier keys"""
        return {key: value for key, value in self.modifiers.items() if value}

    def save_interactions(self, filename):
        """Save recorded interactions to file"""
        try:
            # Combine and sort all interactions
            all_interactions = sorted(
                self.interactions + self.mouse_positions,
                key=lambda x: x['timestamp']
            )

            # Prepare output data
            data = {
                'recording_data': {
                    'start_time': all_interactions[0]['timestamp'] if all_interactions else None,
                    'end_time': all_interactions[-1]['timestamp'] if all_interactions else None,
                    'platform': 'macOS',
                    'os_version': platform.mac_ver()[0],
                    'total_events': len(all_interactions),
                    'interactions': all_interactions
                }
            }

            # Ensure directory exists
            output_path = Path(filename)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            return True

        except Exception as e:
            print(f"Error saving interactions: {e}")
            return False

    def get_statistics(self):
        """Get recording statistics"""
        try:
            return {
                'total_events': len(self.interactions) + len(self.mouse_positions),
                'mouse_clicks': len([x for x in self.interactions if x['type'].startswith('mouse_')]),
                'key_presses': len([x for x in self.interactions if x['type'] == 'key_down']),
                'mouse_moves': len(self.mouse_positions),
                'scrolls': len([x for x in self.interactions if x['type'] == 'scroll']),
                'duration': (datetime.now() - datetime.fromisoformat(self.interactions[0]['timestamp'])).total_seconds() if self.interactions else 0
            }
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return None

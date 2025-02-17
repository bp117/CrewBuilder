from pynput import mouse, keyboard
import time
from datetime import datetime
import json
import threading
import platform
from pathlib import Path

class MacInteractionRecorder:
    """macOS-specific mouse and keyboard interaction recorder"""
    def __init__(self):
        self.interactions = []
        self.mouse_positions = []
        self.last_mouse_time = time.time()
        self.mouse_sample_rate = 0.05  # 50ms for mouse movement sampling
        self.recording = False
        
        # Initialize listeners
        self.mouse_listener = None
        self.keyboard_listener = None
        
        # Special keys mapping for macOS
        self.special_keys = {
            keyboard.Key.cmd: "command",
            keyboard.Key.alt: "option",
            keyboard.Key.shift: "shift",
            keyboard.Key.ctrl: "control",
            keyboard.Key.caps_lock: "caps_lock",
            keyboard.Key.tab: "tab",
            keyboard.Key.esc: "escape",
            keyboard.Key.space: "space",
            keyboard.Key.enter: "return",
            keyboard.Key.backspace: "delete",
            keyboard.Key.delete: "forward_delete",
            keyboard.Key.right: "right_arrow",
            keyboard.Key.left: "left_arrow",
            keyboard.Key.up: "up_arrow",
            keyboard.Key.down: "down_arrow",
            keyboard.Key.page_up: "page_up",
            keyboard.Key.page_down: "page_down",
            keyboard.Key.home: "home",
            keyboard.Key.end: "end"
        }
        
        # Track modifier keys state
        self.modifiers = {
            "command": False,
            "option": False,
            "shift": False,
            "control": False
        }

    def start_recording(self):
        """Start recording mouse and keyboard interactions"""
        try:
            self.recording = True
            self.interactions = []
            self.mouse_positions = []
            
            # Start mouse listener
            self.mouse_listener = mouse.Listener(
                on_move=self._on_move,
                on_click=self._on_click,
                on_scroll=self._on_scroll
            )
            self.mouse_listener.start()
            
            # Start keyboard listener
            self.keyboard_listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            self.keyboard_listener.start()
            
            print("Interaction recording started")
            
        except Exception as e:
            print(f"Error starting interaction recording: {e}")
            self.recording = False

    def stop_recording(self):
        """Stop recording interactions"""
        try:
            self.recording = False
            
            # Stop listeners
            if self.mouse_listener:
                self.mouse_listener.stop()
                self.mouse_listener = None
                
            if self.keyboard_listener:
                self.keyboard_listener.stop()
                self.keyboard_listener = None
                
            print("Interaction recording stopped")
            
        except Exception as e:
            print(f"Error stopping interaction recording: {e}")

    def _get_modifier_state(self):
        """Get current state of modifier keys"""
        return {key: value for key, value in self.modifiers.items() if value}

    def _on_move(self, x, y):
        """Handle mouse movement events"""
        if not self.recording:
            return
            
        current_time = time.time()
        if current_time - self.last_mouse_time >= self.mouse_sample_rate:
            try:
                self.mouse_positions.append({
                    "timestamp": datetime.now().isoformat(),
                    "type": "mouse_move",
                    "position": {"x": x, "y": y},
                    "modifiers": self._get_modifier_state()
                })
                self.last_mouse_time = current_time
            except Exception as e:
                print(f"Error recording mouse movement: {e}")

    def _on_click(self, x, y, button, pressed):
        """Handle mouse click events"""
        if not self.recording:
            return
            
        try:
            # Convert button to string representation
            if button == mouse.Button.left:
                button_name = "left"
            elif button == mouse.Button.right:
                button_name = "right"
            elif button == mouse.Button.middle:
                button_name = "middle"
            else:
                button_name = str(button)
            
            self.interactions.append({
                "timestamp": datetime.now().isoformat(),
                "type": "mouse_" + ("down" if pressed else "up"),
                "button": button_name,
                "position": {"x": x, "y": y},
                "modifiers": self._get_modifier_state()
            })
        except Exception as e:
            print(f"Error recording mouse click: {e}")

    def _on_scroll(self, x, y, dx, dy):
        """Handle mouse scroll events"""
        if not self.recording:
            return
            
        try:
            self.interactions.append({
                "timestamp": datetime.now().isoformat(),
                "type": "scroll",
                "direction": "down" if dy < 0 else "up",
                "position": {"x": x, "y": y},
                "amount": abs(dy),
                "modifiers": self._get_modifier_state()
            })
        except Exception as e:
            print(f"Error recording scroll: {e}")

    def _on_press(self, key):
        """Handle key press events"""
        if not self.recording:
            return
            
        try:
            # Handle modifier keys
            if key in self.special_keys:
                key_name = self.special_keys[key]
                if key_name in self.modifiers:
                    self.modifiers[key_name] = True
            
            # Get key name
            if hasattr(key, 'char'):
                key_name = key.char
            else:
                key_name = self.special_keys.get(key, str(key))
            
            self.interactions.append({
                "timestamp": datetime.now().isoformat(),
                "type": "keypress",
                "key": key_name,
                "modifiers": self._get_modifier_state()
            })
        except Exception as e:
            print(f"Error recording key press: {e}")

    def _on_release(self, key):
        """Handle key release events"""
        if not self.recording:
            return
            
        try:
            # Update modifier state
            if key in self.special_keys:
                key_name = self.special_keys[key]
                if key_name in self.modifiers:
                    self.modifiers[key_name] = False
            
            # Get key name
            if hasattr(key, 'char'):
                key_name = key.char
            else:
                key_name = self.special_keys.get(key, str(key))
            
            self.interactions.append({
                "timestamp": datetime.now().isoformat(),
                "type": "keyrelease",
                "key": key_name,
                "modifiers": self._get_modifier_state()
            })
        except Exception as e:
            print(f"Error recording key release: {e}")

    def save_interactions(self, filename):
        """Save recorded interactions to a file"""
        try:
            # Combine and sort all interactions
            all_interactions = sorted(
                self.interactions + self.mouse_positions,
                key=lambda x: x['timestamp']
            )
            
            # Prepare output data
            data = {
                "recording_data": {
                    "start_time": all_interactions[0]["timestamp"] if all_interactions else None,
                    "end_time": all_interactions[-1]["timestamp"] if all_interactions else None,
                    "platform": "macOS",
                    "os_version": platform.mac_ver()[0],
                    "total_events": len(all_interactions),
                    "interactions": all_interactions
                }
            }
            
            # Create directory if it doesn't exist
            output_path = Path(filename)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"Interactions saved to: {filename}")
            return True
            
        except Exception as e:
            print(f"Error saving interactions: {e}")
            return False

    def get_statistics(self):
        """Get statistics about recorded interactions"""
        try:
            mouse_clicks = len([x for x in self.interactions if x['type'].startswith('mouse_')])
            key_presses = len([x for x in self.interactions if x['type'] == 'keypress'])
            mouse_moves = len(self.mouse_positions)
            scrolls = len([x for x in self.interactions if x['type'] == 'scroll'])
            
            return {
                "total_events": len(self.interactions) + len(self.mouse_positions),
                "mouse_clicks": mouse_clicks,
                "key_presses": key_presses,
                "mouse_moves": mouse_moves,
                "scrolls": scrolls
            }
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return None

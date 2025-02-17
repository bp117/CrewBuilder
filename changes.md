from pynput import mouse, keyboard
import time
from datetime import datetime
import threading

class InteractionRecorder:
    """Records mouse and keyboard interactions using pynput"""
    def __init__(self):
        self.interactions = []
        self.mouse_positions = []
        self.last_mouse_time = time.time()
        self.mouse_sample_rate = 0.05  # 50ms
        self.recording = False
        self.mouse_listener = None
        self.keyboard_listener = None

    def start_recording(self):
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
            on_press=self._on_press
        )
        self.keyboard_listener.start()

    def stop_recording(self):
        self.recording = False
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()

    def _on_move(self, x, y):
        if not self.recording:
            return
            
        current_time = time.time()
        if current_time - self.last_mouse_time >= self.mouse_sample_rate:
            self.mouse_positions.append({
                "timestamp": datetime.now().isoformat(),
                "type": "mouse_move",
                "position": {"x": x, "y": y}
            })
            self.last_mouse_time = current_time

    def _on_click(self, x, y, button, pressed):
        if not self.recording:
            return
            
        self.interactions.append({
            "timestamp": datetime.now().isoformat(),
            "type": "mouse_" + ("down" if pressed else "up"),
            "button": str(button),
            "position": {"x": x, "y": y}
        })

    def _on_scroll(self, x, y, dx, dy):
        if not self.recording:
            return
            
        self.interactions.append({
            "timestamp": datetime.now().isoformat(),
            "type": "scroll",
            "direction": "down" if dy < 0 else "up",
            "position": {"x": x, "y": y}
        })

    def _on_press(self, key):
        if not self.recording:
            return
            
        try:
            key_name = key.char if hasattr(key, 'char') else str(key)
            self.interactions.append({
                "timestamp": datetime.now().isoformat(),
                "type": "keypress",
                "key": key_name
            })
        except AttributeError:
            pass  # Special keys that don't have a char attribute

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


class AudioRecorder:
    """Handles audio recording functionality"""
    def __init__(self):
        self.audio_frames = []
        self.recording = False
        self.sample_rate = 44100
        self.start_time = None
        self.channels = 1  # Changed to mono recording
        self.device_info = self._get_audio_device()

    def _get_audio_device(self):
        """Get the appropriate audio input device"""
        try:
            devices = sd.query_devices()
            default_input = sd.query_devices(kind='input')
            print("Available audio devices:", devices)
            print("Default input device:", default_input)
            return default_input
        except Exception as e:
            print(f"Error getting audio device: {e}")
            return None

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
            if not self.device_info:
                print("No audio device found")
                return

            # Configure audio stream
            stream_config = {
                'channels': self.channels,
                'callback': self._audio_callback,
                'samplerate': int(self.device_info['default_samplerate']),
                'blocksize': int(self.device_info['default_samplerate'] / 10),  # 100ms blocks
                'device': self.device_info['index']
            }
            
            print("Starting audio recording with config:", stream_config)
            
            with sd.InputStream(**stream_config):
                while self.recording:
                    time.sleep(0.001)
                    
        except Exception as e:
            print(f"Error recording audio: {e}")

    def _audio_callback(self, indata, frames, time, status):
        if status:
            print("Audio status:", status)
        if self.recording:
            self.audio_frames.append(indata.copy())

    def save_audio(self, filename):
        if not self.audio_frames:
            print("No audio frames to save")
            return False
            
        try:
            # Concatenate all audio frames
            audio_data = np.concatenate(self.audio_frames, axis=0)
            
            # Ensure the data is in the correct format (float32)
            audio_data = audio_data.astype(np.float32)
            
            # Normalize audio data to prevent clipping
            max_val = np.max(np.abs(audio_data))
            if max_val > 0:
                audio_data = audio_data / max_val
            
            print(f"Saving audio with shape: {audio_data.shape}")
            wavfile.write(filename, int(self.device_info['default_samplerate']), audio_data)
            return True
        except Exception as e:
            print(f"Error saving audio: {e}")
            return False

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
            
            # Combine video and audio if audio exists
            has_audio = os.path.exists(audio_path) and os.path.getsize(audio_path) > 0
            
            if has_audio:
                try:
                    command = [
                        'ffmpeg', '-y',
                        '-i', temp_video,
                        '-i', audio_path,
                        '-c:v', 'copy',
                        '-c:a', 'aac',
                        '-map', '0:v:0',
                        '-map', '1:a:0',
                        '-shortest',  # Use the shortest stream
                        str(video_path)
                    ]
                    subprocess.run(command, check=True, capture_output=True)
                    os.remove(temp_video)
                except Exception as e:
                    print(f"Error combining audio and video: {e}")
                    # Fallback to video only
                    os.rename(temp_video, video_path)
            else:
                # Just use the video without audio
                os.rename(temp_video, video_path)
            
            return True
            
        except Exception as e:
            print(f"Error saving video with audio: {e}")
            return False
            

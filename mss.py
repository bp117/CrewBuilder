import mss
import sounddevice as sd
import soundfile as sf
import numpy as np
import cv2
import time
import threading
from pathlib import Path
import subprocess

class ScreenRecorder:
    def __init__(self):
        self.recording = False
        self.frames = []
        self.audio_frames = []
        self.sct = mss.mss()
        self.sample_rate = 44100  # Audio sample rate
        
    def start_recording(self):
        """Start both screen and audio recording"""
        self.recording = True
        self.frames = []
        self.audio_frames = []
        
        # Start screen recording thread
        screen_thread = threading.Thread(target=self._record_screen)
        screen_thread.daemon = True
        screen_thread.start()
        
        # Start audio recording thread
        audio_thread = threading.Thread(target=self._record_audio)
        audio_thread.daemon = True
        audio_thread.start()
        
    def stop_recording(self):
        """Stop recording and save the video"""
        self.recording = False
        return self._save_recording()
        
    def _record_screen(self):
        """Record screen frames"""
        try:
            monitor = self.sct.monitors[0]  # Get the primary monitor
            while self.recording:
                # Capture screen
                screenshot = self.sct.grab(monitor)
                # Convert to numpy array
                frame = np.array(screenshot)
                # Convert from BGRA to BGR
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                self.frames.append(frame)
                time.sleep(1/30)  # Target 30 FPS
        except Exception as e:
            print(f"Error recording screen: {e}")
            self.recording = False
            
    def _record_audio(self):
        """Record audio"""
        try:
            with sd.InputStream(channels=2, 
                              samplerate=self.sample_rate,
                              callback=self._audio_callback):
                while self.recording:
                    time.sleep(0.1)
        except Exception as e:
            print(f"Error recording audio: {e}")
            
    def _audio_callback(self, indata, frames, time, status):
        """Callback for audio recording"""
        if status:
            print(status)
        if self.recording:
            self.audio_frames.append(indata.copy())
            
    def _save_recording(self):
        """Save the recording with audio"""
        try:
            if not self.frames:
                return None, None
                
            # Create output directory
            output_dir = Path("recordings")
            output_dir.mkdir(exist_ok=True)
            
            # Generate output paths
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            temp_video = output_dir / f"temp_{timestamp}.mp4"
            temp_audio = output_dir / f"temp_{timestamp}.wav"
            final_video = output_dir / f"recording_{timestamp}.mp4"
            
            # Save video
            height, width = self.frames[0].shape[:2]
            video_writer = cv2.VideoWriter(
                str(temp_video),
                cv2.VideoWriter_fourcc(*'mp4v'),
                30,
                (width, height)
            )
            
            for frame in self.frames:
                video_writer.write(frame)
            video_writer.release()
            
            # Save audio
            if self.audio_frames:
                audio_data = np.concatenate(self.audio_frames, axis=0)
                sf.write(str(temp_audio), audio_data, self.sample_rate)
                
                # Combine video and audio
                command = [
                    'ffmpeg', '-y',
                    '-i', str(temp_video),
                    '-i', str(temp_audio),
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    str(final_video)
                ]
                subprocess.run(command, check=True, capture_output=True)
                
                # Clean up temporary files
                temp_video.unlink()
                temp_audio.unlink()
            else:
                # If no audio, just rename the video file
                temp_video.rename(final_video)
                
            return str(final_video), None
            
        except Exception as e:
            print(f"Error saving recording: {e}")
            return None, None


Yes, we can use `python-mss` for screen recording and sounddevice for audio recording, which is more reliable on macOS. Here's a simpler and more reliable implementation:

1. First, install the required packages:
```bash
pip install mss sounddevice soundfile numpy opencv-python
```

2. Here's the simplified recorder implementation:

import mss
import sounddevice as sd
import soundfile as sf
import numpy as np
import cv2
import time
import threading
from pathlib import Path
import subprocess

class ScreenRecorder:
    def __init__(self):
        self.recording = False
        self.frames = []
        self.audio_frames = []
        self.sct = mss.mss()
        self.sample_rate = 44100  # Audio sample rate
        
    def start_recording(self):
        """Start both screen and audio recording"""
        self.recording = True
        self.frames = []
        self.audio_frames = []
        
        # Start screen recording thread
        screen_thread = threading.Thread(target=self._record_screen)
        screen_thread.daemon = True
        screen_thread.start()
        
        # Start audio recording thread
        audio_thread = threading.Thread(target=self._record_audio)
        audio_thread.daemon = True
        audio_thread.start()
        
    def stop_recording(self):
        """Stop recording and save the video"""
        self.recording = False
        return self._save_recording()
        
    def _record_screen(self):
        """Record screen frames"""
        try:
            monitor = self.sct.monitors[0]  # Get the primary monitor
            while self.recording:
                # Capture screen
                screenshot = self.sct.grab(monitor)
                # Convert to numpy array
                frame = np.array(screenshot)
                # Convert from BGRA to BGR
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                self.frames.append(frame)
                time.sleep(1/30)  # Target 30 FPS
        except Exception as e:
            print(f"Error recording screen: {e}")
            self.recording = False
            
    def _record_audio(self):
        """Record audio"""
        try:
            with sd.InputStream(channels=2, 
                              samplerate=self.sample_rate,
                              callback=self._audio_callback):
                while self.recording:
                    time.sleep(0.1)
        except Exception as e:
            print(f"Error recording audio: {e}")
            
    def _audio_callback(self, indata, frames, time, status):
        """Callback for audio recording"""
        if status:
            print(status)
        if self.recording:
            self.audio_frames.append(indata.copy())
            
    def _save_recording(self):
        """Save the recording with audio"""
        try:
            if not self.frames:
                return None, None
                
            # Create output directory
            output_dir = Path("recordings")
            output_dir.mkdir(exist_ok=True)
            
            # Generate output paths
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            temp_video = output_dir / f"temp_{timestamp}.mp4"
            temp_audio = output_dir / f"temp_{timestamp}.wav"
            final_video = output_dir / f"recording_{timestamp}.mp4"
            
            # Save video
            height, width = self.frames[0].shape[:2]
            video_writer = cv2.VideoWriter(
                str(temp_video),
                cv2.VideoWriter_fourcc(*'mp4v'),
                30,
                (width, height)
            )
            
            for frame in self.frames:
                video_writer.write(frame)
            video_writer.release()
            
            # Save audio
            if self.audio_frames:
                audio_data = np.concatenate(self.audio_frames, axis=0)
                sf.write(str(temp_audio), audio_data, self.sample_rate)
                
                # Combine video and audio
                command = [
                    'ffmpeg', '-y',
                    '-i', str(temp_video),
                    '-i', str(temp_audio),
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    str(final_video)
                ]
                subprocess.run(command, check=True, capture_output=True)
                
                # Clean up temporary files
                temp_video.unlink()
                temp_audio.unlink()
            else:
                # If no audio, just rename the video file
                temp_video.rename(final_video)
                
            return str(final_video), None
            
        except Exception as e:
            print(f"Error saving recording: {e}")
            return None, None

This implementation:
1. Uses `mss` for screen capture, which is more reliable on macOS
2. Uses `sounddevice` for audio recording
3. Simplifies the overall recording process
4. Handles file saving with proper cleanup

To use this, you would need to modify your CrossPlatformScreenRecorder to use this new implementation:<antArtifact identifier="cross-platform-recorder" type="application/vnd.ant.code" language="python" title="Updated Cross-Platform Recorder">
class CrossPlatformScreenRecorder:
    def __init__(self, app_reference):
        self.app = app_reference
        self.recorder = ScreenRecorder()
        
    def start_recording(self):
        """Start recording"""
        try:
            self.recorder.start_recording()
            print("Recording started")
        except Exception as e:
            print(f"Error starting recording: {e}")
            raise
            
    def stop_recording(self):
        """Stop recording"""
        try:
            video_path, _ = self.recorder.stop_recording()
            if video_path:
                print(f"Recording saved to: {video_path}")
                return video_path, None
            return None, None
        except Exception as e:
            print(f"Error stopping recording: {e}")
            return None, None

Key benefits of this approach:
1. More reliable screen capture
2. Better audio recording
3. Simpler implementation
4. Less platform-specific code
5. Better performance

Make sure you have ffmpeg installed for the audio-video merging:
```bash
brew install ffmpeg
```

Would you like me to explain any part in detail or help with implementation?

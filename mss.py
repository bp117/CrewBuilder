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
        self.sample_rate = 44100
        self.fps = 30.0
        self.frame_time = 1/self.fps
        
    def start_recording(self):
        """Start both screen and audio recording"""
        try:
            print("Initializing recording...")
            self.recording = True
            self.frames = []
            self.audio_frames = []
            
            # Start audio recording
            self.audio_thread = threading.Thread(target=self._record_audio)
            self.audio_thread.daemon = True
            self.audio_thread.start()
            
            # Start screen recording
            self.screen_thread = threading.Thread(target=self._record_screen)
            self.screen_thread.daemon = True
            self.screen_thread.start()
            
            print("Recording started")
            
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.recording = False
            raise
        
    def stop_recording(self):
        """Stop recording and save the video"""
        print("Stopping recording...")
        self.recording = False
        
        # Wait for threads to finish
        if hasattr(self, 'screen_thread'):
            self.screen_thread.join(timeout=2.0)
        if hasattr(self, 'audio_thread'):
            self.audio_thread.join(timeout=2.0)
            
        return self._save_recording()
        
    def _record_screen(self):
        """Record screen frames"""
        try:
            # Get the primary monitor
            monitor = self.sct.monitors[0]
            
            last_frame_time = time.time()
            frame_count = 0
            
            while self.recording:
                current_time = time.time()
                elapsed = current_time - last_frame_time
                
                if elapsed >= self.frame_time:
                    # Capture screen
                    screenshot = self.sct.grab(monitor)
                    frame = np.array(screenshot)
                    
                    # Convert from BGRA to BGR
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                    self.frames.append(frame)
                    
                    frame_count += 1
                    last_frame_time = current_time
                    
                    if frame_count % 30 == 0:  # Log every 30 frames
                        print(f"Captured {frame_count} frames")
                else:
                    # Sleep for a short time to prevent CPU overuse
                    time.sleep(max(0, self.frame_time - elapsed))
                    
        except Exception as e:
            print(f"Error in screen recording: {e}")
            self.recording = False
            
    def _record_audio(self):
        """Record audio"""
        try:
            # Configure audio stream
            stream = sd.InputStream(
                channels=2,
                samplerate=self.sample_rate,
                blocksize=int(self.sample_rate * self.frame_time),  # Match video frame time
                callback=self._audio_callback
            )
            
            print("Starting audio stream...")
            with stream:
                while self.recording:
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"Error in audio recording: {e}")
            
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for audio recording"""
        if status:
            print(f"Audio status: {status}")
        if self.recording:
            self.audio_frames.append(indata.copy())
            
    def _save_recording(self):
        """Save the recording with audio"""
        try:
            if not self.frames:
                print("No frames captured!")
                return None, None
                
            print(f"Saving recording... ({len(self.frames)} frames, {len(self.audio_frames)} audio chunks)")
                
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
                self.fps,
                (width, height)
            )
            
            for frame in self.frames:
                video_writer.write(frame)
            video_writer.release()
            
            print("Video saved temporarily")
            
            # Save audio if we have any
            have_audio = False
            if self.audio_frames:
                try:
                    audio_data = np.concatenate(self.audio_frames, axis=0)
                    sf.write(str(temp_audio), audio_data, self.sample_rate)
                    have_audio = True
                    print("Audio saved temporarily")
                except Exception as e:
                    print(f"Error saving audio: {e}")
            
            # Combine video and audio if we have both
            if have_audio:
                try:
                    command = [
                        'ffmpeg', '-y',
                        '-i', str(temp_video),
                        '-i', str(temp_audio),
                        '-c:v', 'copy',
                        '-c:a', 'aac',
                        str(final_video)
                    ]
                    subprocess.run(command, check=True, capture_output=True)
                    print("Video and audio combined")
                except Exception as e:
                    print(f"Error combining video and audio: {e}")
                    # If combining fails, just use the video
                    temp_video.rename(final_video)
            else:
                # If no audio, just rename the video file
                temp_video.rename(final_video)
            
            # Cleanup
            try:
                if temp_video.exists():
                    temp_video.unlink()
                if temp_audio.exists():
                    temp_audio.unlink()
            except Exception as e:
                print(f"Error cleaning up temporary files: {e}")
            
            print(f"Recording saved to: {final_video}")
            return str(final_video), None
            
        except Exception as e:
            print(f"Error saving recording: {e}")
            return None, None

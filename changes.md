class CrossPlatformScreenRecorder:
    """Main screen recorder class that coordinates all recording functionality"""
    def __init__(self, app_reference):
        self.app = app_reference
        self.recording = False
        self.frames = []
        self.frame_times = []
        self.start_time = None
        self.audio_enabled = not platform.system() == 'Darwin'  # Disable audio on macOS
        
        # Initialize screen recorder
        if platform.system() == 'Windows':
            self.screen_recorder = WindowsScreenRecorder()
        elif platform.system() == 'Darwin':
            self.screen_recorder = MacScreenRecorder()
        else:
            raise NotImplementedError(f"Platform {platform.system()} not supported")
            
        # Initialize audio recorder only if enabled
        if self.audio_enabled:
            try:
                self.audio_recorder = AudioRecorder()
            except Exception as e:
                print(f"Audio recording disabled due to error: {e}")
                self.audio_enabled = False
                self.audio_recorder = None
        else:
            self.audio_recorder = None
            
        # Initialize interaction recorder
        self.interaction_recorder = InteractionRecorder()
        
        # Create output directory
        self.output_dir = Path("recordings")
        self.output_dir.mkdir(exist_ok=True)

    def start_recording(self):
        """Start all recording processes"""
        try:
            self.recording = True
            self.frames = []
            self.frame_times = []
            self.start_time = time.time()
            
            # Start audio recording if enabled
            if self.audio_enabled and self.audio_recorder:
                try:
                    self.audio_recorder.start_recording()
                except Exception as e:
                    print(f"Audio recording failed to start: {e}")
                    self.audio_enabled = False
            
            # Start screen recording
            threading.Thread(target=self._record_screen, daemon=True).start()
            
            # Start interaction recording
            self.interaction_recorder.start_recording()
            
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.stop_recording()

    def stop_recording(self):
        """Stop all recording processes and save files"""
        if not self.recording:
            return None, None
            
        try:
            self.recording = False
            
            # Stop audio recording if enabled
            if self.audio_enabled and self.audio_recorder:
                try:
                    self.audio_recorder.stop_recording()
                except Exception as e:
                    print(f"Error stopping audio: {e}")
            
            # Stop interaction recording
            self.interaction_recorder.stop_recording()
            
            # Generate filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_path = self.output_dir / f"recording_{timestamp}.mp4"
            audio_path = self.output_dir / f"audio_{timestamp}.wav"
            interactions_path = self.output_dir / f"interactions_{timestamp}.json"
            
            # Save interactions
            self.interaction_recorder.save_interactions(interactions_path)
            
            # Save audio if enabled and available
            audio_saved = False
            if self.audio_enabled and self.audio_recorder:
                try:
                    audio_saved = self.audio_recorder.save_audio(audio_path)
                except Exception as e:
                    print(f"Error saving audio: {e}")
                    audio_saved = False
            
            # Save video with or without audio
            self._save_video_with_audio(video_path, audio_path if audio_saved else None)
            
            # Clean up audio file
            if audio_saved and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except:
                    pass
            
            return str(video_path), str(interactions_path)
            
        except Exception as e:
            print(f"Error stopping recording: {e}")
            return None, None

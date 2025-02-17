def start_recording(self):
        """Start recording mouse and keyboard interactions"""
        try:
            self.recording = True
            self.interactions = []
            self.mouse_positions = []
            
            # Initialize listeners without starting them
            self.mouse_listener = mouse.Listener(
                on_move=self._on_move,
                on_click=self._on_click,
                on_scroll=self._on_scroll
            )
            
            self.keyboard_listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )
            
            # Start listeners in separate threads with error handling
            def safe_start_mouse():
                try:
                    if self.mouse_listener and not self.mouse_listener.running:
                        self.mouse_listener.start()
                        print("Mouse listener started")
                except Exception as e:
                    print(f"Error starting mouse listener: {e}")
                    self.mouse_listener = None

            def safe_start_keyboard():
                try:
                    if self.keyboard_listener and not self.keyboard_listener.running:
                        self.keyboard_listener.start()
                        print("Keyboard listener started")
                except Exception as e:
                    print(f"Error starting keyboard listener: {e}")
                    self.keyboard_listener = None

            # Start listeners in separate threads
            mouse_thread = threading.Thread(target=safe_start_mouse)
            keyboard_thread = threading.Thread(target=safe_start_keyboard)
            
            mouse_thread.daemon = True
            keyboard_thread.daemon = True
            
            print("Starting interaction recording...")
            mouse_thread.start()
            keyboard_thread.start()
            
            # Wait for threads to complete initialization
            mouse_thread.join(timeout=1.0)
            keyboard_thread.join(timeout=1.0)
            
            if (not self.mouse_listener or not self.keyboard_listener):
                raise Exception("Failed to initialize listeners")
                
            print("Interaction recording initialized")
            
        except Exception as e:
            print(f"Error in interaction recording: {e}")
            self.recording = False
            self.stop_recording()  # Cleanup any partially initialized listeners
            raise
class SimpleMacInteractionRecorder:
    """Simplified macOS interaction recorder without pynput"""
    def __init__(self):
        self.recording = False
        self.interactions = []
        self.start_time = None
        
    def start_recording(self):
        """Start basic recording"""
        self.recording = True
        self.interactions = []
        self.start_time = datetime.now().isoformat()
        print("Simple interaction recording started")
        
    def stop_recording(self):
        """Stop recording"""
        self.recording = False
        end_time = datetime.now().isoformat()
        self.interactions.append({
            "timestamp": end_time,
            "type": "recording_end",
            "duration": "Recording completed"
        })
        print("Simple interaction recording stopped")
        
    def save_interactions(self, filename):
        """Save basic recording information"""
        try:
            data = {
                "recording_data": {
                    "start_time": self.start_time,
                    "end_time": datetime.now().isoformat(),
                    "platform": "macOS",
                    "os_version": platform.mac_ver()[0],
                    "note": "Basic recording only - interaction monitoring was disabled",
                    "interactions": self.interactions
                }
            }
            
            output_path = Path(filename)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error saving basic interactions: {e}")
            return False
class CrossPlatformScreenRecorder:
    def __init__(self, app_reference):
        self.app = app_reference
        self.recording = False
        self.frames = []
        self.frame_times = []
        self.start_time = None
        
        # Initialize screen recorder based on platform
        try:
            if platform.system() == 'Windows':
                self.screen_recorder = WindowsScreenRecorder()
                self.interaction_recorder = InteractionRecorder()
            elif platform.system() == 'Darwin':
                self.screen_recorder = MacScreenRecorder()
                try:
                    self.interaction_recorder = MacInteractionRecorder()
                except Exception as e:
                    print(f"Falling back to simple interaction recorder: {e}")
                    self.interaction_recorder = SimpleMacInteractionRecorder()
            else:
                raise NotImplementedError(f"Platform {platform.system()} not supported")
        except Exception as e:
            print(f"Error initializing recorder: {e}")
            raise
        
        # Create output directory
        self.output_dir = Path("recordings")
        self.output_dir.mkdir(exist_ok=True)

    def start_recording(self):
        """Start recording processes"""
        try:
            self.recording = True
            self.frames = []
            self.frame_times = []
            self.start_time = time.time()
            
            # Start interaction recording first
            try:
                self.interaction_recorder.start_recording()
            except Exception as e:
                print(f"Warning: Interaction recording failed: {e}")
                # Continue with screen recording even if interaction recording fails
            
            # Start screen recording
            threading.Thread(target=self._record_screen, daemon=True).start()
            
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.stop_recording()

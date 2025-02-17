import json
class InteractionAnalyzer:
    def __init__(self):
        self.workflow_steps = []
        
    def analyze_interactions(self, interactions_path):
        with open(interactions_path, 'r') as f:
            data = json.load(f)
            
        interactions = data["recording_data"]["interactions"]
        
        for interaction in interactions:
            if interaction["type"] == "click":
                element = interaction["element"]
                position = element.get("position", {"x": 0, "y": 0})  # Get position from element if available
                self.workflow_steps.append({
                    "type": "action",
                    "details": {
                        "action_type": "click",
                        "target": element.get("text", "Unknown"),
                        "position": position
                    }
                })
            elif interaction["type"] == "scroll":
                self.workflow_steps.append({
                    "type": "action",
                    "details": {
                        "action_type": "scroll",
                        "direction": interaction.get("direction", "unknown")
                    }
                })
                
        return {"steps": self.workflow_steps}
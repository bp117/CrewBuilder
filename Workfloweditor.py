import sys
import json
import math
from PyQt5.QtWidgets import (QApplication, QMainWindow, QSplitter, QTabWidget, 
                            QGraphicsView, QGraphicsScene, QGraphicsRectItem, 
                            QGraphicsTextItem, QGraphicsLineItem, QGraphicsPolygonItem,
                            QVBoxLayout, QHBoxLayout, QPushButton, QWidget, QMenu, 
                            QAction, QDialog, QLabel, QLineEdit, QTextEdit, QFileDialog, 
                            QMessageBox, QGraphicsItem, QTreeWidget, QTreeWidgetItem,
                            QPlainTextEdit)
from PyQt5.QtCore import Qt, pyqtSlot, QPointF, QRectF, QSize
from PyQt5.QtGui import QColor, QPen, QBrush, QPolygonF, QFont, QPainter, QSyntaxHighlighter, QTextCharFormat


class JsonSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for JSON."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#008000"))  # Green
        
        self.key_format = QTextCharFormat()
        self.key_format.setForeground(QColor("#0000FF"))  # Blue
        
        self.value_format = QTextCharFormat()
        self.value_format.setForeground(QColor("#B8860B"))  # Dark golden rod
        
        self.special_format = QTextCharFormat()
        self.special_format.setForeground(QColor("#FF0000"))  # Red
        
    def highlightBlock(self, text):
        # Simplified highlighting - not a full JSON parser
        in_quotes = False
        quote_start = 0
        in_key = False
        
        for i, char in enumerate(text):
            if char == '"':
                if i > 0 and text[i-1] == '\\':
                    continue
                
                if not in_quotes:
                    in_quotes = True
                    quote_start = i
                else:
                    in_quotes = False
                    # If followed by colon, it's a key
                    is_key = False
                    for j in range(i+1, len(text)):
                        if text[j].isspace():
                            continue
                        if text[j] == ':':
                            is_key = True
                        break
                    
                    if is_key:
                        self.setFormat(quote_start, i - quote_start + 1, self.key_format)
                    else:
                        self.setFormat(quote_start, i - quote_start + 1, self.string_format)
        
        # Highlight special values (true, false, null)
        for word, start in [(match, match.start()) for match in 
                           [(word, text.find(word)) for word in ["true", "false", "null"]]
                           if match[1] != -1]:
            # Ensure it's a full word
            if (start == 0 or not text[start-1].isalpha()) and \
               (start + len(word) == len(text) or not text[start + len(word)].isalpha()):
                self.setFormat(start, len(word), self.special_format)
        
        # Highlight numbers
        for i, char in enumerate(text):
            if char.isdigit():
                # Check if it's part of a number
                start = i
                while start > 0 and (text[start-1].isdigit() or text[start-1] == '.' or text[start-1] == '-'):
                    start -= 1
                
                end = i
                while end < len(text) - 1 and (text[end+1].isdigit() or text[end+1] == '.'):
                    end += 1
                
                # Ensure it's a full number
                if (start == 0 or not text[start-1].isalnum()) and \
                   (end == len(text) - 1 or not text[end+1].isalnum()):
                    self.setFormat(start, end - start + 1, self.value_format)


class JsonEditor(QPlainTextEdit):
    """Enhanced text editor for JSON with syntax highlighting."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Courier New", 10))
        self.highlighter = JsonSyntaxHighlighter(self.document())
        
    def set_json(self, data):
        """Set JSON data formatted with indentation."""
        if isinstance(data, str):
            try:
                parsed_data = json.loads(data)
                formatted_json = json.dumps(parsed_data, indent=2)
                self.setPlainText(formatted_json)
            except json.JSONDecodeError:
                self.setPlainText(data)
        else:
            formatted_json = json.dumps(data, indent=2)
            self.setPlainText(formatted_json)
            
    def get_json(self):
        """Get JSON data from editor."""
        try:
            return json.loads(self.toPlainText())
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "JSON Error", f"Invalid JSON: {str(e)}")
            return None


class NodeEditDialog(QDialog):
    """Dialog for adding or editing a node."""
    
    def __init__(self, parent=None, title="", description=""):
        super().__init__(parent)
        self.setWindowTitle("Edit Node")
        self.setMinimumSize(500, 300)
        
        layout = QVBoxLayout()
        
        # Title field
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("Title:"))
        self.title_edit = QLineEdit(title)
        title_layout.addWidget(self.title_edit)
        layout.addLayout(title_layout)
        
        # Description field
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(QLabel("Content:"))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlainText(description)
        desc_layout.addWidget(self.desc_edit)
        layout.addLayout(desc_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_data(self):
        """Return the dialog data."""
        return {
            "title": self.title_edit.text(),
            "content": self.desc_edit.toPlainText()
        }


class NodeItem(QGraphicsRectItem):
    """A node in the workflow graph."""
    
    def __init__(self, title, content="", x=0, y=0, width=180, height=80):
        super().__init__(0, 0, width, height)
        self.setPos(x, y)
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsMovable)
        
        # Basic node appearance
        self.setBrush(QBrush(QColor(230, 230, 250)))  # Light lavender color
        self.setPen(QPen(QColor(100, 100, 150), 2))
        
        # Title text
        self.title_item = QGraphicsTextItem(self)
        self.title_item.setPos(10, 5)
        self.title_item.setFont(QFont("Arial", 10, QFont.Bold))
        self.title_item.setTextWidth(width - 20)
        self.title_item.setPlainText(title)
        
        # Content text (shortened if needed)
        self.content_item = QGraphicsTextItem(self)
        self.content_item.setPos(10, 30)
        self.content_item.setFont(QFont("Arial", 9))
        self.content_item.setTextWidth(width - 20)
        
        # Limit text length for display
        displayed_content = content
        if len(content) > 100:
            displayed_content = content[:97] + "..."
        self.content_item.setPlainText(displayed_content)
        
        # Store data
        self.node_title = title
        self.node_content = content
        self.children = []
        self.parent_node = None
        self.arrows = []
        self.node_data = {}  # Store original data
        
    def set_data(self, title, content, data=None):
        """Update node data."""
        self.node_title = title
        self.node_content = content
        self.title_item.setPlainText(title)
        
        # Limit text length for display
        displayed_content = content
        if len(content) > 100:
            displayed_content = content[:97] + "..."
        self.content_item.setPlainText(displayed_content)
        
        if data:
            self.node_data = data
            
    def add_child(self, child_node):
        """Add a child node and create connection arrow."""
        self.children.append(child_node)
        child_node.parent_node = self
        
        # Create arrow
        arrow = ArrowItem(self, child_node)
        self.arrows.append(arrow)
        return arrow
    
    def remove_child(self, child_node):
        """Remove a child node and its arrow."""
        if child_node in self.children:
            self.children.remove(child_node)
            
            # Remove arrows
            for arrow in self.arrows[:]:
                if arrow.end_node == child_node:
                    self.arrows.remove(arrow)
                    scene = arrow.scene()
                    if scene:
                        scene.removeItem(arrow)
    
    def update_arrows(self):
        """Update positions of all connected arrows."""
        for arrow in self.arrows:
            arrow.update_position()
        
        # Update incoming arrows if this is a child node
        if self.parent_node:
            for arrow in self.parent_node.arrows:
                if arrow.end_node == self:
                    arrow.update_position()
                    
    def mouseReleaseEvent(self, event):
        """Handle mouse release event to update arrows."""
        super().mouseReleaseEvent(event)
        self.update_arrows()


class ArrowItem(QGraphicsLineItem):
    """An arrow connecting two nodes."""
    
    def __init__(self, start_node, end_node):
        super().__init__()
        self.start_node = start_node
        self.end_node = end_node
        self.setPen(QPen(QColor(100, 100, 150), 2))
        
        # Create arrowhead
        self.arrowhead = QGraphicsPolygonItem(self)
        self.arrowhead.setBrush(QBrush(QColor(100, 100, 150)))
        self.arrowhead.setPen(QPen(Qt.NoPen))
        
        self.update_position()
        
        # Add to the scene if nodes are already in a scene
        scene = start_node.scene()
        if scene:
            scene.addItem(self)
            
    def update_position(self):
        """Update the position and orientation of the arrow."""
        if not self.start_node or not self.end_node:
            return
            
        # Get the center bottom of start node and center top of end node
        start_rect = self.start_node.rect()
        end_rect = self.end_node.rect()
        
        start_pos = self.start_node.pos()
        end_pos = self.end_node.pos()
        
        start_point = QPointF(
            start_pos.x() + start_rect.width()/2,
            start_pos.y() + start_rect.height()
        )
        
        end_point = QPointF(
            end_pos.x() + end_rect.width()/2,
            end_pos.y()
        )
        
        # Set the line positions
        self.setLine(start_point.x(), start_point.y(), end_point.x(), end_point.y())
        
        # Update arrowhead
        arrowhead_size = 10
        angle = math.atan2(end_point.y() - start_point.y(), end_point.x() - start_point.x())
        arrowhead_angle = math.pi / 6  # 30 degrees
        
        # Calculate the arrowhead points
        p0 = QPointF(end_point)
        p1 = QPointF(
            end_point.x() - arrowhead_size * math.cos(angle - arrowhead_angle),
            end_point.y() - arrowhead_size * math.sin(angle - arrowhead_angle)
        )
        p2 = QPointF(
            end_point.x() - arrowhead_size * math.cos(angle + arrowhead_angle),
            end_point.y() - arrowhead_size * math.sin(angle + arrowhead_angle)
        )
        
        polygon = QPolygonF()
        polygon.append(p0)
        polygon.append(p1)
        polygon.append(p2)
        
        self.arrowhead.setPolygon(polygon)


class WorkflowGraphScene(QGraphicsScene):
    """Custom graphics scene for the workflow graph."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.nodes = []
        self.setSceneRect(0, 0, 2000, 2000)
        
    def add_node(self, title, content="", x=0, y=0, data=None):
        """Add a new node to the scene."""
        node = NodeItem(title, content, x, y)
        if data:
            node.node_data = data
        self.addItem(node)
        self.nodes.append(node)
        return node
        
    def remove_node(self, node):
        """Remove a node and its connections."""
        # Remove child relationships
        if node.parent_node:
            node.parent_node.remove_child(node)
            
        # Remove this node as parent from all children
        for child in node.children[:]:
            node.remove_child(child)
            
        # Remove the node from the scene
        self.removeItem(node)
        self.nodes.remove(node)
        
    def clear_all(self):
        """Clear all nodes and arrows."""
        super().clear()
        self.nodes = []


class WorkflowJsonEditor(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Workflow JSON Editor")
        self.resize(1200, 800)
        
        self.current_file = None
        self.json_data = {}
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface."""
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # Create a splitter for the main views
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Left side: JSON tree and text editor
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # Tab widget for tree and text views
        self.tab_widget = QTabWidget()
        
        # Tree view
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Key", "Value"])
        self.tree.setColumnWidth(0, 200)
        
        # JSON text editor
        self.json_editor = JsonEditor()
        
        self.tab_widget.addTab(self.tree, "Tree View")
        self.tab_widget.addTab(self.json_editor, "JSON View")
        
        left_layout.addWidget(self.tab_widget)
        left_widget.setLayout(left_layout)
        
        # Right side: Graph visualization
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        
        # Graphics view
        self.scene = WorkflowGraphScene()
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self.show_context_menu)
        
        right_layout.addWidget(self.view)
        right_widget.setLayout(right_layout)
        
        # Add widgets to splitter
        self.splitter.addWidget(left_widget)
        self.splitter.addWidget(right_widget)
        
        # Set splitter sizes
        self.splitter.setSizes([400, 800])
        
        main_layout.addWidget(self.splitter)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # File operations
        new_button = QPushButton("New")
        new_button.clicked.connect(self.new_file)
        load_button = QPushButton("Load")
        load_button.clicked.connect(self.load_file)
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_file)
        save_as_button = QPushButton("Save As")
        save_as_button.clicked.connect(self.save_file_as)
        
        # Node operations
        add_button = QPushButton("Add Activity")
        add_button.clicked.connect(self.add_activity)
        
        # Visualization control
        refresh_button = QPushButton("Refresh Visualization")
        refresh_button.clicked.connect(self.refresh_visualization)
        
        button_layout.addWidget(new_button)
        button_layout.addWidget(load_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(save_as_button)
        button_layout.addWidget(add_button)
        button_layout.addWidget(refresh_button)
        
        main_layout.addLayout(button_layout)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Connect tab change signals
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        # Connect tree item changed signals
        self.tree.itemChanged.connect(self.on_tree_item_changed)
    
    def on_tab_changed(self, index):
        """Handle tab change events."""
        if index == 0:  # Tree view
            # Update tree from JSON editor if needed
            try:
                json_data = self.json_editor.get_json()
                if json_data:
                    self.json_data = json_data
                    self.update_tree()
            except Exception as e:
                QMessageBox.warning(self, "Warning", f"Error updating tree view: {str(e)}")
        elif index == 1:  # JSON view
            # Update JSON editor from tree view if needed
            self.update_json_editor()
    
    def on_tree_item_changed(self, item, column):
        """Handle tree item change events."""
        # Update the JSON data based on tree changes
        self.update_json_from_tree()
        self.update_json_editor()
    
    def update_tree(self):
        """Update the tree widget from JSON data."""
        self.tree.clear()
        self.tree.setColumnCount(2)
        
        if not self.json_data:
            return
            
        # Helper function to add items recursively
        def add_items(parent_item, data):
            if isinstance(data, dict):
                for key, value in data.items():
                    item = QTreeWidgetItem(parent_item)
                    item.setText(0, str(key))
                    item.setFlags(item.flags() | Qt.ItemIsEditable)
                    
                    if isinstance(value, (dict, list)):
                        # Just show a placeholder for complex types
                        item.setText(1, f"[{type(value).__name__}]")
                        add_items(item, value)
                    else:
                        item.setText(1, str(value))
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
            elif isinstance(data, list):
                for i, value in enumerate(data):
                    item = QTreeWidgetItem(parent_item)
                    item.setText(0, str(i))
                    
                    if isinstance(value, (dict, list)):
                        # Just show a placeholder for complex types
                        item.setText(1, f"[{type(value).__name__}]")
                        add_items(item, value)
                    else:
                        item.setText(1, str(value))
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
        
        # Add root items
        add_items(self.tree.invisibleRootItem(), self.json_data)
        self.tree.expandAll()
    
    def update_json_from_tree(self):
        """Update JSON data from the tree widget."""
        # This is a complex operation and would need full implementation
        # For now, we're focusing on the visualization aspects
        pass
    
    def update_json_editor(self):
        """Update the JSON editor from the JSON data."""
        self.json_editor.set_json(self.json_data)
    
    def load_sample_workflow(self):
        """Load a sample workflow JSON."""
        sample_json = {
            "system_goal": "To create a screen recording application using Python.",
            "user_goal": "I want to test my screen recording application and see if it's working correctly.",
            "activities_for_goal": [
                1,
                2
            ],
            "activities": [
                {
                    "activity_name": "Start Screen Recording",
                    "activity_no": 1,
                    "activity_steps": [
                        {
                            "activity_step_no": 1,
                            "activity_step_rationale": "To initiate the screen recording process.",
                            "activity_step_type": "Click",
                            "activity_step_control": "Start Recording button",
                            "activity_step_desc": "The user clicks the 'Start Recording' button.",
                            "activity_screen_desc": "The application's main interface is visible, showing actions to start, stop, and configure the recording."
                        }
                    ]
                },
                {
                    "activity_name": "Stop Screen Recording",
                    "activity_no": 2,
                    "activity_steps": [
                        {
                            "activity_step_no": 1,
                            "activity_step_rationale": "To end the screen recording and save the file.",
                            "activity_step_type": "Click",
                            "activity_step_control": "Stop Recording button",
                            "activity_step_desc": "The user clicks the 'Stop Recording' button.",
                            "activity_screen_desc": "The application shows a message indicating that the recording has been completed."
                        }
                    ]
                }
            ]
        }
        
        self.json_data = sample_json
        self.update_tree()
        self.update_json_editor()
        self.visualize_workflow()
    
    def visualize_workflow(self):
        """Create a visual representation of the workflow JSON."""
        self.scene.clear_all()
        
        if not self.json_data or "activities" not in self.json_data:
            return
            
        activities = self.json_data.get("activities", [])
        
        # Create activity nodes
        activity_nodes = {}
        
        for i, activity in enumerate(activities):
            activity_name = activity.get("activity_name", f"Activity {i+1}")
            activity_desc = f"Activity #{activity.get('activity_no', i+1)}"
            
            # Position nodes in a row
            x = 100 + i * 400
            y = 50
            
            node = self.scene.add_node(activity_name, activity_desc, x, y, activity)
            activity_nodes[activity.get("activity_no", i+1)] = node
            
            # Add activity steps
            steps = activity.get("activity_steps", [])
            for j, step in enumerate(steps):
                step_no = step.get("activity_step_no", j+1)
                step_type = step.get("activity_step_type", "")
                step_desc = step.get("activity_step_desc", "")
                
                step_title = f"Step {step_no}: {step_type}"
                
                # Position step below the activity
                step_x = x
                step_y = y + 150 + j * 120
                
                step_node = self.scene.add_node(step_title, step_desc, step_x, step_y, step)
                
                # Connect activity to step
                arrow = node.add_child(step_node)
                self.scene.addItem(arrow)
        
        # Adjust view to see all items
        self.view.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)
    
    def refresh_visualization(self):
        """Refresh the workflow visualization."""
        # Update JSON data from the current view
        if self.tab_widget.currentIndex() == 0:
            # From tree view
            self.update_json_from_tree()
        else:
            # From JSON editor
            json_data = self.json_editor.get_json()
            if json_data:
                self.json_data = json_data
        
        # Refresh visualization
        self.visualize_workflow()
    
    @pyqtSlot()
    def new_file(self):
        """Create a new file."""
        self.scene.clear_all()
        self.json_data = {}
        self.current_file = None
        self.setWindowTitle("Workflow JSON Editor - New File")
        self.update_tree()
        self.update_json_editor()
    
    @pyqtSlot()
    def load_file(self):
        """Load JSON from a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open JSON File", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    data = json.load(file)
                
                self.scene.clear_all()
                self.json_data = data
                self.current_file = file_path
                self.setWindowTitle(f"Workflow JSON Editor - {file_path}")
                
                self.update_tree()
                self.update_json_editor()
                self.visualize_workflow()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")
    
    @pyqtSlot()
    def save_file(self):
        """Save JSON to the current file."""
        if self.current_file:
            self.save_to_file(self.current_file)
        else:
            self.save_file_as()
    
    @pyqtSlot()
    def save_file_as(self):
        """Save JSON to a new file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save JSON File", "", "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            self.save_to_file(file_path)
            self.current_file = file_path
            self.setWindowTitle(f"Workflow JSON Editor - {file_path}")
    
    def save_to_file(self, file_path):
        """Save the current JSON data to a file."""
        try:
            # Ensure we have the latest data
            if self.tab_widget.currentIndex() == 1:  # JSON view
                json_data = self.json_editor.get_json()
                if json_data:
                    self.json_data = json_data
            
            with open(file_path, 'w') as file:
                json.dump(self.json_data, file, indent=2)
            QMessageBox.information(self, "Success", "File saved successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
    
    @pyqtSlot()
    def add_activity(self):
        """Add a new activity to the workflow."""
        dialog = NodeEditDialog(self, "New Activity", "")
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            
            # Create new activity
            activity_no = len(self.json_data.get("activities", [])) + 1
            new_activity = {
                "activity_name": data["title"],
                "activity_no": activity_no,
                "activity_steps": []
            }
            
            # Add to JSON data
            if "activities" not in self.json_data:
                self.json_data["activities"] = []
            
            self.json_data["activities"].append(new_activity)
            
            # Update views
            self.update_tree()
            self.update_json_editor()
            self.visualize_workflow()
    
    @pyqtSlot()
    def add_step(self):
        """Add a step to the selected activity."""
        # Get selected activity
        selected_items = self.scene.selectedItems()
        selected_nodes = [item for item in selected_items if isinstance(item, NodeItem)]
        
        if not selected_nodes:
            QMessageBox.warning(self, "Warning", "No activity selected")
            return
        
        node = selected_nodes[0]
        
        # Check if it's an activity node
        if not node.node_data or "activity_name" not in node.node_data:
            QMessageBox.warning(self, "Warning", "Please select an activity node")
            return
        
        dialog = NodeEditDialog(self, "New Step", "")
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            
            # Create new step
            activity = node.node_data
            step_no = len(activity.get("activity_steps", [])) + 1
            
            new_step = {
                "activity_step_no": step_no,
                "activity_step_desc": data["content"],
                "activity_step_type": "Click",
                "activity_step_control": data["title"],
                "activity_step_rationale": "Step rationale"
            }
            
            # Add to activity
            if "activity_steps" not in activity:
                activity["activity_steps"] = []
            
            activity["activity_steps"].append(new_step)
            
            # Update views
            self.update_tree()
            self.update_json_editor()
            self.visualize_workflow()
    
    @pyqtSlot()
    def edit_node(self):
        """Edit the selected node."""
        selected_items = self.scene.selectedItems()
        selected_nodes = [item for item in selected_items if isinstance(item, NodeItem)]
        
        if not selected_nodes:
            QMessageBox.warning(self, "Warning", "No node selected")
            return
        
        node = selected_nodes[0]
        
        dialog = NodeEditDialog(self, node.node_title, node.node_content)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            node.set_data(data["title"], data["content"])
            
            # Update underlying data
            if "activity_name" in node.node_data:
                # It's an activity node
                node.node_data["activity_name"] = data["title"]
            elif "activity_step_desc" in node.node_data:
                # It's a step node
                node.node_data["activity_step_desc"] = data["content"]
                node.node_data["activity_step_control"] = data["title"]
            
            # Update views
            self.update_tree()
            self.update_json_editor()
    
    @pyqtSlot()
    def delete_node(self):
        """Delete the selected node."""
        selected_items = self.scene.selectedItems()
        selected_nodes = [item for item in selected_items if isinstance(item, NodeItem)]
        
        if not selected_nodes:
            QMessageBox.warning(self, "Warning", "No node selected")
            return
        
        node = selected_nodes[0]
        
        # Ask for confirmation
        if QMessageBox.question(
            self, "Confirm Deletion", 
            f"Delete {node.node_title}?",
            QMessageBox.Yes | QMessageBox.No
        ) == QMessageBox.No:
            return
            
        # Remove from JSON data
        # This would require more complex logic to update the JSON structure
        # For now, we just remove from visualization
        
        self.scene.remove_node(node)
    
    def show_context_menu(self, position):
        """Show context menu for graph items."""
        scene_pos = self.view.mapToScene(position)
        item = self.scene.itemAt(scene_pos, self.view.transform())
        
        if isinstance(item, NodeItem) or isinstance(item, QGraphicsTextItem) and isinstance(item.parentItem(), NodeItem):
            # If we clicked on a text item, get its parent node
            if isinstance(item, QGraphicsTextItem):
                item = item.parentItem()
                
            # Select the node
            item.setSelected(True)
            
            menu = QMenu()
            
            # Check if it's an activity node
            if "activity_name" in item.node_data:
                add_step_action = QAction("Add Step", self)
                add_step_action.triggered.connect(self.add_step)
                menu.addAction(add_step_action)
            
            edit_action = QAction("Edit", self)
            delete_action = QAction("Delete", self)
            
            edit_action.triggered.connect(self.edit_node)
            delete_action.triggered.connect(self.delete_node)
            
            menu.addAction(edit_action)
            menu.addAction(delete_action)
            
            menu.exec_(self.view.mapToGlobal(position))
        else:
            # Background context menu
            menu = QMenu()
            add_action = QAction("Add Activity", self)
            add_action.triggered.connect(self.add_activity)
            menu.addAction(add_action)
            
            menu.exec_(self.view.mapToGlobal(position))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    from PyQt5.QtGui import QPainter  # Adding this import for antialiasing
    window = WorkflowJsonEditor()
    window.load_sample_workflow()  # Load the sample workflow by default
    window.show()
    sys.exit(app.exec_())

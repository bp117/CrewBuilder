import os
import gradio as gr
import requests
from docling.document_converter import DocumentConverter
from markitdown import MarkItDown

class DocumentAnalyzer:
    def __init__(self):
        # Initialize API settings
        self.api_key = "AIzaSyBgCCcqKLTycx26si6WCZqTapu_MTS-r_M"#os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Please set GOOGLE_API_KEY environment variable")
        
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-001:generateContent"
        
    def analyze_document(self, file_path, user_prompt):
        try:
            # Convert using DocLing
            converter = DocumentConverter()
            docling_result = converter.convert(file_path)
            docling_content = docling_result.document.export_to_markdown()
            
            # Convert using MarkItDown
            md = MarkItDown()
            markitdown_result = md.convert(file_path)
            markitdown_content = markitdown_result.text_content
            
            # Prepare headers for API requests
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            
            # Get analysis for DocLing output with user prompt
            docling_payload = {
                "contents": [{
                    "parts": [{
                        "text": f"""
                        System: You are a helpful assistant.
                        User: {user_prompt}
                        Content from DocLing conversion: {docling_content}
                        """
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1024,
                }
            }
            
            # Get analysis for MarkItDown output with user prompt
            markitdown_payload = {
                "contents": [{
                    "parts": [{
                        "text": f"""
                        System: You are a helpful assistant.
                        User: {user_prompt}
                        Content from MarkItDown conversion: {markitdown_content}
                        """
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1024,
                }
            }
            
            # Make API requests for both analyses
            docling_response = requests.post(
                self.api_url,
                headers=headers,
                json=docling_payload
            )
            
            markitdown_response = requests.post(
                self.api_url,
                headers=headers,
                json=markitdown_payload
            )
            
            # Process responses
            if docling_response.status_code == 200:
                docling_analysis = docling_response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                docling_analysis = f"API Error: {docling_response.status_code}"
            
            if markitdown_response.status_code == 200:
                markitdown_analysis = markitdown_response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                markitdown_analysis = f"API Error: {markitdown_response.status_code}"
            
            # Combine analyses for comparison
            combined_analysis = f"""
            Analysis based on DocLing conversion:
            {docling_analysis}
            
            Analysis based on MarkItDown conversion:
            {markitdown_analysis}
            """
            
            return (
                docling_content,
                markitdown_content,
                docling_analysis,
                markitdown_analysis,
                combined_analysis
            )
                    
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            return (error_msg, error_msg, error_msg, error_msg, error_msg)

def create_gradio_interface():
    analyzer = DocumentAnalyzer()
    
    with gr.Blocks(title="Document Analysis Comparison") as app:
        gr.Markdown("## Document Analysis Comparison Tool")
        gr.Markdown("Upload an Excel file to compare different conversion methods.")
        
        with gr.Row():
            file_input = gr.File(
                label="Upload Excel File",
                file_types=[".xlsx", ".xls"],
                type="filepath"
            )
            prompt_input = gr.Textbox(
                label="Custom Analysis Prompt",
                placeholder="Ask a specific question about the document...",
                lines=3
            )
        
        with gr.Row():
            analyze_btn = gr.Button("Analyze Document", variant="primary")
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### DocLing Analysis")
                docling_output = gr.TextArea(
                    label="DocLing Conversion",
                    lines=10,
                    show_copy_button=True
                )
                docling_summary = gr.TextArea(
                    label="DocLing Summary",
                    lines=5,
                    show_copy_button=True
                )
            
            with gr.Column(scale=1):
                gr.Markdown("### MarkItDown Analysis")
                markitdown_output = gr.TextArea(
                    label="MarkItDown Conversion",
                    lines=10,
                    show_copy_button=True
                )
                markitdown_summary = gr.TextArea(
                    label="MarkItDown Summary",
                    lines=5,
                    show_copy_button=True
                )
        
        with gr.Row():
            custom_analysis_output = gr.TextArea(
                label="Custom Analysis",
                lines=5,
                show_copy_button=True
            )
        
        analyze_btn.click(
            fn=analyzer.analyze_document,
            inputs=[file_input, prompt_input],
            outputs=[
                docling_output,
                markitdown_output,
                docling_summary,
                markitdown_summary,
                custom_analysis_output
            ]
        )
    
    return app

if __name__ == "__main__":
    # Create and launch the Gradio interface
    app = create_gradio_interface()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
        debug=True
    )
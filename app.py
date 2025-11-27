

import streamlit as st
import os
from typing import List, Dict, Any

from pdf_processor import extract_text_from_pdf
from word_processor import extract_text_from_docx
from ai_parser import process_resume, check_ai_credits
from excel_exporter import export_to_excel, get_export_filename


# Page configuration
st.set_page_config(
    page_title="Resume Parser & Analyzer 2.0",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for dark theme with blue accents
st.markdown("""
<style>
    /* Main container styling */
    .stApp {
        background-color: #0f172a;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        border: 1px solid #334155;
    }
    
    .main-title {
        color: #f8fafc;
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .main-subtitle {
        color: #94a3b8;
        font-size: 0.875rem;
        margin-top: 0.25rem;
        font-family: 'JetBrains Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }
    
    /* Upload section styling */
    .upload-section {
        background: #1e293b;
        border: 2px dashed #334155;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .upload-section:hover {
        border-color: #3b82f6;
        background: #1e3a5f20;
    }
    
    /* Results table styling */
    .results-container {
        background: #1e293b;
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid #334155;
    }
    
    /* Status badges */
    .status-success {
        background: #064e3b;
        color: #6ee7b7;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    .status-error {
        background: #7f1d1d;
        color: #fca5a5;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    .status-ai {
        background: #1e3a8a;
        color: #93c5fd;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
    }
    
    /* Credit warning */
    .credit-warning {
        background: #78350f;
        border: 1px solid #fbbf24;
        border-radius: 8px;
        padding: 1rem;
        color: #fef3c7;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Custom button styling */
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
    }
    
    /* Download button */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    
    /* File uploader styling */
    .stFileUploader {
        background: #1e293b;
        border-radius: 12px;
    }
    
    .stFileUploader > div {
        background: transparent !important;
    }
    
    /* Dataframe styling */
    .stDataFrame {
        background: #1e293b;
        border-radius: 8px;
    }
    
    /* Text colors */
    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc !important;
    }
    
    p, span, label {
        color: #e2e8f0;
    }
    
    /* Metrics styling */
    .stMetric {
        background: #1e293b;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #334155;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    if 'results' not in st.session_state:
        st.session_state.results = []
    if 'processing' not in st.session_state:
        st.session_state.processing = False


def process_file(uploaded_file, api_key: str) -> Dict[str, Any]:
    """Process a single uploaded file and extract information."""
    result = {
        'filename': uploaded_file.name,
        'name': None,
        'email': None,
        'phone': None,
        'ai_used': False,
        'error': None,
        'status': 'processing'
    }
    
    try:
        # Read file bytes
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)  # Reset file pointer
        
        # Extract text based on file type
        if uploaded_file.name.lower().endswith('.pdf'):
            text = extract_text_from_pdf(file_bytes)
        elif uploaded_file.name.lower().endswith('.docx'):
            text = extract_text_from_docx(file_bytes)
        else:
            result['error'] = 'Unsupported file format'
            result['status'] = 'error'
            return result
        
        if not text.strip():
            result['error'] = 'No text could be extracted'
            result['status'] = 'error'
            return result
        
        # Process with regex and AI fallback
        extraction = process_resume(text, api_key)
        
        result['name'] = extraction.get('name')
        result['email'] = extraction.get('email')
        result['phone'] = extraction.get('phone')
        result['ai_used'] = extraction.get('ai_used', False)
        result['error'] = extraction.get('error')
        
        # Determine status
        if result['error'] and 'credit' in result['error'].lower():
            result['status'] = 'credit_error'
        elif result['name'] or result['email'] or result['phone']:
            result['status'] = 'success'
        else:
            result['status'] = 'partial'
            
    except Exception as e:
        result['error'] = str(e)
        result['status'] = 'error'
    
    return result


def render_header():
    """Render the application header."""
    st.markdown("""
    <div class="main-header">
        <h1 class="main-title">📄 Resume Parser & Analyzer 2.0</h1>
        <p class="main-subtitle">Extract contact details from resumes</p>
    </div>
    """, unsafe_allow_html=True)


def render_results_table(results: List[Dict[str, Any]]):
    """Render the results table with styling."""
    if not results:
        st.info("No files processed yet. Upload resumes to see results here.")
        return
    
    # Create displayable data
    table_data = []
    for r in results:
        status_badge = ""
        if r['status'] == 'success':
            status_badge = "✅"
        elif r['status'] == 'error' or r['status'] == 'credit_error':
            status_badge = "❌"
        else:
            status_badge = "⚠️"
        
        ai_badge = " 🤖" if r.get('ai_used') else ""
        
        table_data.append({
            "Status": status_badge,
            "Name": r.get('name') or "Not found",
            "Email": r.get('email') or "Not found",
            "Phone": r.get('phone') or "Not found",
            "File": r.get('filename', 'Unknown'),
            "AI": "Yes" if r.get('ai_used') else "No",
            "Error": r.get('error') or ""
        })
    
    # Display as dataframe
    import pandas as pd
    df = pd.DataFrame(table_data)
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn("", width="small"),
            "Name": st.column_config.TextColumn("Name", width="medium"),
            "Email": st.column_config.TextColumn("Email", width="medium"),
            "Phone": st.column_config.TextColumn("Phone", width="medium"),
            "File": st.column_config.TextColumn("File Name", width="medium"),
            "AI": st.column_config.TextColumn("AI Used", width="small"),
            "Error": st.column_config.TextColumn("Error", width="medium"),
        }
    )


def main():
    """Main application entry point."""
    initialize_session_state()
    
    # Render header
    render_header()
    
    # Get API key from environment
    api_key = os.environ.get('CLAUDE_SONNET_API_KEY', '')
    
    # Check AI credits status
    has_credits = True
    credit_error = None
    if api_key:
        has_credits, credit_error = check_ai_credits(api_key)
    
    # Layout
    col1, col2 = st.columns([2, 1])
    
    with col2:
        # Stats/Info panel
        st.markdown("###Processing Status")
        
        total = len(st.session_state.results)
        successful = sum(1 for r in st.session_state.results if r['status'] == 'success')
        ai_used = sum(1 for r in st.session_state.results if r.get('ai_used'))
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("Total", total)
        with col_b:
            st.metric("Success", successful)
        with col_c:
            st.metric("AI Used", ai_used)
        
        # Credit warning
        if not api_key:
            st.warning("⚠️ No OpenRouter API key configured. AI fallback is disabled.")
        elif not has_credits:
            st.error(f"🚫 {credit_error or 'AI credits unavailable'}")
    
    with col1:
        # File uploader
        st.markdown("### 📁 Upload Resumes")
        
        uploaded_files = st.file_uploader(
            "Drag and drop PDF or DOCX files here",
            type=['pdf', 'docx'],
            accept_multiple_files=True,
            help="Limit 200MB per file • PDF, DOCX formats supported"
        )
        
        # Process button
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
        
        with col_btn1:
            process_btn = st.button(
                "🚀 Extract Data",
                disabled=not uploaded_files,
                use_container_width=True
            )
        
        with col_btn2:
            if st.button("🗑️ Clear Results", use_container_width=True):
                st.session_state.results = []
                st.rerun()
        
        # Process files when button clicked
        if process_btn and uploaded_files:
            progress_bar = st.progress(0, text="Processing files...")
            
            for idx, file in enumerate(uploaded_files):
                progress = (idx + 1) / len(uploaded_files)
                progress_bar.progress(progress, text=f"Processing {file.name}...")
                
                result = process_file(file, api_key)
                st.session_state.results.append(result)
            
            progress_bar.empty()
            st.success(f"✅ Processed {len(uploaded_files)} files!")
            st.rerun()
    
    # Results section
    st.markdown("---")
    st.markdown("### 📋 Extraction Results")
    
    # Action buttons
    if st.session_state.results:
        col_dl1, col_dl2 = st.columns([1, 4])
        
        with col_dl1:
            # Export to Excel
            excel_data = export_to_excel(st.session_state.results)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=get_export_filename(),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    # Render results table
    render_results_table(st.session_state.results)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #64748b; font-size: 0.75rem;'>"
        "Resume Parser & Analyzer • Built with Streamlit"
        "</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

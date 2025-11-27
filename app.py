import streamlit as st
import os
from typing import List, Dict, Any

from pdf_processor import extract_text_from_pdf, convert_pdf_to_images
from word_processor import extract_text_from_docx
from ai_parser import process_resume, check_ai_credits
from excel_exporter import export_to_excel, get_export_filename


st.set_page_config(
    page_title="Resume Parser & Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {
        background-color: #ffffff;
    }
    
    .main-header {
        background: #ffffff;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        border: 1px solid #e0e0e0;
    }
    
    .main-title {
        color: #000000;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 0;
    }
    
    .main-subtitle {
        color: #666666;
        font-size: 0.75rem;
        margin-top: 0.25rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .upload-section {
        background: #fafafa;
        border: 1px dashed #cccccc;
        border-radius: 8px;
        padding: 1.5rem;
        text-align: center;
    }
    
    .upload-section:hover {
        border-color: #999999;
    }
    
    .results-container {
        background: #fafafa;
        border-radius: 8px;
        padding: 1rem;
        border: 1px solid #e0e0e0;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .stButton > button {
        background: #333333;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1.5rem;
        font-weight: 500;
    }
    
    .stButton > button:hover {
        background: #000000;
    }
    
    .stDownloadButton > button {
        background: #333333;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 500;
    }
    
    .stDownloadButton > button:hover {
        background: #000000;
    }
    
    .stFileUploader {
        background: #fafafa;
        border-radius: 8px;
    }
    
    .stFileUploader > div {
        background: transparent !important;
    }
    
    .stDataFrame {
        background: #ffffff;
        border-radius: 6px;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #000000 !important;
    }
    
    p, span, label {
        color: #333333;
    }
    
    .stMetric {
        background: #fafafa;
        padding: 1rem;
        border-radius: 6px;
        border: 1px solid #e0e0e0;
    }
    
    .stMetric label {
        color: #666666 !important;
    }
    
    .stMetric [data-testid="stMetricValue"] {
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    if 'results' not in st.session_state:
        st.session_state.results = []
    if 'processing' not in st.session_state:
        st.session_state.processing = False


def process_file(uploaded_file) -> Dict[str, Any]:
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
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)
        
        if uploaded_file.name.lower().endswith('.pdf'):
            text, is_image_based = extract_text_from_pdf(file_bytes)
            
            images = None
            if is_image_based:
                images = convert_pdf_to_images(file_bytes, max_pages=1)
            
            extraction = process_resume(text, is_image_based, images)
            
        elif uploaded_file.name.lower().endswith('.docx'):
            text = extract_text_from_docx(file_bytes)
            extraction = process_resume(text, is_image_based=False, images=None)
        else:
            result['error'] = 'Unsupported file format'
            result['status'] = 'error'
            return result
        
        result['name'] = extraction.get('name')
        result['email'] = extraction.get('email')
        result['phone'] = extraction.get('phone')
        result['ai_used'] = extraction.get('ai_used', False)
        result['error'] = extraction.get('error')
        
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
        <p class="main-title">Resume Parser & Analyzer</p>
        <p class="main-subtitle">Extract contact details from resumes</p>
    </div>
    """, unsafe_allow_html=True)


def render_results_table(results: List[Dict[str, Any]]):
    """Render the results table with styling."""
    if not results:
        st.info("No files processed yet. Upload resumes to see results here.")
        return
    
    table_data = []
    for r in results:
        status_badge = ""
        if r['status'] == 'success':
            status_badge = "✅"
        elif r['status'] == 'error' or r['status'] == 'credit_error':
            status_badge = "❌"
        else:
            status_badge = "⚠️"
        
        table_data.append({
            "Status": status_badge,
            "Name": r.get('name') or "Not found",
            "Email": r.get('email') or "Not found",
            "Phone": r.get('phone') or "Not found",
            "File": r.get('filename', 'Unknown'),
            "AI": "Yes" if r.get('ai_used') else "No",
            "Error": r.get('error') or ""
        })
    
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
    
    render_header()
    
    has_credits, credit_error = check_ai_credits()
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.markdown("### Processing Status")
        
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
        
        if not has_credits:
            st.warning(f"⚠️ {credit_error or 'AI features unavailable'}")
    
    with col1:
        st.markdown("### Upload Resumes")
        
        uploaded_files = st.file_uploader(
            "Drag and drop PDF or DOCX files here",
            type=['pdf', 'docx'],
            accept_multiple_files=True,
            help="Limit 200MB per file - PDF, DOCX formats supported"
        )
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
        
        with col_btn1:
            process_btn = st.button(
                "Extract Data",
                disabled=not uploaded_files,
                use_container_width=True
            )
        
        with col_btn2:
            if st.button("Clear Results", use_container_width=True):
                st.session_state.results = []
                st.rerun()
        
        if process_btn and uploaded_files:
            progress_bar = st.progress(0, text="Processing files...")
            
            for idx, file in enumerate(uploaded_files):
                progress = (idx + 1) / len(uploaded_files)
                progress_bar.progress(progress, text=f"Processing {file.name}...")
                
                result = process_file(file)
                st.session_state.results.append(result)
            
            progress_bar.empty()
            st.success(f"Processed {len(uploaded_files)} files!")
            st.rerun()
    
    st.markdown("---")
    st.markdown("### Extraction Results")
    
    if st.session_state.results:
        col_dl1, col_dl2 = st.columns([1, 4])
        
        with col_dl1:
            excel_data = export_to_excel(st.session_state.results)
            st.download_button(
                label="Download Excel",
                data=excel_data,
                file_name=get_export_filename(),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    render_results_table(st.session_state.results)
    
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #999999; font-size: 0.75rem;'>"
        "Resume Parser & Analyzer"
        "</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()

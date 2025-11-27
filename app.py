import streamlit as st
import os
from typing import List, Dict, Any
import time
import html

from pdf_processor import extract_text_from_pdf
from word_processor import extract_text_from_docx
from ai_parser import process_resume, check_ai_credits
from excel_exporter import export_to_excel, get_export_filename
from extraction_logger import extraction_logger


st.set_page_config(
    page_title="Resume Parser & Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0f172a;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .main-title {
        color: #f8fafc;
        font-size: 1.75rem;
        font-weight: 600;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .subtitle {
        color: #fbbf24;
        font-size: 1.5rem;
        font-weight: 700;
        margin-top: 0.5rem;
    }
    
    .upload-label {
        color: #94a3b8;
        font-size: 0.875rem;
        margin-bottom: 0.5rem;
    }

    .stFileUploader {
        background: #1e293b;
        border-radius: 8px;
    }
    
    .stFileUploader > div {
        background: transparent !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
    }
    
    .stDownloadButton > button {
        background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #f8fafc !important;
    }
    
    p, span, label {
        color: #e2e8f0;
    }
    
    .stMetric {
        background: #1e293b;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    
    .stDataFrame {
        background: #1e293b;
        border-radius: 8px;
    }
    
    .file-status-success {
        background: #064e3b;
        color: #6ee7b7;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        margin: 0.25rem 0;
        font-size: 0.875rem;
    }
    
    .file-status-error {
        background: #7f1d1d;
        color: #fca5a5;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        margin: 0.25rem 0;
        font-size: 0.875rem;
    }
    
    .file-status-partial {
        background: #78350f;
        color: #fbbf24;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        margin: 0.25rem 0;
        font-size: 0.875rem;
    }
    
    .file-status-processing {
        background: #1e3a5f;
        color: #93c5fd;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        margin: 0.25rem 0;
        font-size: 0.875rem;
    }
    
    .preview-box {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem;
        max-height: 300px;
        overflow-y: auto;
        font-family: monospace;
        font-size: 0.75rem;
        color: #94a3b8;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    
    .log-box {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 1rem;
        max-height: 400px;
        overflow-y: auto;
        font-family: monospace;
        font-size: 0.75rem;
        color: #94a3b8;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    if 'results' not in st.session_state:
        st.session_state.results = []
    if 'file_previews' not in st.session_state:
        st.session_state.file_previews = {}
    if 'batch_status' not in st.session_state:
        st.session_state.batch_status = []
    if 'extraction_logs' not in st.session_state:
        st.session_state.extraction_logs = []
    if 'uploaded_previews' not in st.session_state:
        st.session_state.uploaded_previews = {}


def get_file_type(filename: str) -> str:
    """Get file type from filename."""
    lower = filename.lower()
    if lower.endswith('.pdf'):
        return 'pdf'
    elif lower.endswith('.docx'):
        return 'docx'
    return 'unknown'


def extract_text(file_bytes: bytes, file_type: str) -> str:
    """Extract text from file based on type."""
    if file_type == 'pdf':
        return extract_text_from_pdf(file_bytes)
    elif file_type == 'docx':
        return extract_text_from_docx(file_bytes)
    else:
        raise Exception(f'Unsupported file format: {file_type}')


def preview_uploaded_file(uploaded_file) -> str:
    """Extract and preview text from an uploaded file before processing."""
    filename = uploaded_file.name
    file_type = get_file_type(filename)
    
    try:
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)
        text = extract_text(file_bytes, file_type)
        return text[:2000] if text else "No text could be extracted"
    except Exception as e:
        return f"Error extracting text: {str(e)}"


def process_file(uploaded_file, api_key: str, batch_status_list: list) -> Dict[str, Any]:
    filename = uploaded_file.name
    file_type = get_file_type(filename)
    
    batch_status_list.append({
        'filename': filename,
        'status': 'processing',
        'error': '',
        'message': 'Extracting text...'
    })
    
    result = {
        'filename': filename,
        'name': None,
        'email': None,
        'phone': None,
        'ai_used': False,
        'error': None,
        'status': 'processing',
        'confidence': {'name': 0.0, 'email': 0.0, 'phone': 0.0},
        'methods': {'name': 'none', 'email': 'none', 'phone': 'none'}
    }
    
    try:
        file_bytes = uploaded_file.read()
        uploaded_file.seek(0)
        
        extraction_logger.log_file_start(filename, file_type, len(file_bytes))
        
        text = extract_text(file_bytes, file_type)
        
        extraction_logger.log_text_extraction(filename, len(text), success=True)
        
        if not text.strip():
            result['error'] = 'No text could be extracted'
            result['status'] = 'error'
            batch_status_list[-1]['status'] = 'error'
            batch_status_list[-1]['error'] = result['error']
            batch_status_list[-1]['message'] = 'Failed to extract text'
            extraction_logger.log_text_extraction(filename, 0, success=False, error='No text extracted')
            return result
        
        st.session_state.file_previews[filename] = text[:2000]
        
        batch_status_list[-1]['message'] = 'Analyzing with AI...'
        
        extraction = process_resume(text, api_key)
        
        result['name'] = extraction.get('name')
        result['email'] = extraction.get('email')
        result['phone'] = extraction.get('phone')
        result['ai_used'] = extraction.get('ai_used', False)
        result['error'] = extraction.get('error')
        result['confidence'] = extraction.get('confidence', {'name': 0.0, 'email': 0.0, 'phone': 0.0})
        result['methods'] = extraction.get('methods', {'name': 'none', 'email': 'none', 'phone': 'none'})
        
        for field in ['name', 'email', 'phone']:
            extraction_logger.log_field_extraction(
                filename=filename,
                field=field,
                value=result.get(field),
                method=result['methods'].get(field, 'unknown'),
                confidence=result['confidence'].get(field, 0.0),
                success=result.get(field) is not None
            )
        
        if result['error'] and 'credit' in result['error'].lower():
            result['status'] = 'credit_error'
        elif result['name'] or result['email'] or result['phone']:
            result['status'] = 'success'
        else:
            result['status'] = 'partial'
        
        batch_status_list[-1]['status'] = result['status']
        batch_status_list[-1]['error'] = result.get('error', '')
        batch_status_list[-1]['message'] = 'Complete'
        
        extraction_logger.log_file_complete(filename, result)
            
    except Exception as e:
        result['error'] = str(e)
        result['status'] = 'error'
        batch_status_list[-1]['status'] = 'error'
        batch_status_list[-1]['error'] = str(e)
        batch_status_list[-1]['message'] = 'Failed'
        extraction_logger.log_file_complete(filename, result)
    
    return result


def render_header():
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<p class="main-title">📄 Resume Parser & Analyzer</p>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="linktal-logo" style="text-align: right; padding-top: 10px;">
            <svg width="40" height="40" viewBox="0 0 100 100" style="display: inline-block; vertical-align: middle;">
                <circle cx="50" cy="50" r="45" fill="#3b82f6"/>
                <text x="50" y="58" text-anchor="middle" fill="white" font-size="28" font-weight="bold">L</text>
            </svg>
            <span class="linktal-text" style="display: inline-block; vertical-align: middle;"></span>
        </div>
        <p class="processing-status" style="text-align: right;"></p>
        """, unsafe_allow_html=True)


def format_confidence(confidence: float) -> str:
    """Format confidence as percentage."""
    return f"{confidence * 100:.0f}%"


def render_batch_status():
    """Render batch processing status history."""
    if not st.session_state.batch_status:
        return
    
    with st.expander("📊Processing ", expanded=False):
        for status in st.session_state.batch_status[-30:]:
            safe_filename = html.escape(status.get('filename', 'Unknown'))
            status_type = status.get('status', 'unknown')
            error_msg = status.get('error', '')
            message = status.get('message', '')
            
            if status_type == 'success':
                st.markdown(f'<div class="file-status-success">✅ {safe_filename} - Extracted successfully</div>', 
                           unsafe_allow_html=True)
            elif status_type == 'error' or status_type == 'credit_error':
                safe_error = html.escape(error_msg) if error_msg else 'Unknown error'
                st.markdown(f'<div class="file-status-error">❌ {safe_filename} - {safe_error}</div>', 
                           unsafe_allow_html=True)
            elif status_type == 'processing':
                safe_msg = html.escape(message) if message else 'Processing...'
                st.markdown(f'<div class="file-status-processing">🔄 {safe_filename} - {safe_msg}</div>', 
                           unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="file-status-partial">⚠️ {safe_filename} - Partial extraction</div>', 
                           unsafe_allow_html=True)


def render_results_table(results: List[Dict[str, Any]]):
    if not results:
        st.info("No files processed yet. Upload resumes to see results here.")
        return
    
    import pandas as pd
    
    table_data = []
    for r in results:
        status_badge = ""
        if r['status'] == 'success':
            status_badge = "✅"
        elif r['status'] == 'error' or r['status'] == 'credit_error':
            status_badge = "❌"
        else:
            status_badge = "⚠️"
        
        confidence = r.get('confidence', {})
        
        name_conf = format_confidence(confidence.get('name', 0))
        email_conf = format_confidence(confidence.get('email', 0))
        phone_conf = format_confidence(confidence.get('phone', 0))
        
        row = {
            "Status": status_badge,
            "Name": r.get('name') or "Not found",
            "Name Conf.": name_conf if r.get('name') else "-",
            "Email": r.get('email') or "Not found",
            "Email Conf.": email_conf if r.get('email') else "-",
            "Phone": r.get('phone') or "Not found",
            "Phone Conf.": phone_conf if r.get('phone') else "-",
            "File": r.get('filename', 'Unknown'),
            "AI": "Yes" if r.get('ai_used') else "No",
        }
        
        if r.get('error'):
            row["Error"] = r.get('error')
        else:
            row["Error"] = ""
        
        table_data.append(row)
    
    df = pd.DataFrame(table_data)
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Status": st.column_config.TextColumn("", width="small"),
            "Name": st.column_config.TextColumn("Name", width="medium"),
            "Name Conf.": st.column_config.TextColumn("Conf.", width="small"),
            "Email": st.column_config.TextColumn("Email", width="medium"),
            "Email Conf.": st.column_config.TextColumn("Conf.", width="small"),
            "Phone": st.column_config.TextColumn("Phone", width="medium"),
            "Phone Conf.": st.column_config.TextColumn("Conf.", width="small"),
            "File": st.column_config.TextColumn("File Name", width="medium"),
            "AI": st.column_config.TextColumn("AI", width="small"),
            "Error": st.column_config.TextColumn("Error", width="medium"),
        }
    )


def render_upload_preview(uploaded_files):
    """Render preview of uploaded files before processing."""
    if not uploaded_files:
        return
    
    with st.expander("📝 Preview", expanded=True):
        file_names = [f.name for f in uploaded_files]
        selected = st.selectbox("Select file to preview", file_names, key="upload_preview_select")
        
        if selected:
            for f in uploaded_files:
                if f.name == selected:
                    if selected not in st.session_state.uploaded_previews:
                        preview_text = preview_uploaded_file(f)
                        st.session_state.uploaded_previews[selected] = preview_text
                    
                    preview = st.session_state.uploaded_previews.get(selected, "Loading...")
                    safe_preview = html.escape(preview)
                    st.markdown(f'<div class="preview-box">{safe_preview}</div>', unsafe_allow_html=True)
                    break


def render_file_preview():
    """Render file text previews after processing."""
    if not st.session_state.file_previews:
        return
    
    with st.expander("📝 Processed Resume Previews", expanded=False):
        file_options = list(st.session_state.file_previews.keys())
        if file_options:
            selected_file = st.selectbox(
                "Select processed file to preview",
                options=file_options,
                key="processed_preview_select"
            )
            
            if selected_file and selected_file in st.session_state.file_previews:
                preview_text = st.session_state.file_previews[selected_file]
                safe_preview = html.escape(preview_text)
                st.markdown(f'<div class="preview-box">{safe_preview}</div>', unsafe_allow_html=True)


def render_extraction_logs():
    """Render extraction logs for debugging."""
    extraction_logger.load_logs(st.session_state.extraction_logs)
    
    with st.expander("📋 Extraction Logs", expanded=False):
        col1, col2 = st.columns([3, 1])
        
        with col2:
            if st.button("Clear Logs", key="clear_logs"):
                extraction_logger.clear()
                st.session_state.extraction_logs = []
                st.rerun()
        
        summary = extraction_logger.get_summary()
        if summary['total_files'] > 0:
            st.markdown(f"""
            **Summary**: {summary['total_files']} files processed | 
            {summary['successful']} successful | 
            {summary['failed']} failed | 
            {summary['success_rate']:.1f}% success rate
            """)
        
        failed_logs = extraction_logger.get_failed_extractions()
        if failed_logs:
            st.markdown("**Failed Extractions:**")
            for log in failed_logs[-10:]:
                safe_filename = html.escape(log.get('filename', 'Unknown'))
                safe_error = html.escape(str(log.get('error', 'Unknown error')))
                st.markdown(f"- ❌ {safe_filename}: {safe_error}")
        
        logs_text = extraction_logger.format_logs_for_display()
        st.markdown(f'<div class="log-box">{logs_text}</div>', unsafe_allow_html=True)


def main():
    initialize_session_state()
    
    extraction_logger.load_logs(st.session_state.extraction_logs)
    
    render_header()
    
    api_key = os.environ.get('CLAUDE_SONNET_API_KEY', '')
    
    has_credits = True
    credit_error = None
    if api_key:
        has_credits, credit_error = check_ai_credits(api_key)
    
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<p class="upload-label">Upload as many you like!</p>', unsafe_allow_html=True)
        
        uploaded_files = st.file_uploader(
            "Drag and drop files here",
            type=['pdf', 'docx'],
            accept_multiple_files=True,
            help="Limit 200MB per file • PDF, DOCX",
            label_visibility="collapsed"
        )
        
        if uploaded_files:
            render_upload_preview(uploaded_files)
        
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
        
        with col_btn1:
            process_btn = st.button(
                "🚀 Extract Data",
                disabled=not uploaded_files,
                use_container_width=True
            )
        
        with col_btn2:
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.results = []
                st.session_state.file_previews = {}
                st.session_state.batch_status = []
                st.session_state.extraction_logs = []
                st.session_state.uploaded_previews = {}
                extraction_logger.clear()
                st.rerun()
        
        if process_btn and uploaded_files:
            progress_bar = st.progress(0, text="Starting batch processing...")
            status_container = st.container()
            
            total_files = len(uploaded_files)
            batch_status_list = []
            
            for idx, file in enumerate(uploaded_files):
                progress = idx / total_files
                progress_bar.progress(progress, text=f"Processing file {idx + 1} of {total_files}: {file.name}")
                
                with status_container:
                    st.markdown(f'<div class="file-status-processing">🔄 Processing: {file.name}</div>', 
                               unsafe_allow_html=True)
                
                result = process_file(file, api_key, batch_status_list)
                st.session_state.results.append(result)
                
                with status_container:
                    if result['status'] == 'success':
                        st.markdown(f'<div class="file-status-success">✅ Done: {file.name}</div>', 
                                   unsafe_allow_html=True)
                    elif result['status'] == 'error':
                        error_msg = html.escape(result.get('error', 'Unknown'))[:50]
                        st.markdown(f'<div class="file-status-error">❌ Failed: {file.name} - {error_msg}</div>', 
                                   unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="file-status-partial">⚠️ Partial: {file.name}</div>', 
                                   unsafe_allow_html=True)
            
            st.session_state.batch_status.extend(batch_status_list)
            st.session_state.extraction_logs = extraction_logger.get_logs_list()
            
            progress_bar.progress(1.0, text="Batch processing complete!")
            time.sleep(0.3)
            
            successful = sum(1 for s in batch_status_list if s['status'] == 'success')
            failed = sum(1 for s in batch_status_list if s['status'] in ['error', 'credit_error'])
            partial = total_files - successful - failed
            
            status_msg = f"✅ Processed {total_files} files: {successful} successful"
            if partial > 0:
                status_msg += f", {partial} partial"
            if failed > 0:
                status_msg += f", {failed} failed"
            
            st.success(status_msg)
            st.rerun()
    
    with col2:
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
        
        if not api_key:
            st.warning("⚠️ No API key configured. AI features disabled.")
        elif not has_credits:
            st.error(f"🚫 {credit_error or 'AI credits unavailable'}")
    
    st.markdown("---")
    st.markdown("### 📋 Extraction Results")
    
    if st.session_state.results:
        col_dl1, col_dl2, col_dl3 = st.columns([1, 1, 3])
        
        with col_dl1:
            excel_data = export_to_excel(st.session_state.results)
            st.download_button(
                label="📥 Download Excel",
                data=excel_data,
                file_name=get_export_filename(),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    render_results_table(st.session_state.results)
    
    render_batch_status()
    
    render_file_preview()
    
    render_extraction_logs()


if __name__ == "__main__":
    main()

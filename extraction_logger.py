"""
Extraction Logger Module
Provides detailed logging for debugging failed extraction cases.
Logs are stored in session state for persistence across Streamlit reruns.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
import html


class ExtractionLogger:
    """Logger for tracking extraction operations and debugging."""
    
    def __init__(self):
        self.logs: List[Dict[str, Any]] = []
    
    def log_extraction(self, filename: str, stage: str, details: Dict[str, Any], 
                       success: bool = True, error: Optional[str] = None):
        """Log an extraction operation."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'filename': filename,
            'stage': stage,
            'success': success,
            'details': details,
            'error': error
        }
        self.logs.append(entry)
    
    def log_file_start(self, filename: str, file_type: str, file_size: int):
        """Log the start of file processing."""
        self.log_extraction(
            filename=filename,
            stage='file_start',
            details={
                'file_type': file_type,
                'file_size': file_size
            }
        )
    
    def log_text_extraction(self, filename: str, text_length: int, 
                            success: bool = True, error: Optional[str] = None):
        """Log text extraction result."""
        self.log_extraction(
            filename=filename,
            stage='text_extraction',
            details={
                'text_length': text_length
            },
            success=success,
            error=error
        )
    
    def log_field_extraction(self, filename: str, field: str, value: Optional[str],
                             method: str, confidence: float = 1.0,
                             success: bool = True, error: Optional[str] = None):
        """Log individual field extraction."""
        self.log_extraction(
            filename=filename,
            stage=f'extract_{field}',
            details={
                'field': field,
                'value': value[:50] if value and len(value) > 50 else value,
                'method': method,
                'confidence': confidence
            },
            success=value is not None,
            error=error
        )
    
    def log_file_complete(self, filename: str, result: Dict[str, Any]):
        """Log file processing completion."""
        has_any_data = any([
            result.get('name'),
            result.get('email'),
            result.get('phone')
        ])
        
        self.log_extraction(
            filename=filename,
            stage='file_complete',
            details={
                'name_found': result.get('name') is not None,
                'email_found': result.get('email') is not None,
                'phone_found': result.get('phone') is not None,
                'ai_used': result.get('ai_used', False)
            },
            success=has_any_data,
            error=result.get('error')
        )
    
    def get_logs_for_file(self, filename: str) -> List[Dict[str, Any]]:
        """Get all logs for a specific file."""
        return [log for log in self.logs if log['filename'] == filename]
    
    def get_failed_extractions(self) -> List[Dict[str, Any]]:
        """Get logs where no data was extracted."""
        failed = []
        for log in self.logs:
            if log['stage'] == 'file_complete' and not log['success']:
                failed.append(log)
        return failed
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all extractions."""
        complete_logs = [log for log in self.logs if log['stage'] == 'file_complete']
        total = len(complete_logs)
        successful = len([log for log in complete_logs if log['success']])
        failed = total - successful
        
        return {
            'total_files': total,
            'successful': successful,
            'failed': failed,
            'success_rate': (successful / total * 100) if total > 0 else 0
        }
    
    def format_logs_for_display(self, filename: Optional[str] = None) -> str:
        """Format logs for display in UI with proper HTML escaping."""
        logs_to_show = self.get_logs_for_file(filename) if filename else self.logs
        
        if not logs_to_show:
            return "No logs available yet. Process some files to see extraction logs."
        
        output = []
        for log in logs_to_show[-50:]:
            status = "✅" if log['success'] else "❌"
            try:
                timestamp = log['timestamp'].split('T')[1].split('.')[0]
            except:
                timestamp = "00:00:00"
            
            safe_filename = html.escape(log.get('filename', 'Unknown'))
            safe_stage = html.escape(log.get('stage', 'Unknown'))
            
            line = f"[{timestamp}] {status} {safe_filename} - {safe_stage}"
            
            if log.get('error'):
                safe_error = html.escape(str(log['error']))
                line += f"\n    Error: {safe_error}"
            
            if log['stage'].startswith('extract_') and log['details'].get('value'):
                field = html.escape(str(log['details'].get('field', '')))
                value = html.escape(str(log['details'].get('value', '')))
                method = html.escape(str(log['details'].get('method', '')))
                confidence = log['details'].get('confidence', 0) * 100
                line += f"\n    {field}: {value} ({method}, {confidence:.0f}%)"
            
            output.append(line)
        
        return '\n'.join(output)
    
    def get_logs_list(self) -> List[Dict[str, Any]]:
        """Get the raw logs list for session state storage."""
        return self.logs.copy()
    
    def load_logs(self, logs: List[Dict[str, Any]]):
        """Load logs from session state."""
        self.logs = logs.copy()
    
    def clear(self):
        """Clear all logs."""
        self.logs = []


extraction_logger = ExtractionLogger()

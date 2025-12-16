"""
Integration module for easy integration with existing cretify.py system
"""

import os
from .certificate_builder_with_headers import create_certificate_pdf

def generate_certificate_from_replacements(replacements, output_path, name):
    """
    Generate certificate PDF from the existing replacements format
    
    Args:
        replacements (dict): Dictionary with replacement keys from existing system
        output_path (str): Full path where PDF should be saved
        name (str): Student name for logging
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    try:
        # Convert replacements format to student_data format
        student_data = {
            'name': replacements.get("<name>", name).strip(),
            'role': replacements.get("<role>", "Course").strip(),
            'duration': replacements.get("<duration>", "").strip(),
            'technologies': replacements.get("technologies", "").strip(),
            'project': replacements.get("o1", "").strip(),
            'location': replacements.get("<location>", "").strip(),
            'trainer': replacements.get("trainer", "").strip(),
            'print_date': replacements.get("<p1>", "").strip()
        }
        
        # Generate the certificate
        create_certificate_pdf(student_data, output_path)
        
        # Validate the PDF was created
        if os.path.exists(output_path):
            # Check file size
            file_size = os.path.getsize(output_path)
            if file_size < 100:
                raise Exception("Generated PDF is too small")
            
            # Check PDF format
            with open(output_path, 'rb') as f:
                pdf_content = f.read(10)
                if not pdf_content.startswith(b'%PDF'):
                    raise Exception("Generated file is not a valid PDF")
            
            print(f"PROD DEBUG - New PDF generator successful for {name}")
            return True
        else:
            raise Exception("PDF file was not created")
            
    except Exception as e:
        print(f"PROD ERROR - New PDF generator failed for {name}: {e}")
        return False

def batch_generate_certificates(excel_data, output_directory):
    """
    Generate certificates for batch processing from Excel data
    
    Args:
        excel_data (pandas.DataFrame): Excel data with certificate information
        output_directory (str): Directory to save certificates
    
    Returns:
        list: List of tuples (name, success, file_path)
    """
    
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    results = []
    
    for index, row in excel_data.iterrows():
        try:
            name = str(row.get('name', 'Unknown')).strip()
            
            # Prepare student data
            student_data = {
                'name': name,
                'role': str(row.get('role', 'Course')).strip(),
                'duration': str(row.get('duration', '')).strip(),
                'technologies': str(row.get('technologies', '')).strip(),
                'project': str(row.get('project', '')).strip(),
                'location': str(row.get('branch_name', '')).strip(),
                'trainer': str(row.get('trainer', '')).strip(),
                'print_date': str(row.get('print_date', '')).strip()
            }
            
            # Generate safe filename
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            output_path = os.path.join(output_directory, f"{safe_name}.pdf")
            
            # Generate certificate
            success = generate_certificate_from_replacements(
                {
                    "<name>": student_data['name'],
                    "<role>": student_data['role'],
                    "<duration>": student_data['duration'],
                    "technologies": student_data['technologies'],
                    "o1": student_data['project'],
                    "<location>": student_data['location'],
                    "trainer": student_data['trainer'],
                    "<p1>": student_data['print_date']
                },
                output_path,
                name
            )
            
            results.append((name, success, output_path if success else None))
            
        except Exception as e:
            print(f"Error processing {name}: {e}")
            results.append((name, False, None))
    
    return results
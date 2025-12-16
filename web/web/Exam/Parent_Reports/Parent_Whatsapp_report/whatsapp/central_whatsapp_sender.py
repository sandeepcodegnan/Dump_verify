"""
WhatsApp message sender using central WhatsApp notification system
"""
import time
from typing import Dict, List
from web.Exam.central_whatsapp_notifications.wa_send import send_whatsapp
from web.Exam.central_whatsapp_notifications.payloads import SP_Payload, clean_phone


class CentralWhatsAppSender:
    def send_report_message(self, phone_number: str, student_name: str, parent_name: str, s3_url: str, 
                          report_type: str, location: str, batch: str, period_id: str, 
                          from_dt: str, to_dt: str) -> Dict:
        """Send WhatsApp message with PDF report link using central system"""
        try:
            # Clean phone number
            clean_phone_num = clean_phone(phone_number)
            if not clean_phone_num:
                return {
                    "success": False,
                    "status": "FAILED",
                    "error": "Invalid phone number",
                    "phone": phone_number
                }
            
            # Create payload using central system
            payload = SP_Payload(
                first_name=parent_name or "Parent",
                phone=clean_phone_num,
                pdf_url=s3_url,
                from_dt=from_dt,
                to_dt=to_dt,
                location=location,
                student_name=student_name,
                batch=batch,
                period_id=period_id,
                report_type=report_type
            )
            
            # Prepare info for logging to parent_message_status (delivery tracking only)
            info = {
                "phone": clean_phone_num,
                "student_name": student_name,
                "s3_url": s3_url,
                "batch": batch,
                "location": location,
                "period_id": period_id,
                "report_type": report_type
            }
            
            # Send using central WhatsApp system
            purpose = "Weekly_Report" if report_type == "weekly" else "Monthly_Report"
            success = send_whatsapp(payload, info=info, purpose=purpose)
            
            return {
                "success": success,
                "status": "SENT" if success else "FAILED",
                "error": None if success else "WhatsApp API failed",
                "phone": phone_number
            }
                
        except Exception as e:
            return {
                "success": False,
                "status": "ERROR",
                "error": str(e),
                "phone": phone_number
            }


def send_batch_whatsapp_messages(students: List[Dict], report_type: str, location: str, 
                                batch_name: str, period_id: str) -> List[Dict]:
    """Send WhatsApp messages to all students in a batch using central system"""
    sender = CentralWhatsAppSender()
    results = []
    
    # Extract date range from period_id
    try:
        from_dt, to_dt = period_id.split("_to_")
    except:
        from_dt = to_dt = period_id
    
    for student in students:
        parent_phone = student.get("parentPhone") or student.get("parentPhNumber")
        if not student.get("s3_url") or not parent_phone:
            results.append({
                "student_id": student.get("id"),
                "student_name": student.get("name"),
                "success": False,
                "status": "SKIPPED",
                "reason": "No PDF or parent phone",
                "phone": parent_phone
            })
            continue
        
        result = sender.send_report_message(
            phone_number=parent_phone,
            student_name=student.get("name"),
            parent_name=f"{student.get('name', 'Student')}_Parent",
            s3_url=student.get("s3_url"),
            report_type=report_type,
            location=location,
            batch=batch_name,
            period_id=period_id,
            from_dt=from_dt,
            to_dt=to_dt
        )
        
        result.update({
            "student_id": student.get("id"),
            "student_name": student.get("name")
        })
        
        results.append(result)
        time.sleep(2.0)  # Rate limiting
    
    return results
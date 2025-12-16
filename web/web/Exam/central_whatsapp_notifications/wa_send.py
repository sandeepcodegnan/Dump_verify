import os
import requests
from web.Exam.central_whatsapp_notifications.wa_collections import wa_parent_collection, wa_examiner_collection
from web.Exam.central_whatsapp_notifications.log_records import SP_Weekly_Report, Daily_Exam_Notify
from web.Exam.central_whatsapp_notifications.helpers import auto_format_datetime
from web.Exam.central_whatsapp_notifications.config import logger


# Use NEW_CHATRACE for all WhatsApp communications (Parent Reports, Admin Reports, Daily Exam Notifications)
CHATRACE_API   = os.getenv("NEW_CHATRACE_API")
CHATRACE_TOKEN = os.getenv("NEW_CHATRACE_TOKEN")



def validate_chatrace_config():
    """Validate ChatRace configuration"""
    if not CHATRACE_API:
        logger.error("CHATRACE_API environment variable is not set")
        return False
    if not CHATRACE_TOKEN:
        logger.error("CHATRACE_TOKEN environment variable is not set")
        return False
    logger.info(f"ChatRace API: {CHATRACE_API}")
    logger.info(f"ChatRace Token (first 20 chars): {CHATRACE_TOKEN[:20]}...")
    return True

if not validate_chatrace_config():
    raise ValueError("Chatrace API URL or token is not set in the environment variables.")

def get_headers_and_api(purpose=None):
    """Get API and headers for WhatsApp communication"""
    logger.info(f"Using ChatRace API for purpose: {purpose}")
    return CHATRACE_API, {
        "X-ACCESS-TOKEN": CHATRACE_TOKEN,
        "accept": "application/json",
        "Content-Type": "application/json",
    }


log_Weekly_WA_Status = SP_Weekly_Report(wa_parent_collection)
log_Daily_Exam_WA_Status = Daily_Exam_Notify(wa_examiner_collection)



def send_whatsapp(payload,info=None,purpose=None):
    """Send one WhatsApp message via Chatrace. Return True on success."""
    try:
        api_url, headers = get_headers_and_api(purpose)
        response = requests.post(f"{api_url}/users", headers=headers, json=payload, timeout=15)
        
        # Handle 401 Unauthorized specifically
        if response.status_code == 401:
            logger.error(f"ChatRace API authentication failed. Token: {headers.get('X-ACCESS-TOKEN', 'Not found')[:20]}...")
            logger.error(f"Response: {response.text}")
            return False
            
        response.raise_for_status()
        
        # Log to parent_message_status for delivery tracking
        if info is not None:
            try:
                date_header = response.headers.get("Date")
                info['sent'] = auto_format_datetime(date_header)
                
                if purpose in ["Weekly_Report", "Monthly_Report"]:
                    result = log_Weekly_WA_Status.insert_or_update_details(info)
                    if not result.get("success"):
                        print(f"Failed to log WhatsApp status: {result}")
                elif purpose=="Daily_Exam":
                    result = log_Daily_Exam_WA_Status.insert_or_update_details(info)
                    if not result.get("success"):
                        print(f"Failed to log exam WhatsApp status: {result}")
            except Exception as log_error:
                print(f"Error logging WhatsApp status: {log_error}")
                # Don't fail the WhatsApp send if logging fails
        return True
    except requests.exceptions.Timeout:
        logger.error("WhatsApp send timeout")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"WhatsApp send request failed: {e}")
        return False
    except Exception as e:
        logger.error(f"WhatsApp send unexpected error: {e}")
        return False
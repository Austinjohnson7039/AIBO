import os
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)

def get_whatsapp_client():
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth = os.getenv("TWILIO_AUTH_TOKEN")
    if not sid or not auth:
        return None
    return Client(sid, auth)

def send_whatsapp_alert(message: str) -> bool:
    """Send an immediate WhatsApp message to the admin."""
    client = get_whatsapp_client()
    
    admin_num = os.getenv("ADMIN_WHATSAPP_NUMBER", "")
    sys_num = os.getenv("TWILIO_WHATSAPP_NUMBER", "")

    if not client or not admin_num or not sys_num:
        logger.warning(f"WhatsApp alert skipped (not configured): {message}")
        print(f"[WHATSAPP MOCK] {message}")
        return False
        
    try:
        to_number = f"whatsapp:{admin_num}" if not admin_num.startswith("whatsapp:") else admin_num
        from_number = f"whatsapp:{sys_num}" if not sys_num.startswith("whatsapp:") else sys_num
        
        msg = client.messages.create(
            body=message,
            from_=from_number,
            to=to_number
        )
        logger.info(f"WhatsApp alert sent! ID: {msg.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send WhatsApp alert: {str(e)}")
        return False

def format_daily_summary(low_items: list) -> str:
    """Format the daily summary of low inventory items."""
    if not low_items:
        return "☕ AIBO Daily Stock Report: All inventory levels are optimal."
        
    lines = ["📉 *AIBO Daily Stock Alert* 📉", "The following items require your attention:"]
    for item in low_items:
        name = item.get('ingredient_name', item.get('item', 'Unknown'))
        stock = item.get('current_stock', item.get('stock', 0))
        unit = item.get('unit', 'units')
        reorder = item.get('reorder_level', item.get('reorder', 0))
        lines.append(f"• {name}: {stock} {unit} left (Reorder trigger: {reorder})")
    
    return "\n".join(lines)

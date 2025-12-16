import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional
from web.Exam.exam_central_db import db, admin_notifications_collection, daily_report_status_collection
from web.Exam.central_whatsapp_notifications.payloads import Admin_Payload
from web.Exam.central_whatsapp_notifications.wa_send import send_whatsapp
from apscheduler.schedulers.background import BackgroundScheduler

tz = ZoneInfo("Asia/Kolkata")


def get_active_admins() -> Dict[str, str]:
    """Get active admin list from database (only those who want daily reports)"""
    try:
        active_admins = {}
        admin_docs = admin_notifications_collection.find({
            "isActive": True,
            "notifications.dailyReports": True
        })
        for doc in admin_docs:
            phone = doc.get("phone")
            name = doc.get("name")
            if phone and name:
                active_admins[phone] = name
        return active_admins
    except Exception as e:
        print(f"[ERROR] Failed to get admins from DB: {e}")
        # Fallback to hardcoded list
        return {
            "917036339459": "Mr.sandeep",
        }

# ─── Metrics helper ────────────────────────────────────────────────
def build_metrics_for_date(date_key: str) -> Dict[str, Any]:
    # Count ALL exams (both started and not started) - like old version
    exams = list(db["Daily-Exam"].find({"startDate": date_key}))
    loc_map: Dict[str, Dict[str, int]] = {}
    for e in exams:
        loc = e.get("location") or "Unknown"
        rec = loc_map.setdefault(loc, {"allocated": 0, "attempted": 0})
        rec["allocated"] += 1
        if e.get("attempt-status"):
            rec["attempted"] += 1

    alloc_parts       = [f"{loc} – {d['allocated']}" for loc, d in loc_map.items()]
    attempt_parts     = [f"{loc} – {d['attempted']}" for loc, d in loc_map.items()]
    non_attempt_parts = [
        f"{loc} – {d['allocated']-d['attempted']}" for loc, d in loc_map.items()
    ]

    total_alloc   = sum(d["allocated"] for d in loc_map.values())
    total_attempt = sum(d["attempted"] for d in loc_map.values())

    return {
        "alloc_parts":       ", ".join(alloc_parts),
        "attempt_parts":     ", ".join(attempt_parts),
        "non_attempt_parts": ", ".join(non_attempt_parts),
        "total_alloc":       total_alloc,
        "total_attempt":     total_attempt,
        "total_non_attempt": total_alloc - total_attempt,
    }

# ─── Scheduled job --------------------------------------------------
def _check_and_trigger_report():
    """Runs every minute. Waits for window periods to end + all started exams to finish."""
    
    now = datetime.datetime.now(tz)
    current_seconds = now.hour * 3600 + now.minute * 60 + now.second

    today_str = now.strftime("%Y-%m-%d")
    
    # Check if report already sent today (database-persisted)
    report_status = daily_report_status_collection.find_one({"date": today_str})
    if report_status and report_status.get("sent"):
        return  # already sent today

    # Get all exams for today (both started and unstarted)
    all_exams_today = list(db["Daily-Exam"].find({"startDate": today_str}))
    if not all_exams_today:
        return

    # --- Step 1: Check if all window periods have ended ---
    latest_window_end = None
    for e in all_exams_today:
        window_end = e.get("windowEndTime")
        if window_end is not None:
            latest_window_end = window_end if latest_window_end is None else max(latest_window_end, window_end)
    
    if latest_window_end is None:
        print("[WARN] No window periods found - using old logic")
        return
    
    # Wait until 5 minutes after latest window ends
    trigger_time = latest_window_end + (2 * 60)  # +5 minutes
    
    if current_seconds < trigger_time:
        print(f"[DEBUG] Waiting for window period to end + 2min buffer. Trigger at: {trigger_time//3600:02d}:{(trigger_time%3600)//60:02d}")
        return

    # --- Step 2: Calculate worst-case scenario for late starters ---
    # Someone could start at windowEnd-1 minute and still get full duration
    max_exam_duration = 0
    for e in all_exams_today:
        dur = e.get("totalExamTime")
        if dur is not None:
            max_exam_duration = max(max_exam_duration, int(dur))
    
    # Worst case: student starts 1 minute before window closes + gets full duration
    worst_case_end_seconds = latest_window_end + (max_exam_duration * 60)  # window end + max duration
    worst_case_trigger = worst_case_end_seconds + (2 * 60)  # + 2 min grace
    
    if current_seconds < worst_case_trigger:
        wc_hours = worst_case_trigger // 3600
        wc_minutes = (worst_case_trigger % 3600) // 60
        print(f"[DEBUG] Waiting for potential late starters. Worst case trigger: {wc_hours:02d}:{wc_minutes:02d}")
        return
    
    # --- Step 3: Double-check all actually started exams have finished ---
    started_exams = [e for e in all_exams_today if e.get("startTimestamp")]
    if started_exams:
        latest_exam_end = None
        for e in started_exams:
            start_ts, dur = e.get("startTimestamp"), e.get("totalExamTime")
            if not start_ts or dur is None:
                continue
            try:
                if isinstance(start_ts, datetime.datetime):
                    start_dt = start_ts.replace(tzinfo=tz) if start_ts.tzinfo is None else start_ts.astimezone(tz)
                else:
                    start_dt = datetime.datetime.fromisoformat(str(start_ts)).replace(tzinfo=tz)
                
                end_dt = start_dt + datetime.timedelta(minutes=int(dur))
                latest_exam_end = end_dt if latest_exam_end is None else max(latest_exam_end, end_dt)
            except (ValueError, TypeError) as err:
                print("[WARN] could not parse startTimestamp for doc:", e.get("_id"), err)
        
        if latest_exam_end:
            grace_end = latest_exam_end + datetime.timedelta(minutes=1)  # 1-min buffer
            if now <= grace_end:
                print(f"[DEBUG] Waiting for started exams to finish. Grace ends: {grace_end.strftime('%H:%M:%S')}")
                return

    # --- All conditions met → build and send report ---
    greeting = "Good Morning" if now.hour < 12 else "Good Evening"
    m        = build_metrics_for_date(today_str)

    active_admins = get_active_admins()
    for phone, name in active_admins.items():
        print(f"[DEBUG] Sending report to {name} ({phone})")
        admin_payload = Admin_Payload(phone,name,today_str,greeting,m)
        
        try:
            status = send_whatsapp(admin_payload, purpose="Admin_Report")
            if status:
                print(f"[INFO] Success for {name}")
        except Exception as exc:
            print(f"[ERROR] Failed for {name}: {exc}")

    # Mark report as sent in database
    daily_report_status_collection.update_one(
        {"date": today_str},
        {"$set": {
            "sent": True,
            "sentAt": now,
            "adminCount": len(active_admins)
        }},
        upsert=True
    )
    print("[INFO] Report dispatched; scheduler will stay quiet until tomorrow")


# ─── Public helper --------------------------------------------------
_scheduler: Optional[BackgroundScheduler] = None


def start_scheduler() -> BackgroundScheduler:
    """Start the job, guarding against Werkzeug double-import."""
    global _scheduler
    if _scheduler:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone=tz, daemon=True)
    _scheduler.add_job(
        _check_and_trigger_report,
        trigger="interval",
        minutes=1,
        id="daily_exam_report",
        max_instances=1,                 # prevent overlap
        coalesce=True,                   # skip if backlog
    )
    _scheduler.start()
    print("[INFO] APScheduler started")
    return _scheduler
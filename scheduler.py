import uuid
import threading
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

# Initialize the scheduler once globally
scheduler = BackgroundScheduler()

def start_automated_captures(interval_seconds: int, note: str, capture_task_function, start_time: datetime = None, precheck_function=None):
    """Starts precise interval captures using APScheduler, with an optional 10s early precheck."""
    
    if not start_time:
        # 1. Fire initial capture in a daemon thread so it never blocks
        threading.Thread(target=capture_task_function, args=(note,), daemon=True).start()
        # 2. Calculate the exact time for the next sequence
        start_time = datetime.now() + timedelta(seconds=interval_seconds)
    
    # Schedule the precheck 10 seconds early to absorb login macro delays
    # (Only apply precheck if the interval is large enough to support a 10s offset)
    precheck_offset = 10 if interval_seconds >= 20 else 0
    if precheck_function and precheck_offset > 0:
        precheck_time = start_time - timedelta(seconds=precheck_offset)
        scheduler.add_job(
            func=precheck_function,
            trigger='interval',
            seconds=interval_seconds,
            id='bms_precheck_task',
            start_date=precheck_time,
            replace_existing=True 
        )

    # Schedule recurring captures EXACTLY on the scheduled time
    scheduler.add_job(
        func=capture_task_function,
        trigger='interval',
        seconds=interval_seconds,
        args=[note],
        id='bms_capture_task',
        start_date=start_time,
        replace_existing=True 
    )
    
    if not scheduler.running:
        scheduler.start()
        
    time_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[*] Precise scheduler started: Capturing every {interval_seconds}s. Starts: {time_str}")

def stop_automated_captures():
    """Stops the recurring capture and precheck tasks."""
    stopped = False
    if scheduler.get_job('bms_capture_task'):
        scheduler.remove_job('bms_capture_task')
        stopped = True
        
    if scheduler.get_job('bms_precheck_task'):
        scheduler.remove_job('bms_precheck_task')
        
    if stopped:
        print("[*] Scheduler stopped.")
        return True
    return False

def is_scheduler_running():
    """Returns True if the timer is currently active."""
    return scheduler.get_job('bms_capture_task') is not None

def schedule_single_capture(run_date: datetime, note: str, capture_task_function, precheck_function=None):
    """Schedules a single one-time capture at an exact timestamp."""
    job_id = f"single_capture_{uuid.uuid4().hex[:6]}"
    
    # Precheck 10s early
    if precheck_function:
        precheck_time = run_date - timedelta(seconds=10)
        # Ensure we don't try to schedule a precheck in the past
        if precheck_time > datetime.now():
            scheduler.add_job(
                func=precheck_function,
                trigger='date',
                run_date=precheck_time,
                id=f"pre_{job_id}",
                misfire_grace_time=60
            )
    
    # Main capture execution
    scheduler.add_job(
        func=capture_task_function,
        trigger='date',
        run_date=run_date,
        args=[note],
        id=job_id,
        misfire_grace_time=60
    )
    
    if not scheduler.running:
        scheduler.start()
        
    print(f"[*] Scheduled 1-time capture at {run_date.strftime('%Y-%m-%d %H:%M:%S')}")
from apscheduler.schedulers.background import BackgroundScheduler

# Initialize the scheduler once globally
scheduler = BackgroundScheduler()

def start_automated_captures(interval_seconds: int, note: str, capture_task_function):
    """Starts precise interval captures using APScheduler."""
    
    # 1. Take the first screenshot immediately
    capture_task_function(note)
    
    # 2. Schedule all future captures using exact seconds
    scheduler.add_job(
        func=capture_task_function,
        trigger='interval',
        seconds=interval_seconds,
        args=[note],
        id='bms_capture_task',
        replace_existing=True 
    )
    
    # 3. Start the background scheduler thread if it isn't running yet
    if not scheduler.running:
        scheduler.start()
        
    print(f"[*] Precise scheduler started: Capturing every {interval_seconds} seconds.")

def stop_automated_captures():
    """Stops the recurring capture task."""
    if scheduler.get_job('bms_capture_task'):
        scheduler.remove_job('bms_capture_task')
        print("[*] Scheduler stopped.")
        return True
    return False

def is_scheduler_running():
    """Returns True if the timer is currently active."""
    return scheduler.get_job('bms_capture_task') is not None
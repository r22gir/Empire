#!/usr/bin/env python3
"""
CoPilotForge Native Messaging Host
Receives messages from browser extension and saves to local files
"""

import sys
import json
import struct
import os
from datetime import datetime
from pathlib import Path

SAVE_DIR = Path.home() / "Empire/products/copilotforge/data/chats"
LOG_FILE = Path.home() / "Empire/products/copilotforge/data/sessions.log"

def log(message):
    """Append to log file"""
    with open(LOG_FILE, 'a') as f:
        f.write(f"[{datetime.now().isoformat()}] {message}\n")

def get_message():
    """Read message from stdin (browser)"""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack('=I', raw_length)[0]
    message = sys.stdin.buffer.read(message_length).decode('utf-8')
    return json.loads(message)

def send_message(message):
    """Send message to browser"""
    encoded = json.dumps(message).encode('utf-8')
    sys.stdout.buffer.write(struct.pack('=I', len(encoded)))
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()

def save_chat(data):
    """Save chat content to file"""
    timestamp = datetime.now()
    date_str = timestamp.strftime('%Y-%m-%d')
    time_str = timestamp.strftime('%H-%M-%S')
    
    # Create session directory
    session_dir = SAVE_DIR / f"{date_str}_session"
    session_dir.mkdir(parents=True, exist_ok=True)
    
    # Save current (always latest)
    current_file = session_dir / "current.md"
    with open(current_file, 'w') as f:
        f.write(data.get('content', ''))
    
    # Save timestamped version
    save_file = session_dir / f"{time_str}.md"
    with open(save_file, 'w') as f:
        f.write(data.get('content', ''))
    
    # Hourly cleanup - keep only last file per hour
    cleanup_hourly(session_dir)
    
    log(f"Saved: {save_file} ({data.get('reason', 'unknown')})")
    
    return {'success': True, 'file': str(save_file)}

def cleanup_hourly(session_dir):
    """Keep only the latest file from each previous hour"""
    current_hour = datetime.now().strftime('%H')
    files_by_hour = {}
    
    for f in session_dir.glob('*.md'):
        if f.name in ['current.md', 'final.md'] or f.name.startswith('hour_'):
            continue
        
        try:
            hour = f.stem.split('-')[0]
            if hour != current_hour:
                if hour not in files_by_hour:
                    files_by_hour[hour] = []
                files_by_hour[hour].append(f)
        except:
            continue
    
    # Keep only latest from each past hour
    for hour, files in files_by_hour.items():
        files.sort(key=lambda x: x.stem)
        
        # Rename latest to hour snapshot
        latest = files[-1]
        hour_file = session_dir / f"hour_{hour}.md"
        
        if not hour_file.exists():
            latest.rename(hour_file)
            files = files[:-1]
        
        # Delete older files from that hour
        for f in files:
            if f.exists():
                f.unlink()

def main():
    """Main loop - receive and process messages"""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    log("Native host started")
    
    while True:
        message = get_message()
        if message is None:
            break
        
        try:
            if message.get('type') == 'SAVE_CHAT':
                result = save_chat(message)
                send_message(result)
            else:
                send_message({'error': 'Unknown message type'})
        except Exception as e:
            log(f"Error: {e}")
            send_message({'error': str(e)})

if __name__ == '__main__':
    main()

import os
import sys
# Force physical addressing
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
import time
import fcntl
import logging
from logging.handlers import RotatingFileHandler
import socket
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

# ==========================================
# 0. Physical Boundaries & Environment Setup
# ==========================================
BASE_DIR = os.getenv("ZT_BASE_DIR", os.path.expanduser("~/tmp/ZT"))
BLACKBOARD_FILE = os.path.join(BASE_DIR, "coffee.example.json")
LOCK_FILE = os.path.join(BASE_DIR, "coffee.example.json.lock") 

BLACKBOARD_DIR = os.path.join(BASE_DIR, "blackboard")        
BUFFER_DIR = os.path.join(BASE_DIR, "buffer_memory")         

ROUTER_DIR = os.path.join(BASE_DIR, "router")
BRIEFING_CACHE = os.path.join(ROUTER_DIR, "briefing_cache")
PERSONA_FILE = os.path.join(BASE_DIR, "character.example.json") 
LOG_FILE = os.path.join(ROUTER_DIR, "frontdesk_core.log")
PENANCE_LOG = os.path.join(ROUTER_DIR, "frontdesk_penance.log")
INQUISITION_LOG = os.path.join(ROUTER_DIR, "global_inquisition.log")

for d in [BLACKBOARD_DIR, BUFFER_DIR, BRIEFING_CACHE]:
    os.makedirs(d, exist_ok=True)
for log_f in [PENANCE_LOG, INQUISITION_LOG]:
    if not os.path.exists(log_f): open(log_f, 'w').close()

log_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
logging.basicConfig(handlers=[log_handler], level=logging.INFO, format='%(asctime)s - [ROUTER] - %(message)s')

# ==========================================
# 1. Physical Read/Write Locks
# ==========================================
class BlackboardLock:
    def __init__(self, lock_file):
        self.lock_file = lock_file
        self.handle = None
    def __enter__(self):
        self.handle = open(self.lock_file, 'w')
        fcntl.flock(self.handle, fcntl.LOCK_EX)
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        fcntl.flock(self.handle, fcntl.LOCK_UN)
        self.handle.close()

def load_blackboard():
    if not os.path.exists(BLACKBOARD_FILE): return {"tasks": []}
    with BlackboardLock(LOCK_FILE): 
        try:
            with open(BLACKBOARD_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return {"tasks": []}

def save_blackboard(data):
    with BlackboardLock(LOCK_FILE): 
        with open(BLACKBOARD_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

def read_json_file(filepath):
    if not os.path.exists(filepath): return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def read_text_file(filepath):
    if not os.path.exists(filepath): return ""
    try:
        with open(filepath, "r", encoding="utf-8") as f: return f.read()
    except: return ""

def read_memory_tail(filepath, lines=30):
    if not os.path.exists(filepath): return ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return "".join(f.readlines()[-lines:]) 
    except: return ""

# ==========================================
# 1.5 Weapon Fire Control System
# ==========================================
def fire_sglang_engine(prompt, dynamic_system_prompt):
    API_URL = "http://127.0.0.1:30000/v1/chat/completions"
    payload = {
        "model": "default",
        "messages": [
            {"role": "system", "content": dynamic_system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1,  
        "max_tokens": 2048
    }
    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))["choices"][0]["message"]["content"]
    except Exception as e: return f"[!] SGLang engine misfire: {e}"

def fire_ollama_engine(prompt, dynamic_system_prompt, target_model):
    API_URL = "http://127.0.0.1:11434/api/chat"
    payload = {
        "model": target_model, 
        "messages": [
            {"role": "system", "content": dynamic_system_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "format": "json", 
        "keep_alive": "5m"
    }
    req = urllib.request.Request(API_URL, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            return json.loads(response.read().decode("utf-8"))["message"]["content"]
    except Exception as e: return f"[!] Ollama ({target_model}) engine misfire: {e}"

# ==========================================
# 2. [P0] Doomsday Radar
# ==========================================
class DoomsdayRadar:
    GPU_WARNING_TEMP = 82
    GPU_CRITICAL_TEMP = 88

    @staticmethod
    def get_gpu_temp():
        try:
            res = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"], capture_output=True, text=True)
            return int(res.stdout.strip())
        except: return 0

    @staticmethod
    def execute_dunkirk_evacuation(board):
        print("\n🚨 [P0 Radar Triggered]: Thermal threshold breached!")
        
        # OBFUSCATED: Edge node lockdown
        edge_ip = os.getenv("EDGE_NODE_IP", "10.0.0.2")
        edge_user = os.getenv("EDGE_NODE_USER", "edge_user")
        subprocess.run(["ssh", f"{edge_user}@{edge_ip}", "sudo ufw default deny incoming"], capture_output=True)
        
        snapshot = os.path.join(BUFFER_DIR, f"snapshot_{int(time.time())}.json")
        try:
            with open(snapshot, "w") as f: json.dump(board, f)
        except: pass
        
        import select
        for i in range(60, 0, -1):
            i_in, _, _ = select.select([sys.stdin], [], [], 1)
            if i_in:
                cmd = sys.stdin.readline().strip().lower()
                if cmd == 'wait': return "suspended"
                elif cmd == 'no': return "cancelled"
                elif cmd == 'yes': break
        
        # OBFUSCATED: Jump node shutdown sequence
        jump_ip = os.getenv("JUMP_NODE_IP", "10.0.0.3")
        jump_user = os.getenv("JUMP_NODE_USER", "jump_user")
        subprocess.run(["ssh", "-J", f"{edge_user}@{edge_ip}", f"{jump_user}@{jump_ip}", "sudo shutdown -h now &"], capture_output=True)
        subprocess.run(["ssh", f"{edge_user}@{edge_ip}", "sudo shutdown -h now &"], capture_output=True)
        os.system("sudo shutdown -h now")

# ==========================================
# 3. Sympathetic Nerve & Autonomous Control
# ==========================================
class frontdeskActuator:
    last_gpu_active_time = time.time()
    
    @staticmethod
    def is_port_open(port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        s.settimeout(1)
        try:
            s.connect(("127.0.0.1", port))
            s.close()
            return True
        except: return False

    @staticmethod
    def get_agent_config(role_name):
        roles_data = read_json_file(PERSONA_FILE)
        agents = roles_data.get("agents", {})
        return agents.get(role_name, {})

    @staticmethod
    def synthesize_prompt(role_name, agent_info):
        prompt = agent_info.get("system_prompt", f"You are {role_name}.")
        
        if role_name == "frontdesk":
            penance = read_memory_tail(PENANCE_LOG, 30)
            inquisition = read_memory_tail(INQUISITION_LOG, 30)
            if penance.strip(): prompt += f"\n\n[Historical Penance]:\n{penance}"
            if inquisition.strip(): prompt += f"\n\n[Correction Records]:\n{inquisition}"
            
            prompt += """
            \n\n[System Protocol]:
            You are the primary router. You must request approval for high-risk operations (delete, modify, create).
            Output strictly in JSON.
            """
            
        return prompt

    @staticmethod
    def manage_gpu_tidal_state(needs_gpu):
        current_temp = DoomsdayRadar.get_gpu_temp()
        if current_temp >= DoomsdayRadar.GPU_WARNING_TEMP:
            subprocess.run(["pkill", "-f", "sglang"], capture_output=True)
            return "suspended_by_heat"

        is_running = frontdeskActuator.is_port_open(30000)
        current_time = time.time()
        
        if needs_gpu and not is_running:
            subprocess.Popen(["bash", os.path.join(BASE_DIR, "cachemode.sh")], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setpgrp)
            time.sleep(10)
            frontdeskActuator.last_gpu_active_time = current_time
        elif needs_gpu and is_running:
            frontdeskActuator.last_gpu_active_time = current_time
        elif not needs_gpu and is_running:
            if (current_time - frontdeskActuator.last_gpu_active_time) > 900:
                print("\n[💤] VRAM idle for 15 mins. Powering down.")
                subprocess.run(["pkill", "-f", "sglang"], capture_output=True)
        return "ok"

# ==========================================
# 4. Master Scheduler Engine
# ==========================================
def execute_darwin_protocol():
    board = load_blackboard()
    if not board: return
    tasks = board.get("tasks", [])
    has_updates = False
    
    needs_gpu_now = any(t.get("status") == "pending" and t.get("assigned_to") in ["Expert", "Honker"] for t in tasks)
    gpu_status = frontdeskActuator.manage_gpu_tidal_state(needs_gpu_now)
    
    if gpu_status == "suspended_by_heat" and DoomsdayRadar.get_gpu_temp() >= DoomsdayRadar.GPU_CRITICAL_TEMP:
        if DoomsdayRadar.execute_dunkirk_evacuation(board) == "suspended": return

    for task in tasks:
        status = task.get("status")
        if status in ["completed", "waiting_external", "pending_approval"]: continue
            
        if status == "pending":
            task_id = task.get("id", f"task_{int(time.time())}")
            assignee = task.get("assigned_to", "frontdesk")
            
            if gpu_status == "suspended_by_heat" or (assignee in ["Expert", "Honker"] and not frontdeskActuator.is_port_open(30000)):
                suspend_file = os.path.join(BUFFER_DIR, f"{task_id}_suspend.json")
                with open(suspend_file, "w", encoding="utf-8") as f:
                    json.dump({"task_context": task, "timestamp": time.time()}, f, ensure_ascii=False)
                task["status"] = "waiting_external"
                task["buffer_pointer"] = suspend_file 
                has_updates = True
                continue
                
            print(f"\n[>>> Lock Task]: {task_id} | Seat: {assignee}...")
            
            agent_info = frontdeskActuator.get_agent_config(assignee)
            dynamic_system_prompt = frontdeskActuator.synthesize_prompt(assignee, agent_info)
            
            if "buffer_pointer" in task and os.path.exists(task["buffer_pointer"]):
                dynamic_system_prompt += f"\n\n[Restore Memory]:\n{read_text_file(task['buffer_pointer'])}"
            
            target_mod = agent_info.get("model", "qwen3.5:9b")
            
            if assignee in ["frontdesk", "Piper", "Librarian", "Security"]:
                answer = fire_ollama_engine(task.get("prompt"), dynamic_system_prompt, target_mod)
            else:
                answer = fire_sglang_engine(task.get("prompt"), dynamic_system_prompt)
            
            if answer:
                print(f"\n[🤖 {assignee} Execution Complete.] \n")
                if assignee == "frontdesk" and "briefing" in str(task_id).lower():
                    draft_file = os.path.join(BRIEFING_CACHE, f"{task_id}_briefing.md")
                else:
                    draft_file = os.path.join(BLACKBOARD_DIR, f"{task_id}_draft.md")
                
                with open(draft_file, "w", encoding="utf-8") as f: f.write(answer)
                
                task["response_pointer"] = draft_file
                if "prompt" in task: task["prompt"] = "[Truncated]" 
                task["status"] = "completed"
                task["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                
                if "buffer_pointer" in task and os.path.exists(task["buffer_pointer"]):
                    os.remove(task["buffer_pointer"])
                has_updates = True

    if has_updates: save_blackboard(board)

if __name__ == "__main__":
    if os.path.exists(LOCK_FILE):
        try: os.remove(LOCK_FILE)
        except: pass
    lock_fd = open(LOCK_FILE, 'w')
    try: fcntl.lockf(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: sys.exit(1)

    print("⚙ ZT Core: AGI Engine Online")
    try:
        while True:
            execute_darwin_protocol()
            time.sleep(3)
    except KeyboardInterrupt: pass
    finally:
        fcntl.lockf(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

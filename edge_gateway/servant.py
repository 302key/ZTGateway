import os
import sys
import json
import time
import shutil
import subprocess
from datetime import datetime

# ==========================================
# 0. Physical Boundaries
# ==========================================
BASE_DIR = os.getenv("ZT_BASE_DIR", os.path.expanduser("~/tmp/ZT"))
ORDERS_DIR = os.path.join(BASE_DIR, "orders")
PENDING_DIR = os.path.join(ORDERS_DIR, "pending")
COMPLETED_DIR = os.path.join(ORDERS_DIR, "completed")

# OBFUSCATED: Dead drop locations
DEAD_DROP_RAW = os.getenv("DEAD_DROP_RAW", os.path.expanduser("~/tmp/dead_drop/raw_inbox"))
DEAD_DROP_CLEAN = os.getenv("DEAD_DROP_CLEAN", os.path.expanduser("~/tmp/dead_drop/clean_ready"))
REPO_DIR = os.path.join(BASE_DIR, "repo")

REPO_ZONES = [
    os.path.expanduser("~/tmp/ZT"),                      
    REPO_DIR,             
    os.path.expanduser("~/tmp")                    
]

for d in [PENDING_DIR, COMPLETED_DIR, DEAD_DROP_RAW, DEAD_DROP_CLEAN, REPO_DIR]:
    os.makedirs(d, exist_ok=True)

class ResourceSniffer:
    @staticmethod
    def is_comfortable():
        try:
            with open('/proc/loadavg', 'r') as f:
                load1 = float(f.read().split()[0])
            if load1 > 6.0: return False
            res = subprocess.run(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"], capture_output=True, text=True)
            temp = int(res.stdout.strip() or 0)
            if temp > 75: return False
            return True
        except Exception: return True 

class ArmoryScanner:
    @staticmethod
    def locate_python(env_name):
        possible_dir_names = [env_name, f"{env_name}_venv", f"venv_{env_name}"]
        for zone in REPO_ZONES:
            if not os.path.exists(zone): continue
            for p_dir in possible_dir_names:
                target_dir = os.path.join(zone, p_dir)
                if not os.path.exists(target_dir): continue
                for root, dirs, files in os.walk(target_dir):
                    python_path = os.path.join(root, "bin", "python")
                    if os.path.exists(python_path): return python_path
                    depth = root.count(os.sep) - target_dir.count(os.sep)
                    if depth >= 2: dirs.clear() 
        return None

# ==========================================
# 2. Execution Engine
# ==========================================
class Executioner:
    @staticmethod
    def execute_local_venv(task_id, script_code, env_name, persist=False):
        script_path = os.path.join(BASE_DIR, f"temp_script_{task_id}.py")
        is_temp_venv = False
        
        python_exe = ArmoryScanner.locate_python(env_name)
        
        if python_exe:
            print(f"\n[⚔️ Core] Sonar lock on persistent armor: [{env_name}] -> {python_exe}")
            venv_path = None
        else:
            if persist:
                print(f"\n[🏰 Core] AGI Directive: Building persistent armory [{env_name}]...")
                venv_path = os.path.join(REPO_DIR, f"{env_name}_venv")
                subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
                python_exe = os.path.join(venv_path, "bin", "python")
                is_temp_venv = False 
            else:
                print(f"\n[🔧 Core] Deploying ephemeral venv isolation...")
                venv_path = os.path.join(BASE_DIR, f"temp_venv_{task_id}")
                subprocess.run([sys.executable, "-m", "venv", venv_path], check=True)
                python_exe = os.path.join(venv_path, "bin", "python")
                is_temp_venv = True
            
        try:
            with open(script_path, "w", encoding="utf-8") as f: f.write(script_code)
            # Proxychains removed for open source neutrality, assumed local network config
            cmd = [python_exe, script_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.stdout if result.returncode == 0 else f"[!] Script Error:\n{result.stderr}"
        except Exception as e:
            return f"[!] Engine failure: {e}"
        finally:
            print(f"[💥 Core] Task concluded. Purging battlefield.")
            if is_temp_venv and venv_path and os.path.exists(venv_path): 
                shutil.rmtree(venv_path)
            if os.path.exists(script_path): os.remove(script_path)

    @staticmethod
    def execute_edge_docker(task_id, script_code, env_name, persist=False):
        print(f"\n[🌐 Edge] Paging outpost for Docker task...")
        script_name = f"{task_id}_spider.py"
        remote_script_path = os.path.join(DEAD_DROP_RAW, script_name)
        
        edge_ip = os.getenv("EDGE_NODE_IP", "10.0.0.2")
        edge_user = os.getenv("EDGE_NODE_USER", "edge_user")
        remote_dead_drop = os.getenv("EDGE_DEAD_DROP", "/tmp/raw_inbox")
        
        try:
            with open(remote_script_path, "w", encoding="utf-8") as f: f.write(script_code)
            
            if persist:
                print(f"[🏰 Edge] Waking persistent container: {env_name}")
                docker_cmd = (
                    f"docker exec {env_name} "
                    f"python {remote_dead_drop}/{script_name}"
                )
            else:
                docker_cmd = (
                    f"docker run --rm "
                    f"-v {os.getenv('EDGE_DEAD_DROP_ROOT', '/tmp')}:{os.getenv('EDGE_DEAD_DROP_ROOT', '/tmp')} "
                    f"python:3.9-slim python {remote_dead_drop}/{script_name}"
                )
            
            ssh_cmd = ["ssh", f"{edge_user}@{edge_ip}", docker_cmd]
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=600)
            return result.stdout if result.returncode == 0 else f"[!] Edge Docker Error:\n{result.stderr}"
        except Exception as e: return f"[!] Edge Connection Collapse: {e}"
        finally:
            if os.path.exists(remote_script_path): os.remove(remote_script_path)

# ==========================================
# 3. Main Loop
# ==========================================
def run_hand_daemon():
    print("⚙ ZT: Servant Actuator Online...")
    while True:
        try:
            if not ResourceSniffer.is_comfortable():
                time.sleep(15)
                continue
                
            pending_orders = [f for f in os.listdir(PENDING_DIR) if f.endswith(".json")]
            if not pending_orders:
                time.sleep(5)
                continue
                
            order_file = os.path.join(PENDING_DIR, pending_orders[0])
            with open(order_file, "r", encoding="utf-8") as f: order = json.load(f)
                
            task_id = order.get("id", f"unknown_{int(time.time())}")
            env = order.get("env", "local_venv")
            code = order.get("code", "")
            persist = order.get("persist", False) 
            
            if env == "edge_docker":
                output = Executioner.execute_edge_docker(task_id, code, env, persist)
            else:
                output = Executioner.execute_local_venv(task_id, code, env, persist)
                
            order["execution_result"] = output
            order["completed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            
            completed_file = os.path.join(COMPLETED_DIR, pending_orders[0])
            with open(completed_file, "w", encoding="utf-8") as f:
                json.dump(order, f, ensure_ascii=False, indent=4)
                
            os.remove(order_file)
            print(f"[✅] Order {task_id} fulfilled.")
            
        except Exception as e:
            time.sleep(10)

if __name__ == "__main__":
    run_hand_daemon()

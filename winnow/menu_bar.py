import os
import sys
import subprocess
import json
import urllib.request
import threading
import time

def install_and_import(package):
    import importlib
    try:
        importlib.import_module(package)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_and_import("rumps")
import rumps

def get_active_model() -> str:
    env_model = os.environ.get("WINNOW_LOCAL_MODEL")
    if env_model:
        return env_model.strip()
    model_file = os.path.expanduser("~/.winnow/active_model")
    if os.path.exists(model_file):
        try:
            with open(model_file, "r") as f:
                return f.read().strip()
        except Exception:
            pass
    return "Qwen3.5-9B-TNG-PKD-Qwopus-Coder-Qwythos-qx86-hi-mlx"

class WinnowMenuBarApp(rumps.App):
    def __init__(self):
        super(WinnowMenuBarApp, self).__init__("Winnow", title="💸")
        
        self.status_item = rumps.MenuItem("Winnow: Unknown", callback=None)
        self.toggle_item = rumps.MenuItem("Toggle Winnow (⌥⌘W)", callback=self.toggle_winnow, key="w")
        self.stats_item = rumps.MenuItem("Saved: 0 tokens ($0.00)", callback=None)
        self.omlx_status = rumps.MenuItem("oMLX: Checking...", callback=None)
        self.model_menu = rumps.MenuItem("Select Active Model")
        
        self.menu = [
            self.status_item,
            self.toggle_item,
            rumps.separator,
            self.stats_item,
            rumps.separator,
            self.omlx_status,
            self.model_menu,
            rumps.separator,
            rumps.MenuItem("Restart Winnow Proxy", callback=self.restart_proxy),
        ]
        
        self.cached_models_list = []
        self.is_updating = False
        
        self.timer = rumps.Timer(self.trigger_background_update, 5)
        self.timer.start()
        self.trigger_background_update(None)

    def trigger_background_update(self, sender):
        if not self.is_updating:
            threading.Thread(target=self.update_menu_state_async, daemon=True).start()

    def update_menu_state_async(self):
        self.is_updating = True
        try:
            # 1. Update Winnow Proxy enabled/disabled state
            disabled_file = os.path.expanduser("~/.winnow/disabled")
            is_enabled = not os.path.exists(disabled_file)
            
            if is_enabled:
                self.status_item.title = "🟢 Winnow: Active"
                self.toggle_item.title = "Disable Winnow (⌥⌘W)"
            else:
                self.status_item.title = "🔴 Winnow: Disabled"
                self.toggle_item.title = "Enable Winnow (⌥⌘W)"
                
            # 2. Fetch stats from local Winnow proxy
            try:
                req = urllib.request.Request("http://localhost:8787/winnow/stats", method="GET")
                with urllib.request.urlopen(req, timeout=1.0) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    saved = data.get("tokens_saved_total", 0)
                    cost_saved = (saved * 3.00) / 1000000.0
                    self.stats_item.title = f"Saved: {saved:,} tokens (${cost_saved:.2f})"
            except Exception:
                self.stats_item.title = "Saved: Proxy Offline"
                
            # 3. Check oMLX server status, populate models list, & check active model liveness
            active_model = get_active_model()
            try:
                req = urllib.request.Request("http://localhost:8081/v1/models", method="GET")
                with urllib.request.urlopen(req, timeout=1.5) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    models = [m["id"] for m in data.get("data", []) if "gemma" not in m["id"].lower()]
                    
                    if models != self.cached_models_list:
                        self.cached_models_list = models
                        self.model_menu.clear()
                        all_options = models if active_model in models else [active_model] + models
                        for model in all_options:
                            item = rumps.MenuItem(model, callback=self.select_model)
                            if model == active_model:
                                item.state = True
                            self.model_menu.add(item)
                
                # Perform a query check to verify the model is operational
                test_payload = {
                    "model": active_model,
                    "messages": [
                        {"role": "user", "content": "say true"}
                    ],
                    "max_tokens": 5
                }
                req_liveness = urllib.request.Request(
                    "http://localhost:8081/v1/chat/completions",
                    data=json.dumps(test_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                
                with urllib.request.urlopen(req_liveness, timeout=8.0) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    reply = res_data["choices"][0]["message"]["content"].strip().lower()
                    if len(reply) > 0:
                        display_name = active_model.split("/")[-1]
                        if len(display_name) > 28:
                            display_name = display_name[:25] + "..."
                        self.omlx_status.title = f"🟢 oMLX: {display_name}"
                    else:
                        self.omlx_status.title = f"🔴 oMLX: Model Empty Response"
            except Exception:
                display_name = active_model.split("/")[-1]
                if len(display_name) > 20:
                    display_name = display_name[:17] + "..."
                self.omlx_status.title = f"🔴 oMLX: Model Offline/Error ({display_name})"
        finally:
            self.is_updating = False

    def select_model(self, sender):
        if sender.title not in self.cached_models_list:
            rumps.alert("Model Select Error", f"Model '{sender.title}' is not currently loaded on the oMLX server.")
            return

        model_file = os.path.expanduser("~/.winnow/active_model")
        try:
            os.makedirs(os.path.dirname(model_file), exist_ok=True)
            with open(model_file, "w") as f:
                f.write(sender.title)
            rumps.notification("oMLX", "Active Model Pinned", f"Selected {sender.title.split('/')[-1]}")
            for name, item in self.model_menu.items():
                item.state = (name == sender.title)
        except Exception as e:
            rumps.alert(f"Error pinning model: {str(e)}")
        
        self.trigger_background_update(None)

    def toggle_winnow(self, sender):
        disabled_file = os.path.expanduser("~/.winnow/disabled")
        if os.path.exists(disabled_file):
            try:
                os.remove(disabled_file)
                rumps.notification("Winnow", "Proxy Activated", "Stable Moving Window Trimming is running.")
            except Exception as e:
                rumps.alert(f"Error enabling Winnow: {str(e)}")
        else:
            try:
                os.makedirs(os.path.dirname(disabled_file), exist_ok=True)
                with open(disabled_file, "w") as f:
                    f.write("disabled")
                rumps.notification("Winnow", "Proxy Paused", "Trimming disabled. All requests forwarded untouched.")
            except Exception as e:
                rumps.alert(f"Error disabling Winnow: {str(e)}")
        self.trigger_background_update(None)

    def restart_proxy(self, sender):
        try:
            res = subprocess.run("lsof -t -i :8787", shell=True, capture_output=True, text=True)
            pids = res.stdout.strip().split()
            if pids:
                for pid in pids:
                    subprocess.run(["kill", "-9", pid])
                rumps.notification("Winnow", "Proxy Restarted", "Launched fresh Winnow proxy instance.")
            else:
                rumps.notification("Winnow", "Offline", "No active Winnow proxy found on port 8787.")
        except Exception as e:
            rumps.alert(f"Error restarting Winnow: {str(e)}")
        self.trigger_background_update(None)

if __name__ == "__main__":
    app = WinnowMenuBarApp()
    app.run()

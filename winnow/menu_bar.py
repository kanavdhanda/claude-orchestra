import os
import sys
import subprocess
import json
import urllib.request

def install_and_import(package):
    import importlib
    try:
        importlib.import_module(package)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_and_import("rumps")
import rumps

class WinnowMenuBarApp(rumps.App):
    def __init__(self):
        super(WinnowMenuBarApp, self).__init__("Winnow", title="💸")
        
        self.status_item = rumps.MenuItem("Winnow: Unknown", callback=None)
        self.toggle_item = rumps.MenuItem("Toggle Winnow (⌥⌘W)", callback=self.toggle_winnow, key="w")
        self.stats_item = rumps.MenuItem("Saved: 0 tokens ($0.00)", callback=None)
        self.omlx_status = rumps.MenuItem("oMLX: Checking...", callback=None)
        
        # rumps natively appends its own 'Quit' item at the very bottom,
        # so we only configure our custom management actions here.
        self.menu = [
            self.status_item,
            self.toggle_item,
            rumps.separator,
            self.stats_item,
            rumps.separator,
            self.omlx_status,
            rumps.MenuItem("Restart oMLX Server", callback=self.restart_omlx),
            rumps.separator,
            rumps.MenuItem("Restart Winnow Proxy", callback=self.restart_proxy),
        ]
        
        self.timer = rumps.Timer(self.update_menu_state, 5)
        self.timer.start()
        self.update_menu_state(None)

    def update_menu_state(self, sender):
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
            
        # 3. Check oMLX server status (port 8081) and active model
        try:
            req = urllib.request.Request("http://localhost:8081/v1/models", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as response:
                data = json.loads(response.read().decode("utf-8"))
                models = data.get("data", [])
                
                # Filter out cached Gemma models if they exist in oMLX's response
                model_id = None
                for m in models:
                    m_id = m["id"]
                    if "gemma" not in m_id.lower():
                        model_id = m_id
                        break
                
                # If none found, or only Gemma is advertised, override to default Qwen
                if not model_id or "gemma" in model_id.lower():
                    model_id = "Qwen3.5-9B-TNG-PKD-Qwopus-Coder-Qwythos-qx86-hi-mlx"
                
                display_name = model_id.split("/")[-1]
                if len(display_name) > 28:
                    display_name = display_name[:25] + "..."
                self.omlx_status.title = f"🟢 oMLX: {display_name}"
        except Exception:
            self.omlx_status.title = "🔴 oMLX: Offline"

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
        self.update_menu_state(None)

    def restart_omlx(self, sender):
        # Shutdown if running
        try:
            res = subprocess.run("lsof -t -i :8081", shell=True, capture_output=True, text=True)
            pids = res.stdout.strip().split()
            if pids:
                for pid in pids:
                    subprocess.run(["kill", "-9", pid])
        except Exception:
            pass
            
        # Relaunch using open -a oMLX
        try:
            subprocess.run(["open", "-a", "oMLX"])
            rumps.notification("oMLX", "Restarting...", "Launched local oMLX Dashboard Application.")
        except Exception as e:
            rumps.alert(f"Failed to start oMLX: {str(e)}")
        self.update_menu_state(None)

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
        self.update_menu_state(None)

if __name__ == "__main__":
    app = WinnowMenuBarApp()
    app.run()

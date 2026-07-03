import os
import sys
import subprocess
import json
import urllib.request
import threading

def install_and_import(package):
    import importlib
    try:
        importlib.import_module(package)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_and_import("rumps")
import rumps

# Import winnow config dynamically
from winnow import config


def _ensure_bundle_identifier() -> None:
    """rumps.notification() goes through NSUserNotificationCenter, which
    refuses to activate for any process whose Info.plist lacks
    CFBundleIdentifier. Run via a pyenv-installed python.app (no bundled
    Info.plist at all, e.g. .../bin/Info.plist), that raises "Failed to
    setup the notification center" and kills the restart/toggle action
    that triggered it. Mutating NSBundle's in-memory infoDictionary doesn't
    work — NSUserNotificationCenter re-reads the plist from disk — so we
    write the actual Info.plist next to sys.executable, same fix macOS's
    own error dialog suggests via PlistBuddy."""
    try:
        plist_path = os.path.join(os.path.dirname(sys.executable), "Info.plist")
        if not os.path.exists(plist_path):
            subprocess.run(
                [
                    "/usr/libexec/PlistBuddy",
                    "-c",
                    "Add :CFBundleIdentifier string com.winnow.menubar",
                    plist_path,
                ],
                capture_output=True,
            )
    except Exception:
        pass


_ensure_bundle_identifier()

_ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "menu_icon.png")


def _ensure_menu_icon() -> str | None:
    """Renders the SF Symbol 'brain.head.profile' to a template PNG (black
    shape + alpha) so macOS auto-colors it white/black to match every other
    menu bar icon in light/dark mode. Generated once and cached to disk."""
    if os.path.exists(_ICON_PATH):
        return _ICON_PATH
    try:
        import AppKit

        symbol = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_("brain.head.profile", None)
        if symbol is None:
            return None
        cfg = AppKit.NSImageSymbolConfiguration.configurationWithPointSize_weight_scale_(18.0, 0.0, 2)
        scaled = symbol.imageWithSymbolConfiguration_(cfg) or symbol

        w, h = int(scaled.size().width * 2), int(scaled.size().height * 2)
        rep = AppKit.NSBitmapImageRep.alloc().initWithBitmapDataPlanes_pixelsWide_pixelsHigh_bitsPerSample_samplesPerPixel_hasAlpha_isPlanar_colorSpaceName_bytesPerRow_bitsPerPixel_(
            None, w, h, 8, 4, True, False, AppKit.NSDeviceRGBColorSpace, 0, 32
        )
        rep.setSize_((w, h))

        AppKit.NSGraphicsContext.saveGraphicsState()
        AppKit.NSGraphicsContext.setCurrentContext_(AppKit.NSGraphicsContext.graphicsContextWithBitmapImageRep_(rep))
        AppKit.NSColor.blackColor().set()
        scaled.drawInRect_fromRect_operation_fraction_(
            AppKit.NSMakeRect(0, 0, w, h), AppKit.NSZeroRect, AppKit.NSCompositingOperationSourceOver, 1.0
        )
        AppKit.NSGraphicsContext.restoreGraphicsState()

        os.makedirs(os.path.dirname(_ICON_PATH), exist_ok=True)
        rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, None).writeToFile_atomically_(_ICON_PATH, True)
        return _ICON_PATH
    except Exception:
        return None


def _power_status() -> str:
    try:
        out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=2.0).stdout
        first_line = out.splitlines()[0] if out else ""
        on_ac = "AC Power" in first_line
        low_power = "lowpowermode" in out.lower() and "1" in out.lower().split("lowpowermode")[-1][:5]
        pct = ""
        for line in out.splitlines():
            if "%" in line:
                pct = line.strip().split(";")[0].split("\t")[-1].strip()
                break
        label = f"🔌 AC Power" if on_ac else f"🔋 Battery {pct}".strip()
        if low_power:
            label += " (Low Power Mode)"
        return label
    except Exception:
        return "Power: Unknown"


class WinnowMenuBarApp(rumps.App):
    def __init__(self):
        icon_path = _ensure_menu_icon()
        if icon_path:
            super(WinnowMenuBarApp, self).__init__("Winnow", title="", icon=icon_path, template=True)
        else:
            super(WinnowMenuBarApp, self).__init__("Winnow", title="🧠")

        self.status_item = rumps.MenuItem("Winnow: Unknown", callback=None)
        self.toggle_item = rumps.MenuItem("Toggle Winnow (⌥⌘W)", callback=self.toggle_winnow, key="w")
        self.stats_item = rumps.MenuItem("Saved: 0 tokens ($0.00)", callback=None)
        self.power_item = rumps.MenuItem("Power: Checking...", callback=None)

        self.menu = [
            self.status_item,
            self.toggle_item,
            rumps.separator,
            self.stats_item,
            rumps.separator,
            self.power_item,
            rumps.separator,
            rumps.MenuItem("Restart Winnow Proxy", callback=self.restart_proxy),
        ]

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
                
            # 3. Update power-state
            self.power_item.title = _power_status()
        finally:
            self.is_updating = False

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

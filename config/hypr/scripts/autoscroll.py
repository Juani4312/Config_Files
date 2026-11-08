#!/usr/bin/env python3
"""
autoscroll.py - Windows-style middle-click autoscroll (evdev + uinput).

  * Shift + tap the wheel  -> autoscroll locks. Move the mouse up/down: the
                              further from the start point, the faster it
                              scrolls. Any click (or the wheel) ends it.
  * Shift + hold + drag    -> scrolls while held, release to stop.

The pointer is frozen while autoscrolling, so the window under it keeps
receiving the scroll. Plain middle-click passes through as a normal middle
click (close tab, paste, open in new tab); Shift + middle-click starts autoscroll.
Shift state comes from Hyprland binds (configs/keybinds.lua) that send
"shift1"/"shift0" to $XDG_RUNTIME_DIR/autoscroll-ctl.sock, so this daemon
never needs to read the keyboard.

Grabs every real mouse exclusively and re-emits its events through a single
virtual uinput mouse. If this process dies, the grab is released by the kernel
and the mice work normally again.

Needs read access to /dev/input/event* for mice (udev uaccess rule) and
write access to /dev/uinput.  Stop it: systemctl --user stop autoscroll
"""
import math
import os
import select
import socket
import sys
import time

import evdev
from evdev import UInput, ecodes as e

RUNTIME = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
CTL_SOCK = os.path.join(RUNTIME, "autoscroll-ctl.sock")
SHIFT_TIMEOUT = 30.0     # forget a Shift press if its release never arrives

# indicator bubble (autoscroll-indicator.py); silently ignored if not running
NOTIFY_SOCK = os.path.join(RUNTIME, "autoscroll.sock")
_notify = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
_notify.setblocking(False)


def notify(msg):
    try:
        _notify.sendto(msg.encode(), NOTIFY_SOCK)
    except OSError:
        pass

# ---------------------------------------------------------------- tuning ----
DEADZONE       = 12      # counts (~px) around the anchor with no scrolling
DRAG_THRESHOLD = 6       # movement while held that turns a tap into a drag
SCALE          = 40.0    # counts past the deadzone that give 1 notch/s
EXPONENT       = 1.6     # >1: speed grows faster the further you move
MAX_NOTCHES_S  = 120.0   # speed cap (1 notch = 1 wheel click)
MAX_OFFSET     = 2000    # clamp virtual offset so you can always come back
HORIZONTAL     = False   # also scroll horizontally with x movement
INVERT         = False   # True: moving the mouse down scrolls up
TICK_HZ        = 120     # scroll event rate while active
RESCAN_S       = 3.0     # how often to look for new (hotplugged) mice
VNAME          = "autoscroll-virtual-mouse"
# ----------------------------------------------------------------------------

BUTTONS = list(range(e.BTN_LEFT, e.BTN_TASK + 1))
CAPS = {
    e.EV_KEY: BUTTONS,
    e.EV_REL: [e.REL_X, e.REL_Y, e.REL_WHEEL, e.REL_HWHEEL,
               e.REL_WHEEL_HI_RES, e.REL_HWHEEL_HI_RES],
    e.EV_MSC: [e.MSC_SCAN],
}
WHEEL_CODES = {e.REL_WHEEL, e.REL_HWHEEL, e.REL_WHEEL_HI_RES, e.REL_HWHEEL_HI_RES}


def log(*a):
    print("autoscroll:", *a, file=sys.stderr, flush=True)


def is_mouse(dev):
    caps = dev.capabilities()
    rel = caps.get(e.EV_REL, [])
    keys = caps.get(e.EV_KEY, [])
    return e.REL_X in rel and e.REL_Y in rel and e.BTN_MIDDLE in keys


def speed(d):
    """Signed notches/second for an offset of d counts from the anchor."""
    a = abs(d) - DEADZONE
    if a <= 0:
        return 0.0
    return math.copysign(min((a / SCALE) ** EXPONENT, MAX_NOTCHES_S), d)


class Axis:
    """Accumulates fractional hi-res wheel units and emits whole ones."""

    def __init__(self, hires_code, lowres_code):
        self.hires_code, self.lowres_code = hires_code, lowres_code
        self.reset()

    def reset(self):
        self.frac = 0.0     # not yet emitted hi-res units
        self.notch = 0      # emitted hi-res units not yet turned into a notch

    def step(self, ui, notches_per_s, dt):
        self.frac += notches_per_s * 120.0 * dt
        n = int(self.frac)
        if not n:
            return False
        self.frac -= n
        ui.write(e.EV_REL, self.hires_code, n)
        self.notch += n
        low = int(self.notch / 120)          # truncates toward zero
        if low:
            self.notch -= low * 120
            ui.write(e.EV_REL, self.lowres_code, low)
        return True


class Autoscroll:
    def __init__(self):
        self.ui = UInput(CAPS, name=VNAME, vendor=0x1d6b, product=0xa5c0)
        self.devs = {}          # fd -> InputDevice
        self.rejected = set()   # paths that are not mice
        self.swallow = set()    # buttons whose release/repeat must be dropped
        self.active = False
        self.held = False       # middle still physically down since start
        self.moved = False      # moved past DRAG_THRESHOLD while held
        self.dx = self.dy = 0
        self.vy = Axis(e.REL_WHEEL_HI_RES, e.REL_WHEEL)
        self.vx = Axis(e.REL_HWHEEL_HI_RES, e.REL_HWHEEL)
        self.last_tick = 0.0
        self.last_scan = 0.0
        self.shift_since = None  # monotonic time Shift went down, None if up
        try:
            os.unlink(CTL_SOCK)
        except FileNotFoundError:
            pass
        self.ctl = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        self.ctl.bind(CTL_SOCK)
        self.ctl.setblocking(False)

    def shift_down(self):
        if self.shift_since is None:
            return False
        if time.monotonic() - self.shift_since > SHIFT_TIMEOUT:
            self.shift_since = None
            return False
        return True

    def read_ctl(self):
        while True:
            try:
                msg = self.ctl.recv(64).strip()
            except BlockingIOError:
                return
            except OSError:
                return
            if msg == b"shift1":
                self.shift_since = time.monotonic()
            elif msg == b"shift0":
                self.shift_since = None

    # ------------------------------------------------------------ devices --
    def scan(self):
        self.last_scan = time.monotonic()
        paths = set(evdev.list_devices())
        self.rejected &= paths
        open_paths = {d.path for d in self.devs.values()}
        for path in sorted(paths - open_paths - self.rejected):
            try:
                dev = evdev.InputDevice(path)
            except OSError:
                continue
            if dev.name == VNAME or not is_mouse(dev):
                dev.close()
                self.rejected.add(path)
                continue
            try:
                dev.grab()
            except OSError as ex:
                log(f"cannot grab {path} ({dev.name}): {ex}")
                dev.close()
                self.rejected.add(path)
                continue
            self.devs[dev.fd] = dev
            log(f"grabbed {path}: {dev.name}")

    def drop(self, fd):
        dev = self.devs.pop(fd, None)
        if dev:
            log(f"lost {dev.path}: {dev.name}")
            try:
                dev.close()
            except OSError:
                pass

    # -------------------------------------------------------------- state --
    def start(self):
        self.active, self.held, self.moved = True, True, False
        self.dx = self.dy = 0
        self.vy.reset()
        self.vx.reset()
        self.last_tick = time.monotonic()
        self.sent_v, self.sent_t = 0.0, 0.0
        notify("start")

    def stop(self):
        if self.active:
            notify("stop")
        self.active = self.held = False

    def tick(self):
        now = time.monotonic()
        dt = min(now - self.last_tick, 0.1)
        self.last_tick = now
        vy = -speed(self.dy)                 # mouse down -> scroll down
        if INVERT:
            vy = -vy
        if abs(-vy - self.sent_v) > 0.2 and now - self.sent_t > 0.03:
            self.sent_v, self.sent_t = -vy, now
            notify(f"v {-vy:.2f}")            # + = content moving down
        wrote = self.vy.step(self.ui, vy, dt)
        if HORIZONTAL:
            vx = speed(self.dx)
            if INVERT:
                vx = -vx
            wrote |= self.vx.step(self.ui, vx, dt)
        if wrote:
            self.ui.syn()

    # ------------------------------------------------------------- events --
    def handle(self, ev):
        t, c, v = ev.type, ev.code, ev.value

        if t == e.EV_KEY:
            if v == 1:
                if self.active:              # any press ends autoscroll
                    self.stop()
                    self.swallow.add(c)
                    return
                if c == e.BTN_MIDDLE:
                    if not self.shift_down():  # plain middle -> normal click
                        self.ui.write(t, c, v)
                        return
                    self.start()
                    self.swallow.add(c)
                    return
            elif v == 0:
                if c == e.BTN_MIDDLE and self.active and self.held:
                    self.held = False
                    if self.moved:           # hold + drag -> stop on release
                        self.stop()
                    # tap -> stays locked
                    self.swallow.discard(c)
                    return
                if c in self.swallow:
                    self.swallow.discard(c)
                    return
            elif c in self.swallow:          # autorepeat of a swallowed key
                return

        elif t == e.EV_REL and self.active:
            if c in (e.REL_X, e.REL_Y):
                if c == e.REL_X:
                    self.dx = max(-MAX_OFFSET, min(MAX_OFFSET, self.dx + v))
                else:
                    self.dy = max(-MAX_OFFSET, min(MAX_OFFSET, self.dy + v))
                if self.held and math.hypot(self.dx, self.dy) > DRAG_THRESHOLD:
                    self.moved = True
                return                       # pointer stays frozen
            if c in WHEEL_CODES:             # real wheel cancels autoscroll
                self.stop()

        elif t == e.EV_MSC:
            return

        self.ui.write(t, c, v)

    # --------------------------------------------------------------- loop --
    def run(self):
        self.scan()
        if not self.devs:
            log("no mouse could be grabbed (permissions?); will keep retrying")
        period = 1.0 / TICK_HZ
        while True:
            timeout = period if self.active else RESCAN_S
            try:
                ready, _, _ = select.select([self.ctl.fileno(), *self.devs], [], [], timeout)
            except (OSError, ValueError):
                ready = []
            if self.ctl.fileno() in ready:   # before mouse events of this round
                self.read_ctl()
            for fd in ready:
                dev = self.devs.get(fd)
                if not dev:
                    continue
                try:
                    for ev in dev.read():
                        self.handle(ev)
                except BlockingIOError:
                    pass
                except OSError:
                    self.drop(fd)
            now = time.monotonic()
            if self.active and now - self.last_tick >= period:
                self.tick()
            if now - self.last_scan >= RESCAN_S:
                self.scan()


def main():
    app = Autoscroll()
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        for dev in list(app.devs.values()):
            try:
                dev.ungrab()
                dev.close()
            except OSError:
                pass
        app.ui.close()


if __name__ == "__main__":
    main()

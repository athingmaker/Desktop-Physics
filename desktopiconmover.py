import ctypes
from ctypes import wintypes
import time
import math
import random
import pyautogui

LRESULT = ctypes.c_long

LVM_FIRST = 0x1000
LVM_SETITEMPOSITION = LVM_FIRST + 15
LVM_GETITEMCOUNT = LVM_FIRST + 4

SM_CXSCREEN = 0
SM_CYSCREEN = 1

user32 = ctypes.WinDLL('user32', use_last_error=True)

FindWindow = user32.FindWindowW
FindWindow.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
FindWindow.restype = wintypes.HWND

FindWindowEx = user32.FindWindowExW
FindWindowEx.argtypes = [wintypes.HWND, wintypes.HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
FindWindowEx.restype = wintypes.HWND

SendMessage = user32.SendMessageW
SendMessage.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
SendMessage.restype = LRESULT

GetSystemMetrics = user32.GetSystemMetrics
GetSystemMetrics.argtypes = [wintypes.INT]
GetSystemMetrics.restype = wintypes.INT

def get_desktop_listview():
    progman = FindWindow("Progman", None)
    shell_view = FindWindowEx(progman, None, "SHELLDLL_DefView", None)
    desktop_listview = FindWindowEx(shell_view, None, "SysListView32", None)
    if not desktop_listview:
        workerw = FindWindowEx(None, progman, "WorkerW", None)
        shell_view = FindWindowEx(workerw, None, "SHELLDLL_DefView", None)
        desktop_listview = FindWindowEx(shell_view, None, "SysListView32", None)
    if not desktop_listview:
        raise Exception("Could not find desktop ListView handle")
    return desktop_listview

def get_icon_count(listview):
    return SendMessage(listview, LVM_GETITEMCOUNT, 0, 0)

def move_desktop_icon(listview, index, x, y):

    screen_width = GetSystemMetrics(SM_CXSCREEN)
    screen_height = GetSystemMetrics(SM_CYSCREEN)
    x = max(0, min(x, screen_width - 1))
    y = max(0, min(y, screen_height - 1))

    lparam = (y << 16) | (x & 0xFFFF)
    return SendMessage(listview, LVM_SETITEMPOSITION, index, lparam)

class Particle:
    def __init__(self, index, x, y, radius=25):
        self.index = index
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.radius = radius

    def apply_force(self, fx, fy):
        self.vx += fx
        self.vy += fy

    def update(self, dt):
        max_speed = 300
        self.x += self.vx * dt
        self.y += self.vy * dt

        speed = math.sqrt(self.vx ** 2 + self.vy ** 2)
        if speed > max_speed:
            scale = max_speed / speed
            self.vx *= scale
            self.vy *= scale

        damping = 0.92
        self.vx *= damping
        self.vy *= damping

    def check_collision(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        return dist < (self.radius + other.radius)

    def resolve_collision(self, other):
        dx = other.x - self.x
        dy = other.y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist == 0:
            dist = 0.1
        overlap = (self.radius + other.radius) - dist
        separation_strength = 5.0
        fx = -(dx / dist) * overlap * separation_strength
        fy = -(dy / dist) * overlap * separation_strength
        self.apply_force(fx, fy)
        other.apply_force(-fx, -fy)
        correction_factor = 0.5
        self.x -= correction_factor * overlap * (dx / dist)
        self.y -= correction_factor * overlap * (dy / dist)
        other.x += correction_factor * overlap * (dx / dist)
        other.y += correction_factor * overlap * (dy / dist)

def physics_simulation():
    listview = get_desktop_listview()
    icon_count = get_icon_count(listview)
    screen_width = GetSystemMetrics(SM_CXSCREEN)
    screen_height = GetSystemMetrics(SM_CYSCREEN)
    center_x, center_y = screen_width / 2, screen_height / 2

    radius = 200
    particles = []
    for i in range(icon_count):
        angle = 2 * math.pi * i / icon_count
        x = center_x + radius * math.cos(angle)
        y = center_y + radius * math.sin(angle)
        p = Particle(i, x, y)
        particles.append(p)

    center_gravity_strength = 0  
    particle_gravity_strength = 1500000.0  
    dt = 0.03

    mouse_influence_radius = 150
    mouse_repulsion_strength = 1000000000.0

    try:
        while True:
            mx, my = pyautogui.position()  

            for i, p in enumerate(particles):
                dx = center_x - p.x
                dy = center_y - p.y
                dist_center = math.sqrt(dx * dx + dy * dy) + 0.01
                fx = (dx / dist_center) * center_gravity_strength * dt
                fy = (dy / dist_center) * center_gravity_strength * dt

                for j, other in enumerate(particles):
                    if i == j:
                        continue
                    dxo = other.x - p.x
                    dyo = other.y - p.y
                    dist = math.sqrt(dxo * dxo + dyo * dyo) + 0.01
                    f = (particle_gravity_strength * dt) / (dist * dist)
                    fx += (dxo / dist) * f
                    fy += (dyo / dist) * f

                mdx = p.x - mx
                mdy = p.y - my
                mdist = math.sqrt(mdx * mdx + mdy * mdy)
                if mdist < mouse_influence_radius and mdist > 0:
                    repulse_force = (mouse_repulsion_strength / (mdist * mdist)) * dt
                    fx += (mdx / mdist) * repulse_force
                    fy += (mdy / mdist) * repulse_force

                jitter_strength = 15.0
                fx += (random.uniform(-jitter_strength, jitter_strength) * dt)
                fy += (random.uniform(-jitter_strength, jitter_strength) * dt)

                p.apply_force(fx, fy)

            for p in particles:
                p.update(dt)

                p.x = max(p.radius, min(p.x, screen_width - p.radius))
                p.y = max(p.radius, min(p.y, screen_height - p.radius))

            for i in range(len(particles)):
                for j in range(i + 1, len(particles)):
                    p1 = particles[i]
                    p2 = particles[j]
                    if p1.check_collision(p2):
                        p1.resolve_collision(p2)

            for p in particles:
                move_desktop_icon(listview, p.index, int(p.x), int(p.y))
    except KeyboardInterrupt:
        print("Physics simulation stopped.")

if __name__ == "__main__":
    physics_simulation()
import json
import time
import ctypes
from ctypes import wintypes
import sys
from typing import Optional

from memory import Memory
from signature_scanner import SignatureScanner

# Windows virtual key codes
VK_F1 = 0x70
VK_F2 = 0x71
VK_F3 = 0x72
VK_F4 = 0x73

class Trainer:
    def __init__(self):
        self.infinite_oxygen_active = False
        self.ignore_craft_active = False
        self.ghost_active = False
        self.speed_multiplier = 1.0
        self.speed_index = 0  # 0:1.0, 1:1.5, 2:2.0, 3:3.0

        self.process_handle = None
        self.pid = None
        self.module_base = None
        self.module_size = None

        self.oxygen_addr = None
        self.craft_addr = None
        self.ghost_addr = None
        self.speed_addr = None

        self.prev_f1 = False
        self.prev_f2 = False
        self.prev_f3 = False
        self.prev_f4 = False

        self.user32 = ctypes.windll.user32

    def initialize(self, config_path: str) -> bool:
        print("[*] Initializing trainer...")
        # Find game process
        process_name = "Gothic1Remake.exe"
        self.pid = Memory.get_process_id_by_name(process_name)
        if not self.pid:
            print("[!] Game process not found. Is the game running?")
            return False

        try:
            self.process_handle = Memory.open_process(self.pid)
        except Exception as e:
            print(f"[!] Failed to open process: {e}. Run as administrator.")
            return False

        # Get module base address
        self.module_base = Memory.get_module_base_address(self.pid, process_name)
        if not self.module_base:
            print("[!] Could not find module base.")
            return False

        # Get module size (using psutil)
        import psutil
        try:
            proc = psutil.Process(self.pid)
            for mmap in proc.memory_maps(grouped=False):
                if mmap.path and mmap.path.endswith(process_name):
                    # approximate size by taking the last address in the mapping?
                    # Actually we need the size of the image. A simpler way: use module information from kernel32.
                    # We'll use GetModuleInformation via ctypes.
                    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
                    class MODULEINFO(ctypes.Structure):
                        _fields_ = [
                            ('lpBaseOfDll', ctypes.c_void_p),
                            ('SizeOfImage', ctypes.c_ulong),
                            ('EntryPoint', ctypes.c_void_p),
                        ]
                    mod_info = MODULEINFO()
                    if kernel32.GetModuleInformation(self.process_handle, self.module_base, ctypes.byref(mod_info), ctypes.sizeof(mod_info)):
                        self.module_size = mod_info.SizeOfImage
                        break
        except Exception as e:
            print(f"[!] Could not get module size: {e}")
            return False

        if not self.module_size:
            print("[!] Module size not found.")
            return False

        # Resolve addresses
        if not self.resolve_addresses(config_path):
            print("[!] Failed to resolve addresses.")
            return False

        print(f"[+] Trainer initialized. PID: {self.pid}, Base: 0x{self.module_base:X}, Size: 0x{self.module_size:X}")
        print("[+] Hotkeys: F1=Oxygen, F2=Craft, F3=Ghost, F4=Speed")
        return True

    def resolve_addresses(self, config_path: str) -> bool:
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] Error loading offsets.json: {e}")
            return False

        sigs = data.get('signatures', {})
        offs = data.get('offsets', {})

        def resolve(name: str) -> Optional[int]:
            # Try signature first
            if name in sigs:
                pattern = sigs[name]
                addr = SignatureScanner.scan_module(self.process_handle, self.module_base, self.module_size, pattern)
                if addr:
                    print(f"[+] Resolved {name} by signature at 0x{addr:X}")
                    return addr
            # Fallback to offset
            off_key = name + "_offset"
            if off_key in offs:
                offset = offs[off_key]
                addr = self.module_base + offset
                print(f"[+] Resolved {name} by offset 0x{offset:X} -> 0x{addr:X}")
                return addr
            print(f"[!] Failed to resolve {name}")
            return None

        self.oxygen_addr = resolve('oxygen')
        self.craft_addr = resolve('craft_requirement')
        self.ghost_addr = resolve('ghost')
        self.speed_addr = resolve('speed')

        return all([self.oxygen_addr, self.craft_addr, self.ghost_addr, self.speed_addr])

    def write_byte(self, addr: int, value: int) -> bool:
        return Memory.write_process_memory(self.process_handle, addr, value.to_bytes(1, 'little'))

    def write_float(self, addr: int, value: float) -> bool:
        import struct
        bytes_data = struct.pack('<f', value)
        return Memory.write_process_memory(self.process_handle, addr, bytes_data)

    def toggle_oxygen(self):
        self.infinite_oxygen_active = not self.infinite_oxygen_active
        val = 0x00 if self.infinite_oxygen_active else 0x01
        if self.write_byte(self.oxygen_addr, val):
            print(f"[*] Infinite Oxygen: {'ON' if self.infinite_oxygen_active else 'OFF'}")
        else:
            print("[!] Failed to write oxygen memory")

    def toggle_craft(self):
        self.ignore_craft_active = not self.ignore_craft_active
        val = 0x01 if self.ignore_craft_active else 0x00
        if self.write_byte(self.craft_addr, val):
            print(f"[*] Ignore Craft Requirements: {'ON' if self.ignore_craft_active else 'OFF'}")
        else:
            print("[!] Failed to write craft memory")

    def toggle_ghost(self):
        self.ghost_active = not self.ghost_active
        val = 0x01 if self.ghost_active else 0x00
        if self.write_byte(self.ghost_addr, val):
            print(f"[*] Ghost Mode: {'ON' if self.ghost_active else 'OFF'}")
        else:
            print("[!] Failed to write ghost memory")

    def cycle_speed(self):
        speeds = [1.0, 1.5, 2.0, 3.0]
        self.speed_index = (self.speed_index + 1) % 4
        self.speed_multiplier = speeds[self.speed_index]
        if self.write_float(self.speed_addr, self.speed_multiplier):
            print(f"[*] Speed Multiplier: {self.speed_multiplier}x")
        else:
            print("[!] Failed to write speed memory")

    def run(self):
        print("[*] Trainer running. Press F1-F4 to toggle features. Close console to exit.")
        try:
            while True:
                f1 = (self.user32.GetAsyncKeyState(VK_F1) & 0x8000) != 0
                f2 = (self.user32.GetAsyncKeyState(VK_F2) & 0x8000) != 0
                f3 = (self.user32.GetAsyncKeyState(VK_F3) & 0x8000) != 0
                f4 = (self.user32.GetAsyncKeyState(VK_F4) & 0x8000) != 0

                if f1 and not self.prev_f1:
                    self.toggle_oxygen()
                if f2 and not self.prev_f2:
                    self.toggle_craft()
                if f3 and not self.prev_f3:
                    self.toggle_ghost()
                if f4 and not self.prev_f4:
                    self.cycle_speed()

                self.prev_f1 = f1
                self.prev_f2 = f2
                self.prev_f3 = f3
                self.prev_f4 = f4

                time.sleep(0.05)
        except KeyboardInterrupt:
            print("[*] Trainer stopped by user.")
        finally:
            if self.process_handle:
                Memory.close_handle(self.process_handle)

import ctypes
import ctypes.wintypes
import psutil
from typing import Optional, Tuple

# Windows API constants
PROCESS_ALL_ACCESS = 0x1F0FFF
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPMODULE32 = 0x00000010

class Memory:
    @staticmethod
    def get_process_id_by_name(process_name: str) -> Optional[int]:
        """Return PID of the first process with given name."""
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                return proc.info['pid']
        return None

    @staticmethod
    def open_process(pid: int) -> int:
        """Open process with all access and return handle."""
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        handle = kernel32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        return handle

    @staticmethod
    def close_handle(handle: int) -> None:
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.CloseHandle(handle)

    @staticmethod
    def get_module_base_address(pid: int, module_name: str) -> Optional[int]:
        """Return base address of a module in the target process."""
        import psutil
        try:
            proc = psutil.Process(pid)
            for mmap in proc.memory_maps(grouped=False):
                if mmap.path and mmap.path.endswith(module_name):
                    return int(mmap.addr, 16)
        except psutil.NoSuchProcess:
            return None
        return None

    @staticmethod
    def read_process_memory(handle: int, address: int, size: int) -> Optional[bytes]:
        """Read memory from process."""
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        buffer = ctypes.create_string_buffer(size)
        bytes_read = ctypes.c_size_t(0)
        if kernel32.ReadProcessMemory(handle, address, buffer, size, ctypes.byref(bytes_read)):
            return buffer.raw[:bytes_read.value]
        return None

    @staticmethod
    def write_process_memory(handle: int, address: int, data: bytes) -> bool:
        """Write memory to process."""
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        bytes_written = ctypes.c_size_t(0)
        result = kernel32.WriteProcessMemory(handle, address, data, len(data), ctypes.byref(bytes_written))
        return result != 0 and bytes_written.value == len(data)

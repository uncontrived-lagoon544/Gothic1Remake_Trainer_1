import re
from typing import List, Tuple, Optional

class SignatureScanner:
    @staticmethod
    def parse_pattern(hex_pattern: str) -> Tuple[List[int], str]:
        """Convert hex pattern like '48 8B 05 ?? ?? ?? ??' to bytes and mask."""
        pattern_bytes = []
        mask = ''
        for token in hex_pattern.split():
            if token == '??':
                pattern_bytes.append(0)
                mask += '?'
            elif re.match(r'^[0-9A-Fa-f]{2}$', token):
                pattern_bytes.append(int(token, 16))
                mask += 'x'
            else:
                raise ValueError(f"Invalid token: {token}")
        return pattern_bytes, mask

    @staticmethod
    def scan_module(handle: int, base: int, size: int, hex_pattern: str) -> Optional[int]:
        """Scan module memory for a pattern and return address of first match."""
        pattern_bytes, mask = SignatureScanner.parse_pattern(hex_pattern)
        if not pattern_bytes:
            return None

        # Read entire module
        buffer = Memory.read_process_memory(handle, base, size)
        if not buffer:
            return None

        # Search
        for i in range(len(buffer) - len(pattern_bytes) + 1):
            match = True
            for j, (pbyte, mchar) in enumerate(zip(pattern_bytes, mask)):
                if mchar == 'x' and buffer[i+j] != pbyte:
                    match = False
                    break
            if match:
                return base + i
        return None

# Import Memory after definition (circular safe)
from memory import Memory

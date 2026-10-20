import ipaddress

# 26 + 26 + 10 + 6 = 68 symbols, all typeable on a normal keyboard
ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789,.;:-_"
BASE = len(ALPHABET)

PIN_DIGITS = 4                 # PIN is a number from 0000 to 9999
PIN_SPACE = 10 ** PIN_DIGITS

# Every possible (ip, port, pin) combination
TOTAL = (2 ** 32) * (2 ** 16) * PIN_SPACE

# Smallest code length that can represent all combinations
LENGTH = 1
while BASE ** LENGTH < TOTAL:
    LENGTH += 1


def encode(ip: str, port: int, pin: int) -> str:
    ip_int = int(ipaddress.IPv4Address(ip))
    if not 0 <= port <= 65535:
        raise ValueError("port must be 0-65535")
    if not 0 <= pin < PIN_SPACE:
        raise ValueError(f"pin must be 0-{PIN_SPACE - 1}")

    # Pack everything into one big integer (ip | port | pin)
    n = ((ip_int << 16) | port) * PIN_SPACE + pin

    # Write that integer in base 68, padded to a fixed length
    chars = []
    for _ in range(LENGTH):
        n, rem = divmod(n, BASE)
        chars.append(ALPHABET[rem])
    return "".join(reversed(chars))


def decode(code: str):
    code = code.strip()
    if len(code) != LENGTH or any(c not in ALPHABET for c in code):
        raise ValueError(f"invalid code (expected {LENGTH} characters from the allowed set)")

    n = 0
    for c in code:
        n = n * BASE + ALPHABET.index(c)

    n, pin = divmod(n, PIN_SPACE)
    port = n & 0xFFFF
    ip_int = n >> 16
    if ip_int >= 2 ** 32:
        raise ValueError("invalid code")
    return str(ipaddress.IPv4Address(ip_int)), port, pin

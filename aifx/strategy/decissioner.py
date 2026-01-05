"""Decision helpers.

This module converts algorithm outputs (e.g. Magic Lines) into a trade decision.

Conventions:
- Returns: "BUY", "SELL", or "NONE"
"""

from __future__ import annotations


def _parse_line_offsets(result: str) -> dict[str, float]:
    """Parse `magic_lines.process_single_file()` output into {line_id: offset}.

    Expected format:
        CROSSED <IDs...> <UP|DOWN> | D0: -95.57 | ... | A0: 147.94 | ... | SLOPE: 0.1234

    Offsets are expressed as: (line_value - last_close).
    """

    offsets: dict[str, float] = {}

    for chunk in result.split("|")[1:]:
        chunk = chunk.strip()
        if not chunk or ":" not in chunk:
            continue

        key, value = chunk.split(":", 1)
        key = key.strip()
        value = value.strip()

        if not key or key.upper() == "SLOPE":
            continue

        try:
            offsets[key] = float(value)
        except ValueError:
            # Ignore malformed entries.
            continue

    return offsets


def decision(result: str | None) -> str:
    """Map magic_lines.process_single_file() result string to an order type.

    example:
    CROSSED AR1 DOWN | D0: -95.57 | DR1: -273.62 | DS1: 420.07 | A0: 147.94 | AR1: 18.28 | AS1: 683.76
    """

    if not result:
        return "log: no result\nNONE"

    header = result.split('|', 1)[0].strip()

    if not header.startswith("CROSSED"):
        return "log: no crossed\nNONE"

    parts = header.split()
    if not parts:
        return "log: invalid input string\nNONE"
    
    line_id = parts[1]
    direction = parts[2]
    if direction not in ("UP", "DOWN"):
        return f"log: invalid direction: {direction}\nNONE"

    offsets = _parse_line_offsets(result)
    d0_offset = offsets.get("D0")
    a0_offset = offsets.get("A0")

    if "A" in line_id:
        if direction == "UP":
            # Do not buy below D0 (i.e. last_close < D0 => D0 offset > 0).
            if d0_offset is not None and d0_offset > 0:
                return "log: do not buy below D0\nNONE"
            return "BUY"
        elif direction == "DOWN":
            return "log: bad direction\nNONE"

    if "D" in line_id:
        if direction == "DOWN":
            # Do not sell above A0 (i.e. last_close > A0 => A0 offset < 0).
            if a0_offset is not None and a0_offset < 0:
                return "log: do not sell above A0\nNONE"
            return "SELL"
        elif direction == "UP":
            return "log: bad direction\nNONE"
        
    return f"log: bad line id: {line_id}\nNONE"

if __name__ == '__main__':  
    # Example usage
    example_result = "CROSSED DS1 DS2 DOWN | D0: -46.56 | DR1: -166.39 | DR2: -293.96 | DS1: -6.40 | DS2: 70.88 | A0: 935.41 | AR1: 400.80 | AS1: 1383.09 | SLOPE: -3.0436 | BASE: 21222.78"
    print(decision(example_result))

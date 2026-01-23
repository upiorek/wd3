"""Decision helpers.

This module converts algorithm outputs (e.g. Magic Lines) into a trade decision.

Conventions:
- Returns: "BUY", "SELL", or "NONE"
"""

from __future__ import annotations

def version() -> str:
    """Return module version info."""
    return "decissioner 1.2"

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

def _find_extreme_line(crossed_ids: list[str], offsets: dict[str, float], prefix: str) -> float | None:
    """Find the extreme (highest or lowest) line with given prefix and return its offset + BASE.
    
    Args:
        crossed_ids: List of crossed line IDs.
        offsets: Dictionary of line offsets.
        prefix: Line prefix to filter by ("A" finds highest, "D" finds lowest).
    
    Returns:
        The extreme offset + BASE, or None if no valid line is found.
    """
    find_max = (prefix == "A")
    extreme_offset: float | None = None
    for line_id in crossed_ids:
        if not line_id.startswith(prefix):
            continue
        offset = offsets.get(line_id)
        if offset is None:
            continue
        if extreme_offset is None or (offset > extreme_offset if find_max else offset < extreme_offset):
            extreme_offset = offset
    
    # add offset to base
    base_offset = offsets.get("BASE")
    if extreme_offset is not None and base_offset is not None:
        extreme_offset += base_offset
    
    return extreme_offset

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

    direction = parts[-1]
    if direction not in ("UP", "DOWN"):
        return f"log: invalid direction: {direction}\nNONE"

    offsets = _parse_line_offsets(result)

    crossed_ids = parts[1:-1]
    if not crossed_ids:
        return "log: no line ids\nNONE"
    
    near_offsets = {k: v for k, v in offsets.items() if abs(v) < 5.0}
    near_letters = {
        (k[:1].upper() if k else "")
        for k in near_offsets.keys()
        if k and k[:1].upper() in ("A", "D")
    }

    #if "A" in near_letters and "D" in near_letters:
    #    return "log: both A and D within 5 of base\nNONE"

    d0_offset = offsets.get("D0")
    a0_offset = offsets.get("A0")

    # Unified logic for both single- and multi-cross:
    # - If direction is UP and any crossed line is A*, then BUY.
    # - If direction is DOWN and any crossed line is D*, then SELL.
    first_letters = [(line_id[:1].upper() if line_id else "") for line_id in crossed_ids]
    has_a = "A" in first_letters
    has_d = "D" in first_letters

    can_buy = (direction == "UP" and has_a)
    can_sell = (direction == "DOWN" and has_d)

    if can_buy:
        # Do not buy below D0 (i.e. last_close < D0 => D0 offset > 0).
        if d0_offset is not None and d0_offset > 0:
            return "log: do not buy below D0\nNONE"
        
        highest_a_offset = _find_extreme_line(crossed_ids, offsets, "A")
        return "BUY" + (f" ABOVE {highest_a_offset:.2f}" if highest_a_offset is not None else "")

    if can_sell:
        # Do not sell above A0 (i.e. last_close > A0 => A0 offset < 0).
        if a0_offset is not None and a0_offset < 0:
            return "log: do not sell above A0\nNONE"

        lowest_d_offset = _find_extreme_line(crossed_ids, offsets, "D")
        return "SELL" + (f" BELOW {lowest_d_offset:.2f}" if lowest_d_offset is not None else "")

    # No valid lines matched the direction.
    if len(crossed_ids) > 1:
        return "log: no valid lines found\nNONE"

    line_id = crossed_ids[0]
    line_letter = line_id[:1].upper() if line_id else ""
    if line_letter in ("A", "D"):
        return "log: bad direction\nNONE"

    return f"log: bad line id: {line_id}\nNONE"

if __name__ == '__main__':  
    # Example usage
    example_result = "CROSSED DS1 DS2 DOWN | D0: -46.56 | DR1: -166.39 | DR2: -293.96 | DS1: -6.40 | DS2: 70.88 | A0: 935.41 | AR1: 400.80 | AS1: 1383.09 | SLOPE: -3.0436 | BASE: 21222.78"
    print(decision(example_result))

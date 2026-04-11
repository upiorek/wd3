"""Decision helpers.

This module converts algorithm outputs (e.g. Magic Lines) into a trade decision.

Conventions:
- Returns: "BUY", "SELL", or "NONE"
"""

from __future__ import annotations

DEBUG = 0

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

def _dir_letter(line_id: str) -> str:
    if line_id[1] == 'M':
        return line_id[0]
    return line_id[1].upper() if line_id else ""

def _find_extreme_line(crossed_ids: list[str], offsets: dict[str, float], prefix: str) -> tuple[str | None, float | None]:
    """Find the extreme (highest or lowest) line with given prefix.
    
    Args:
        crossed_ids: List of crossed line IDs.
        offsets: Dictionary of line offsets.
        prefix: Line prefix to filter by ("A" finds highest, "D" finds lowest).
    
    Returns:
        Tuple of the chosen line ID and its offset + BASE, or (None, None).
    """
    find_max = (prefix == "A")
    extreme_line_id: str | None = None
    extreme_offset: float | None = None
    for line_id in crossed_ids:
        if DEBUG > 0:
            print(f"Checking line_id: {line_id}")
        prefix_letter = _dir_letter(line_id)
        if DEBUG > 0:
            print(f"Line prefix: {prefix_letter}")
        if not prefix_letter.startswith(prefix):
            continue
        offset = offsets.get(line_id)
        if offset is None:
            continue
        if extreme_offset is None or (offset > extreme_offset if find_max else offset < extreme_offset):
            extreme_line_id = line_id
            extreme_offset = offset

            if DEBUG > 0:
                print(f"New extreme line: {extreme_line_id} with offset {extreme_offset:.2f}")
    
    # add offset to base
    base_offset = offsets.get("BASE")
    if extreme_offset is not None and base_offset is not None:
        extreme_offset += base_offset
    
    return extreme_line_id, extreme_offset

def decision(result: str | None) -> str:
    """Map magic_lines.process_single_file() result string to an order type.

    example:
    CROSSED AR1 DOWN | D0: -95.57 | DR1: -273.62 | DS1: 420.07 | A0: 147.94 | AR1: 18.28 | AS1: 683.76
    """

    ret = ("log: result \"" + result + "\"" if result else "log: result \"no result\"") + "\n"

    if not result:
        return ret + "log: no result\nNONE"

    header = result.split('|', 1)[0].strip()

    if not header.startswith("CROSSED"):
        return ret + "log: no crossed\nNONE"

    parts = header.split()
    if not parts:
        return ret + "log: invalid input string\nNONE"

    direction = parts[-1]
    if direction not in ("UP", "DOWN"):
        return ret + f"log: invalid direction: {direction}\nNONE"
    if DEBUG > 0:
        print(f"direction: {direction}")

    offsets = _parse_line_offsets(result)

    crossed_ids = parts[1:-1]
    if DEBUG > 0:
        print(f"crossed_ids: {crossed_ids}")
    if not crossed_ids:
        return ret + "log: no line ids\nNONE"
    
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

    first_letters = [_dir_letter(line_id) for line_id in crossed_ids]
    if DEBUG > 0:
        print(f"first_letters: {first_letters}")
    has_a = "A" in first_letters
    has_d = "D" in first_letters

    can_buy = (direction == "UP" and has_a)
    can_sell = (direction == "DOWN" and has_d)

    # print(f"can_buy: {can_buy}, can_sell: {can_sell}")

    if can_buy:
        # Do not buy below D0 (i.e. last_close < D0 => D0 offset > 0).
        if d0_offset is not None and d0_offset > 0:
            return  ret + "log: do not buy below D0\nNONE"
        
        highest_a_line_id, highest_a_offset = _find_extreme_line(crossed_ids, offsets, "A")
        decision = "BUY"
        if highest_a_line_id is not None:
            decision += f" {highest_a_line_id}"
        if highest_a_offset is not None:
            decision += f" ABOVE {highest_a_offset:.2f}"
        return ret + decision

    if can_sell:
        # Do not sell above A0 (i.e. last_close > A0 => A0 offset < 0).
        if a0_offset is not None and a0_offset < 0:
            return ret + "log: do not sell above A0\nNONE"

        lowest_d_line_id, lowest_d_offset = _find_extreme_line(crossed_ids, offsets, "D")
        decision = "SELL"
        if lowest_d_line_id is not None:
            decision += f" {lowest_d_line_id}"
        if lowest_d_offset is not None:
            decision += f" BELOW {lowest_d_offset:.2f}"
        return ret + decision

    # No valid lines matched the direction.
    if len(crossed_ids) > 1:
        return ret + "log: no valid lines found\nNONE"

    line_id = crossed_ids[0]
    if DEBUG > 0:
        print(f"line_id: {line_id}")
    line_letter = _dir_letter(line_id)
    if DEBUG > 0:
        print(f"line_letter: {line_letter}")
    if line_letter in ("A", "D"):
        return ret + "log: bad direction\nNONE"

    return ret + f"log: bad line id: {line_id}\nNONE"

if __name__ == '__main__':  
    # Example usage
    DEBUG = 1
    example_result = "CROSSED SD1(3) DM(5) DOWN | SA2(2): 575.81 | AM(1): 350.70 | SA1(0): 173.33 | SD1(3): -11.34 | DM(5): -265.63 | SD2(5): -547.47 | SD3(5): -805.45 | SLOPE: 1.7702 | BASE: 24680.63"
    print(decision(example_result))


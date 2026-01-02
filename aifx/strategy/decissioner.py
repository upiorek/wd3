"""Decision helpers.

This module converts algorithm outputs (e.g. Magic Lines) into a trade decision.

Conventions:
- Returns: "BUY", "SELL", or "NONE"
"""

from __future__ import annotations


def decision(result: str | None) -> str:
    """Map magic_lines.process_single_file() result string to an order type.

    example:
    CROSSED AR1 DOWN | D0: -95.57 | DR1: -273.62 | DS1: 420.07 | A0: 147.94 | AR1: 18.28 | AS1: 683.76
    """


    if not result:
        return "NONE"

    header = result.split('|', 1)[0].strip()

    if not header.startswith("CROSSED"):
        return "NONE"

    parts = header.split()
    if not parts:
        return "NONE"

    line_id = parts[1]
    direction = parts[2]
    if "A" in line_id and direction == "UP":
        return "BUY"
    if  "D" in line_id and direction == "DOWN":
        return "SELL"
    
    # TODO add SL / TP levels
    
    return "NONE"

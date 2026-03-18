# src/citation_utils.py
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple


def _build_number_clause(numbers: List[int], singular: str, plural: str) -> str:
    """Return a human-readable clause describing the provided numbered units."""
    unique_values = sorted(set(numbers))
    if not unique_values:
        return ""
    if len(unique_values) == 1:
        return f"{singular} {unique_values[0]}"

    ranges: List[str] = []
    start = unique_values[0]
    end = unique_values[0]

    for current in unique_values[1:]:
        if current == end + 1:
            end = current
            continue

        ranges.append(str(start) if start == end else f"{start}-{end}")
        start = current
        end = current

    ranges.append(str(start) if start == end else f"{start}-{end}")
    return f"{plural} {', '.join(ranges)}"


def _format_timestamp(seconds: Optional[float]) -> Optional[str]:
    if seconds is None:
        return None
    total_seconds = max(int(seconds), 0)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def _format_timestamp_range(
    start: Optional[float],
    end: Optional[float],
) -> Optional[str]:
    start_label = _format_timestamp(start)
    end_label = _format_timestamp(end)
    if not start_label:
        return None
    if not end_label or end_label == start_label:
        return start_label
    return f"{start_label}-{end_label}"


def format_citations(sources: List[Dict[str, Optional[float]]]) -> str:
    """
    Format structured source metadata (pages and timestamps) into a single citation string.
    """
    if not sources:
        return ""

    page_groups: "OrderedDict[Tuple[str, str], List[int]]" = OrderedDict()
    time_groups: "OrderedDict[str, List[Tuple[Optional[float], Optional[float]]]]" = OrderedDict()

    for src in sources:
        name = src.get("lecture_name") or "Lecture"
        page = src.get("page_number")
        if page is not None:
            file_type = (src.get("file_type") or "pdf").lower()
            unit = "slide" if file_type == "slides" else "page"
            page_groups.setdefault((name, unit), []).append(int(page))
        if src.get("timestamp_start") is not None or src.get("timestamp_end") is not None:
            time_groups.setdefault(name, []).append(
                (src.get("timestamp_start"), src.get("timestamp_end"))
            )

    parts: List[str] = []
    if page_groups:
        page_parts = []
        for (name, unit), numbers in page_groups.items():
            clause = _build_number_clause(
                numbers,
                singular=unit,
                plural=f"{unit}s",
            )
            if clause:
                page_parts.append(f"{name}, {clause}")
        if page_parts:
            parts.append("; ".join(page_parts))

    if time_groups:
        time_parts = []
        for name, ranges in time_groups.items():
            formatted_ranges = [
                tr for tr in (_format_timestamp_range(start, end) for start, end in ranges) if tr
            ]
            if formatted_ranges:
                time_parts.append(f"{name}, {'; '.join(formatted_ranges)}")
        if time_parts:
            parts.append("; ".join(time_parts))

    return f"See {'; '.join(parts)}" if parts else ""


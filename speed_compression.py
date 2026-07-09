# -*- coding: utf-8 -*-

import math


SPEED_FACTOR_OPTIONS = (1.0, 1.10, 1.20, 1.25, 1.33)


def normalize_speed_factor(value):
    try:
        speed_factor = float(value)
    except (TypeError, ValueError):
        return 1.0
    if not math.isfinite(speed_factor) or speed_factor <= 0:
        return 1.0
    return max(1.0, speed_factor)


def speed_factor_enabled(speed_factor):
    return normalize_speed_factor(speed_factor) > 1.0001


def format_speed_factor(speed_factor):
    speed_factor = normalize_speed_factor(speed_factor)
    if not speed_factor_enabled(speed_factor):
        return "不加速"
    return f"{speed_factor:.2f}x"


SPEED_FACTOR_LABELS = tuple(format_speed_factor(value) for value in SPEED_FACTOR_OPTIONS)


def speed_factor_from_label(label):
    label = str(label).strip().lower().replace("×", "x")
    if not label or label == "不加速":
        return 1.0
    if label.endswith("x"):
        label = label[:-1]
    return normalize_speed_factor(label)


def speed_adjusted_duration(duration_seconds, speed_factor):
    speed_factor = normalize_speed_factor(speed_factor)
    if duration_seconds <= 0:
        return duration_seconds
    return duration_seconds / speed_factor


def _format_filter_number(value):
    text = f"{float(value):.6f}".rstrip("0").rstrip(".")
    return text or "1"


def build_atempo_filter(speed_factor):
    speed_factor = normalize_speed_factor(speed_factor)
    filters = []
    while speed_factor > 2.0:
        filters.append("atempo=2.0")
        speed_factor /= 2.0
    filters.append(f"atempo={_format_filter_number(speed_factor)}")
    return ",".join(filters)


def build_speed_filter_args(speed_factor, include_audio=True):
    speed_factor = normalize_speed_factor(speed_factor)
    if not speed_factor_enabled(speed_factor):
        return []
    filter_value = _format_filter_number(speed_factor)
    args = [
        "-filter:v",
        f"setpts=PTS/{filter_value}",
    ]
    if include_audio:
        args.extend(["-filter:a", build_atempo_filter(speed_factor)])
    return args

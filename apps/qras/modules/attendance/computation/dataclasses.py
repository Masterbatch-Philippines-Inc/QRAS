from dataclasses import dataclass, field
from typing import List, Tuple
from datetime import datetime


@dataclass
class PairingResult:
    pairs:          List[Tuple]
    stack:          object
    first_time_in:  object


@dataclass
class HoursResult:
    actual_hours_worked: float
    hours_within_shift:  float
    total_hours_raw:     float
    total_work_display:  float
    actual_break:        float


@dataclass
class LateResult:
    is_late:            bool
    late_hours:         float
    raw_late_hours:     float
    is_halfday_by_late: bool


@dataclass
class HalfdayResult:
    is_halfday:          bool
    is_halfday_by_hours: bool
    is_halfday_by_late:  bool


@dataclass
class CompletionResult:
    is_completed:    bool
    timed_out_on_time: bool


@dataclass
class UndertimeResult:
    undertime:   float
    is_undertime: bool


@dataclass
class OvertimeResult:
    overtime:     float
    pre_overtime: float = 0.0


@dataclass
class CreditedResult:
    credited:            float
    disciplinary_action: bool
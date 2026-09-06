# 4-hour variants of the volume-profile strategies (same logic, higher timeframe).
from VolNodeSupport import VolNodeSupport
from VolProfileBB import VolProfileBB

class VolNodeSupport_4h(VolNodeSupport):
    timeframe = "4h"

class VolProfileBB_4h(VolProfileBB):
    timeframe = "4h"

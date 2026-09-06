# Long-only variant of EMAMTFStoch for SPOT stock backtests (shorting stocks isn't
# modeled cleanly and spot mode forbids can_short). Short signals are simply ignored;
# the EMA trend filter + market drift make longs the primary side for equities anyway.
from EMAMTFStoch import EMAMTFStoch

class EMAMTFStochLong(EMAMTFStoch):
    can_short = False

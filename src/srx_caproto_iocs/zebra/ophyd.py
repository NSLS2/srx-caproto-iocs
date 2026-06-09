from __future__ import annotations

from ophyd import Component as Cpt
from ophyd import EpicsSignal, EpicsSignalRO

from ..base import OphydDeviceWithCaprotoIOC


class ZebraWithCaprotoIOC(OphydDeviceWithCaprotoIOC):
    """An ophyd Device which works with the Zebra caproto extension IOC."""

    # Device-type selector (zebra / scaler)
    dev_type = Cpt(EpicsSignal, "dev_type", string=True)

    # Generic data channels (ch1–ch4)
    ch1 = Cpt(EpicsSignalRO, "ch1", auto_monitor=False)
    ch2 = Cpt(EpicsSignalRO, "ch2", auto_monitor=False)
    ch3 = Cpt(EpicsSignalRO, "ch3", auto_monitor=False)
    ch4 = Cpt(EpicsSignalRO, "ch4", auto_monitor=False)

from __future__ import annotations

from ophyd import Component as Cpt
from ophyd import EpicsSignal, EpicsSignalRO

from ..base import OphydDeviceWithCaprotoIOC


class ZebraWithCaprotoIOC(OphydDeviceWithCaprotoIOC):
    """An ophyd Device which works with the Zebra caproto extension IOC."""

    # Device-type selector (zebra / scaler)
    dev_type = Cpt(EpicsSignal, "dev_type", string=True)

    # Zebra position-capture channels
    enc1 = Cpt(EpicsSignalRO, "enc1", auto_monitor=False)
    enc2 = Cpt(EpicsSignalRO, "enc2", auto_monitor=False)
    enc3 = Cpt(EpicsSignalRO, "enc3", auto_monitor=False)
    zebra_time = Cpt(EpicsSignalRO, "zebra_time", auto_monitor=False)

    # Scaler channels
    i0 = Cpt(EpicsSignalRO, "i0", auto_monitor=False)
    im = Cpt(EpicsSignalRO, "im", auto_monitor=False)
    it = Cpt(EpicsSignalRO, "it", auto_monitor=False)
    sis_time = Cpt(EpicsSignalRO, "sis_time", auto_monitor=False)

from __future__ import annotations

from ophyd import Component as Cpt
from ophyd import EpicsSignal, EpicsSignalRO

from ..base import OphydDeviceWithCaprotoIOC


def make_zebra_ophyd_device(num_channels: int = 4) -> type:
    """Return a :class:`ZebraWithCaprotoIOC` subclass with *num_channels* channels.

    Each channel maps to an EPICS PV suffix ``ch1``, ``ch2``, ...,
    ``ch{num_channels}``::

        MyDevice = make_zebra_ophyd_device(6)
        dev = MyDevice("XF:05IDD-ES:1{ZebraSaver:1}:", name="zs")

    Parameters
    ----------
    num_channels:
        Number of generic data channels to connect to (default: 4).
    """
    if num_channels < 1:
        msg = f"num_channels must be >= 1, got {num_channels}"
        raise ValueError(msg)

    attrs: dict[str, object] = {
        "__doc__": "An ophyd Device which works with the Zebra caproto extension IOC.",
        # Device-type selector (zebra / scaler)
        "dev_type": Cpt(EpicsSignal, "dev_type", string=True),
    }
    for i in range(1, num_channels + 1):
        attrs[f"ch{i}"] = Cpt(EpicsSignalRO, f"ch{i}", auto_monitor=False)

    return type("ZebraWithCaprotoIOC", (OphydDeviceWithCaprotoIOC,), attrs)


#: Default 4-channel device class — backward-compatible public name.
ZebraWithCaprotoIOC: type = make_zebra_ophyd_device(4)

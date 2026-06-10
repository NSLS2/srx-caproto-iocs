# pylint: disable=duplicate-code
from __future__ import annotations

import argparse
import json
import textwrap
from enum import Enum

from caproto import ChannelType
from caproto.server import pvproperty, run, template_arg_parser

from ..base import CaprotoSaveIOC, check_args
from ..utils import now, save_hdf5_zebra

# def export_nano_zebra_data(zebra, filepath, fastaxis):
#     j = 0
#     while zebra.pc.data_in_progress.get() == 1:
#         print("Waiting for zebra...")
#         ttime.sleep(0.1)
#         j += 1
#         if j > 10:
#             print("THE ZEBRA IS BEHAVING BADLY CARRYING ON")
#             break

#     time_d = zebra.pc.data.time.get()
#     enc1_d = zebra.pc.data.enc1.get()
#     enc2_d = zebra.pc.data.enc2.get()
#     enc3_d = zebra.pc.data.enc3.get()

#     px = zebra.pc.pulse_step.get()
#     if fastaxis == 'NANOHOR':
#         # Add half pixelsize to correct encoder
#         enc1_d = enc1_d + (px / 2)
#     elif fastaxis == 'NANOVER':
#         # Add half pixelsize to correct encoder
#         enc2_d = enc2_d + (px / 2)
#     elif fastaxis == 'NANOZ':
#         # Add half pixelsize to correct encoder
#         enc3_d = enc3_d + (px / 2)

#     size = (len(time_d),)
#     with h5py.File(filepath, "w") as f:
#         dset0 = f.create_dataset("zebra_time", size, dtype="f")
#         dset0[...] = np.array(time_d)
#         dset1 = f.create_dataset("enc1", size, dtype="f")
#         dset1[...] = np.array(enc1_d)
#         dset2 = f.create_dataset("enc2", size, dtype="f")
#         dset2[...] = np.array(enc2_d)
#         dset3 = f.create_dataset("enc3", size, dtype="f")
#         dset3[...] = np.array(enc3_d)


# class ZebraPositionCaptureData(Device):
#     """
#     Data arrays for the Zebra position capture function and their metadata.
#     """
#     # Data arrays
#     ...
#     enc1 = Cpt(EpicsSignal, "PC_ENC1")  # XF:05IDD-ES:1{Dev:Zebra2}:PC_ENC1
#     enc2 = Cpt(EpicsSignal, "PC_ENC2")  # XF:05IDD-ES:1{Dev:Zebra2}:PC_ENC2
#     enc3 = Cpt(EpicsSignal, "PC_ENC3")  # XF:05IDD-ES:1{Dev:Zebra2}:PC_ENC3
#     time = Cpt(EpicsSignal, "PC_TIME")  # XF:05IDD-ES:1{Dev:Zebra2}:PC_TIME
#     ...

# class ZebraPositionCapture(Device):
#     """
#     Signals for the position capture function of the Zebra
#     """

#     # Configuration settings and status PVs
#     ...
#     pulse_step = Cpt(EpicsSignalWithRBV, "PC_PULSE_STEP")  # XF:05IDD-ES:1{Dev:Zebra2}:PC_PULSE_STEP
#     ...
#     data_in_progress = Cpt(EpicsSignalRO, "ARRAY_ACQ")  # XF:05IDD-ES:1{Dev:Zebra2}:ARRAY_ACQ
#     ...
#     data = Cpt(ZebraPositionCaptureData, "")

# nanoZebra = SRXZebra(
#    "XF:05IDD-ES:1{Dev:Zebra2}:", name="nanoZebra",
#    read_attrs=["pc.data.enc1", "pc.data.enc2", "pc.data.enc3", "pc.data.time"],
# )

DEFAULT_MAX_LENGTH = 100_000

#: SRX-specific HDF5 dataset names for the first 4 channels, keyed by dev_type.
_SRX_CHANNEL_NAMES: dict[str, list[str]] = {
    "zebra": ["enc1", "enc2", "enc3", "zebra_time"],
    "scaler": ["i0", "im", "it", "sis_time"],
}


class DevTypes(Enum):
    """Enum class for devices."""

    ZEBRA = "zebra"
    SCALER = "scaler"


def _build_default_maps(num_channels: int) -> dict[str, dict[str, str]]:
    """Build default dataset maps for *num_channels* generic channels.

    The first 4 channels use SRX-specific HDF5 dataset names; channels
    beyond 4 fall back to an identity mapping (``chN -> "chN"``).
    """
    maps: dict[str, dict[str, str]] = {}
    for dev_type, srx_names in _SRX_CHANNEL_NAMES.items():
        mapping: dict[str, str] = {}
        for i in range(1, num_channels + 1):
            pv_name = f"ch{i}"
            if i <= len(srx_names):
                mapping[pv_name] = srx_names[i - 1]
            else:
                mapping[pv_name] = pv_name  # identity for extra channels
        maps[dev_type] = mapping
    return maps


def _zebra_init(
    self,
    *args,
    dataset_map: dict[str, str] | None = None,
    **kwargs,
) -> None:
    """Init method.

    Parameters
    ----------
    dataset_map : dict, optional
        Mapping of PV attribute names to HDF5 dataset names, e.g.
        ``{"ch1": "x_pos", "ch2": "y_pos"}``.  When *None* (default)
        the mapping is chosen automatically based on the ``dev_type`` PV.
    """
    self._dataset_map = dataset_map
    CaprotoSaveIOC.__init__(self, *args, **kwargs)


async def _zebra_get_current_dataset(self, *args, **kwargs):  # pylint: disable=unused-argument
    if self._dataset_map is not None:
        mapping = self._dataset_map
    elif self.dev_type.value == DevTypes.ZEBRA.value:
        mapping = self._DEFAULT_DATASET_MAPS[DevTypes.ZEBRA.value]
    else:
        mapping = self._DEFAULT_DATASET_MAPS[DevTypes.SCALER.value]

    dataset = {
        hdf5_name: getattr(self, pv_attr).value
        for pv_attr, hdf5_name in mapping.items()
    }

    print(f"{now()}:\n{dataset}")

    return dataset


def _zebra_saver(request_queue, response_queue) -> None:
    """The saver callback for threading-based queueing."""
    while True:
        received = request_queue.get()
        filename = received["filename"]
        data = received["data"]
        # 'frame_number' is not used for this exporter.
        try:
            save_hdf5_zebra(fname=filename, data=data, mode="a")
            print(f"{now()}: saved data into:\n  {filename}")

            success = True
            error_message = ""
        except Exception as exc:  # pylint: disable=broad-exception-caught
            success = False
            error_message = exc
            print(
                f"Cannot save file {filename!r} due to the following exception:\n{exc}"
            )

        response = {"success": success, "error_message": error_message}
        response_queue.put(response)


def make_zebra_save_ioc(num_channels: int = 4) -> type:
    """Return a :class:`ZebraSaveIOC` subclass with *num_channels* data channels.

    Each channel is exposed as a caproto PV named ``ch1``, ``ch2``, ...,
    ``ch{num_channels}``.  The returned class can be used directly::

        MyIOC = make_zebra_save_ioc(6)
        ioc = MyIOC(**ioc_options)

    Channels beyond 4 use identity mapping by default (``chN -> "chN"``);
    supply ``--dataset-map`` for custom HDF5 names.

    Parameters
    ----------
    num_channels:
        Number of generic data channels to create (default: 4).
    """
    if num_channels < 1:
        msg = f"num_channels must be >= 1, got {num_channels}"
        raise ValueError(msg)

    channel_attrs: dict[str, object] = {
        f"ch{i}": pvproperty(
            value=0,
            dtype=ChannelType.DOUBLE,
            doc=f"Generic channel {i}",
            max_length=DEFAULT_MAX_LENGTH,
        )
        for i in range(1, num_channels + 1)
    }

    default_maps = _build_default_maps(num_channels)

    shared_attrs: dict[str, object] = {
        "__doc__": "Zebra caproto save IOC.",
        "dev_type": pvproperty(
            value=DevTypes.ZEBRA.value,
            enum_strings=[x.value for x in DevTypes],
            dtype=ChannelType.ENUM,
            doc="Pick device type",
        ),
        "_DEFAULT_DATASET_MAPS": default_maps,
        "__init__": _zebra_init,
        "_get_current_dataset": _zebra_get_current_dataset,
        "saver": staticmethod(_zebra_saver),
    }

    return type("ZebraSaveIOC", (CaprotoSaveIOC,), {**channel_attrs, **shared_attrs})


#: Default 4-channel class — backward-compatible public name.
ZebraSaveIOC: type = make_zebra_save_ioc(4)


if __name__ == "__main__":
    # Parse --num-channels first so we can build the right IOC class before
    # template_arg_parser consumes the argument list.
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument(
        "--num-channels",
        type=int,
        default=4,
        help="Number of generic data channels ch1..chN to create (default: 4).",
    )
    pre_args, _ = pre_parser.parse_known_args()
    num_ch = pre_args.num_channels

    DynamicIOC = make_zebra_save_ioc(num_ch)

    parser, split_args = template_arg_parser(
        default_prefix="", desc=textwrap.dedent(DynamicIOC.__doc__ or "")
    )

    parser.add_argument(
        "--num-channels",
        type=int,
        default=4,
        help="Number of generic data channels ch1..chN to create (default: 4).",
    )
    parser.add_argument(
        "--dataset-map",
        help=(
            f"JSON mapping of generic channel names (ch1-ch{num_ch}) to HDF5 dataset names. "
            'Partial FXI-style example: \'{"ch1": "enc1_pi_r", "ch2": "zebra_time"}\'. '
            "When omitted, the mapping is chosen from the built-in SRX defaults "
            "based on the dev_type PV (zebra or scaler); channels beyond 4 use "
            'identity mapping (chN -> "chN").'
        ),
        type=json.loads,
        default=None,
    )

    ioc_options, run_options = check_args(parser, split_args)
    parsed = parser.parse_args()

    ioc = DynamicIOC(dataset_map=parsed.dataset_map, **ioc_options)
    run(ioc.pvdb, **run_options)

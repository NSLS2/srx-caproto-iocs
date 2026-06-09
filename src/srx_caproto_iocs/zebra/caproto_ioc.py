# pylint: disable=duplicate-code
from __future__ import annotations

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


class DevTypes(Enum):
    """Enum class for devices."""

    ZEBRA = "zebra"
    SCALER = "scaler"


class ZebraSaveIOC(CaprotoSaveIOC):
    """Zebra caproto save IOC."""

    dev_type = pvproperty(
        value=DevTypes.ZEBRA.value,
        enum_strings=[x.value for x in DevTypes],
        dtype=ChannelType.ENUM,
        doc="Pick device type",
    )

    ch1 = pvproperty(
        value=0,
        dtype=ChannelType.DOUBLE,
        doc="Generic channel 1 (zebra default: enc1, scaler default: i0)",
        max_length=DEFAULT_MAX_LENGTH,
    )

    ch2 = pvproperty(
        value=0,
        dtype=ChannelType.DOUBLE,
        doc="Generic channel 2 (zebra default: enc2, scaler default: im)",
        max_length=DEFAULT_MAX_LENGTH,
    )

    ch3 = pvproperty(
        value=0,
        dtype=ChannelType.DOUBLE,
        doc="Generic channel 3 (zebra default: enc3, scaler default: it)",
        max_length=DEFAULT_MAX_LENGTH,
    )

    ch4 = pvproperty(
        value=0,
        dtype=ChannelType.DOUBLE,
        doc="Generic channel 4 (zebra default: zebra_time, scaler default: sis_time)",
        max_length=DEFAULT_MAX_LENGTH,
    )

    # def __init__(self, *args, external_pvs=None, **kwargs):
    #     """Init method.

    #     external_pvs : dict
    #         a dictionary of external PVs with keys as human-readable names.
    #     """
    #     super().__init__(*args, **kwargs)
    #     self._external_pvs = external_pvs

    #: Default dataset mappings keyed by dev_type. Keys are generic PV attribute
    #: names (ch1–ch4); values are the HDF5 dataset names written to file.
    _DEFAULT_DATASET_MAPS: dict[str, dict[str, str]] = {
        DevTypes.ZEBRA.value: {
            "ch1": "enc1",
            "ch2": "enc2",
            "ch3": "enc3",
            "ch4": "zebra_time",
        },
        DevTypes.SCALER.value: {
            "ch1": "i0",
            "ch2": "im",
            "ch3": "it",
            "ch4": "sis_time",
        },
    }

    def __init__(
        self,
        *args,
        dataset_map: dict[str, str] | None = None,
        **kwargs,
    ):
        """Init method.

        Parameters
        ----------
        dataset_map : dict, optional
            Mapping of PV attribute names to HDF5 dataset names, e.g.
            ``{"enc1": "x_pos", "enc2": "y_pos"}``.  When *None* (default)
            the mapping is chosen automatically based on the ``dev_type`` PV.
        """
        self._dataset_map = dataset_map
        super().__init__(*args, **kwargs)

    async def _get_current_dataset(self, *args, **kwargs):  # pylint: disable=unused-argument
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

    @staticmethod
    def saver(request_queue, response_queue):
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


if __name__ == "__main__":
    parser, split_args = template_arg_parser(
        default_prefix="", desc=textwrap.dedent(ZebraSaveIOC.__doc__)
    )

    parser.add_argument(
        "--dataset-map",
        help=(
            "JSON mapping of generic channel names (ch1–ch4) to HDF5 dataset names. "
            'Full example: \'{"ch1": "x_pos", "ch2": "y_pos", "ch3": "z_pos", "ch4": "t"}\'. '
            'Partial example (FXI-style, 2 channels): \'{"ch1": "enc1_pi_r", "ch2": "zebra_time"}\'. '
            "When omitted, the mapping is chosen from the built-in SRX defaults "
            "based on the dev_type PV (zebra or scaler)."
        ),
        type=json.loads,
        default=None,
    )

    ioc_options, run_options = check_args(parser, split_args)
    dataset_map_arg = parser.parse_args().dataset_map

    ioc = ZebraSaveIOC(dataset_map=dataset_map_arg, **ioc_options)
    run(ioc.pvdb, **run_options)

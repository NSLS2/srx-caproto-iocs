from __future__ import annotations

import uuid
from pathlib import Path

import h5py
import pytest


@pytest.mark.cloud_friendly
def test_zebra_default_map_zebra_dev_type(zebra_caproto_ioc, zebra_ophyd_device):
    """Default zebra dev_type writes enc1/enc2/enc3/zebra_time datasets."""
    num_frames = 3
    tmpdirname = f"/tmp/srx-caproto-iocs/{str(uuid.uuid4())[:8]}"
    write_dir = Path(tmpdirname)
    write_dir.mkdir(parents=True, exist_ok=True)

    dev = zebra_ophyd_device

    # Put some recognisable test values into the data PVs.
    dev.enc1.parent  # ensure connected
    test_values = {"enc1": [1.1], "enc2": [2.2], "enc3": [3.3], "zebra_time": [0.5]}

    dev.write_dir.put(str(write_dir))
    dev.file_name.put(f"test_{uuid.uuid4().hex[:8]}.h5")
    dev.set("stage").wait(timeout=10)

    for _ in range(num_frames):
        dev.set("acquire").wait(timeout=10)

    dev.set("unstage").wait(timeout=10)

    full_file_path = dev.full_file_path.get()
    assert full_file_path, "full_file_path PV is empty"
    assert Path(full_file_path).is_file(), f"HDF5 file not found: {full_file_path}"

    with h5py.File(full_file_path, "r") as f:
        expected_keys = {"enc1", "enc2", "enc3", "zebra_time"}
        assert expected_keys.issubset(set(f.keys())), (
            f"Expected datasets {expected_keys}, got {set(f.keys())}"
        )


@pytest.mark.cloud_friendly
def test_zebra_default_map_scaler_dev_type(zebra_caproto_ioc, zebra_ophyd_device):
    """Switching dev_type to scaler writes i0/im/it/sis_time datasets."""
    tmpdirname = f"/tmp/srx-caproto-iocs/{str(uuid.uuid4())[:8]}"
    write_dir = Path(tmpdirname)
    write_dir.mkdir(parents=True, exist_ok=True)

    dev = zebra_ophyd_device
    dev.dev_type.put("scaler")

    dev.write_dir.put(str(write_dir))
    dev.file_name.put(f"test_{uuid.uuid4().hex[:8]}.h5")
    dev.set("stage").wait(timeout=10)
    dev.set("acquire").wait(timeout=10)
    dev.set("unstage").wait(timeout=10)

    full_file_path = dev.full_file_path.get()
    assert Path(full_file_path).is_file(), f"HDF5 file not found: {full_file_path}"

    with h5py.File(full_file_path, "r") as f:
        expected_keys = {"i0", "im", "it", "sis_time"}
        assert expected_keys.issubset(set(f.keys())), (
            f"Expected datasets {expected_keys}, got {set(f.keys())}"
        )

    # Reset dev_type back to default.
    dev.dev_type.put("zebra")


@pytest.mark.cloud_friendly
def test_zebra_custom_dataset_map(zebra_caproto_ioc_custom_map, zebra_ophyd_device_custom_map):
    """--dataset-map override produces HDF5 datasets with the custom names."""
    _proc, custom_map = zebra_caproto_ioc_custom_map
    expected_hdf5_keys = set(custom_map.values())

    tmpdirname = f"/tmp/srx-caproto-iocs/{str(uuid.uuid4())[:8]}"
    write_dir = Path(tmpdirname)
    write_dir.mkdir(parents=True, exist_ok=True)

    dev = zebra_ophyd_device_custom_map
    dev.write_dir.put(str(write_dir))
    dev.file_name.put(f"test_{uuid.uuid4().hex[:8]}.h5")
    dev.set("stage").wait(timeout=10)
    dev.set("acquire").wait(timeout=10)
    dev.set("unstage").wait(timeout=10)

    full_file_path = dev.full_file_path.get()
    assert Path(full_file_path).is_file(), f"HDF5 file not found: {full_file_path}"

    with h5py.File(full_file_path, "r") as f:
        assert expected_hdf5_keys.issubset(set(f.keys())), (
            f"Expected custom datasets {expected_hdf5_keys}, got {set(f.keys())}"
        )
        # Original PV names must NOT appear as dataset names.
        pv_attr_names = set(custom_map.keys())
        renamed = pv_attr_names - expected_hdf5_keys
        for name in renamed:
            assert name not in f, f"PV attr name '{name}' should not appear as a dataset key"

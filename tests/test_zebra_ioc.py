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

    dev.write_dir.put(str(write_dir), timeout=10)
    dev.file_name.put(f"test_{uuid.uuid4().hex[:8]}.h5", timeout=10)
    dev.set("stage").wait(timeout=10)

    for _ in range(num_frames):
        dev.set("acquire").wait(timeout=10)

    dev.set("unstage").wait(timeout=10)

    full_file_path = dev.full_file_path.get(timeout=10)
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
    dev.dev_type.put("scaler", timeout=10)

    dev.write_dir.put(str(write_dir), timeout=10)
    dev.file_name.put(f"test_{uuid.uuid4().hex[:8]}.h5", timeout=10)
    dev.set("stage").wait(timeout=10)
    dev.set("acquire").wait(timeout=10)
    dev.set("unstage").wait(timeout=10)

    full_file_path = dev.full_file_path.get(timeout=10)
    assert Path(full_file_path).is_file(), f"HDF5 file not found: {full_file_path}"

    with h5py.File(full_file_path, "r") as f:
        expected_keys = {"i0", "im", "it", "sis_time"}
        assert expected_keys.issubset(set(f.keys())), (
            f"Expected datasets {expected_keys}, got {set(f.keys())}"
        )

    # Reset dev_type back to default.
    dev.dev_type.put("zebra", timeout=10)


@pytest.mark.cloud_friendly
def test_zebra_custom_dataset_map(
    zebra_caproto_ioc_custom_map, zebra_ophyd_device_custom_map
):
    """--dataset-map override produces HDF5 datasets with the custom names."""
    _proc, custom_map = zebra_caproto_ioc_custom_map
    expected_hdf5_keys = set(custom_map.values())

    tmpdirname = f"/tmp/srx-caproto-iocs/{str(uuid.uuid4())[:8]}"
    write_dir = Path(tmpdirname)
    write_dir.mkdir(parents=True, exist_ok=True)

    dev = zebra_ophyd_device_custom_map
    dev.write_dir.put(str(write_dir), timeout=10)
    dev.file_name.put(f"test_{uuid.uuid4().hex[:8]}.h5", timeout=10)
    dev.set("stage").wait(timeout=10)
    dev.set("acquire").wait(timeout=10)
    dev.set("unstage").wait(timeout=10)

    full_file_path = dev.full_file_path.get(timeout=10)
    assert Path(full_file_path).is_file(), f"HDF5 file not found: {full_file_path}"

    with h5py.File(full_file_path, "r") as f:
        assert expected_hdf5_keys.issubset(set(f.keys())), (
            f"Expected custom datasets {expected_hdf5_keys}, got {set(f.keys())}"
        )
        # Original PV names must NOT appear as dataset names.
        pv_attr_names = set(custom_map.keys())
        renamed = pv_attr_names - expected_hdf5_keys
        for name in renamed:
            assert name not in f, (
                f"PV attr name '{name}' should not appear as a dataset key"
            )


@pytest.mark.cloud_friendly
def test_zebra_fxi_partial_dataset_map(
    zebra_caproto_ioc_fxi_map, zebra_ophyd_device_fxi_map
):
    """FXI-style partial 2-channel map produces exactly 2 HDF5 datasets."""
    _proc, fxi_map = zebra_caproto_ioc_fxi_map
    expected_hdf5_keys = set(fxi_map.values())  # {"enc1_pi_r", "zebra_time"}

    tmpdirname = f"/tmp/srx-caproto-iocs/{str(uuid.uuid4())[:8]}"
    write_dir = Path(tmpdirname)
    write_dir.mkdir(parents=True, exist_ok=True)

    dev = zebra_ophyd_device_fxi_map
    dev.write_dir.put(str(write_dir), timeout=10)
    dev.file_name.put(f"test_{uuid.uuid4().hex[:8]}.h5", timeout=10)
    dev.set("stage").wait(timeout=10)
    dev.set("acquire").wait(timeout=10)
    dev.set("unstage").wait(timeout=10)

    full_file_path = dev.full_file_path.get(timeout=10)
    assert Path(full_file_path).is_file(), f"HDF5 file not found: {full_file_path}"

    with h5py.File(full_file_path, "r") as f:
        actual_keys = set(f.keys())
        assert actual_keys == expected_hdf5_keys, (
            f"Expected exactly {expected_hdf5_keys}, got {actual_keys}"
        )
        assert len(actual_keys) == 2, (
            f"Expected exactly 2 datasets, got {len(actual_keys)}: {actual_keys}"
        )


@pytest.mark.cloud_friendly
def test_three_concurrent_iocs(
    zebra_caproto_ioc_conc_srx_zebra,
    zebra_caproto_ioc_conc_srx_sis,
    zebra_caproto_ioc_fxi_map,
    zebra_ophyd_device_conc_srx_zebra,
    zebra_ophyd_device_conc_srx_sis,
    zebra_ophyd_device_fxi_map,
):
    """Three IOCs save data simultaneously: SRX Zebra, SRX SIS, and FXI.

    Verifies that each IOC independently produces an HDF5 file with exactly
    the expected dataset keys while all three processes run concurrently.
    """
    _proc_sis, sis_map = zebra_caproto_ioc_conc_srx_sis
    _proc_fxi, fxi_map = zebra_caproto_ioc_fxi_map

    srx_zebra_dir = Path(f"/tmp/srx-caproto-iocs/{str(uuid.uuid4())[:8]}")
    srx_sis_dir = Path(f"/tmp/srx-caproto-iocs/{str(uuid.uuid4())[:8]}")
    fxi_dir = Path(f"/tmp/srx-caproto-iocs/{str(uuid.uuid4())[:8]}")
    for d in (srx_zebra_dir, srx_sis_dir, fxi_dir):
        d.mkdir(parents=True, exist_ok=True)

    dev_zebra = zebra_ophyd_device_conc_srx_zebra
    dev_sis = zebra_ophyd_device_conc_srx_sis
    dev_fxi = zebra_ophyd_device_fxi_map

    # Configure all three devices
    for dev, write_dir in [
        (dev_zebra, srx_zebra_dir),
        (dev_sis, srx_sis_dir),
        (dev_fxi, fxi_dir),
    ]:
        dev.write_dir.put(str(write_dir), timeout=10)
        dev.file_name.put(f"test_{uuid.uuid4().hex[:8]}.h5", timeout=10)

    # Stage all three concurrently (kick off, then wait)
    st_zebra = dev_zebra.set("stage")
    st_sis = dev_sis.set("stage")
    st_fxi = dev_fxi.set("stage")
    st_zebra.wait(timeout=10)
    st_sis.wait(timeout=10)
    st_fxi.wait(timeout=10)

    # Acquire all three concurrently
    st_zebra = dev_zebra.set("acquire")
    st_sis = dev_sis.set("acquire")
    st_fxi = dev_fxi.set("acquire")
    st_zebra.wait(timeout=10)
    st_sis.wait(timeout=10)
    st_fxi.wait(timeout=10)

    # Unstage all three
    dev_zebra.set("unstage").wait(timeout=10)
    dev_sis.set("unstage").wait(timeout=10)
    dev_fxi.set("unstage").wait(timeout=10)

    # --- Verify SRX Zebra: default map → exactly enc1, enc2, enc3, zebra_time ---
    fp_zebra = dev_zebra.full_file_path.get(timeout=10)
    assert fp_zebra, "SRX Zebra full_file_path PV is empty"
    assert Path(fp_zebra).is_file(), f"SRX Zebra HDF5 file not found: {fp_zebra}"
    with h5py.File(fp_zebra, "r") as f:
        assert set(f.keys()) == {"enc1", "enc2", "enc3", "zebra_time"}, (
            f"SRX Zebra: unexpected datasets {set(f.keys())}"
        )

    # --- Verify SRX SIS: explicit scaler map → exactly i0, im, it, sis_time ---
    fp_sis = dev_sis.full_file_path.get(timeout=10)
    assert fp_sis, "SRX SIS full_file_path PV is empty"
    assert Path(fp_sis).is_file(), f"SRX SIS HDF5 file not found: {fp_sis}"
    with h5py.File(fp_sis, "r") as f:
        assert set(f.keys()) == set(sis_map.values()), (
            f"SRX SIS: unexpected datasets {set(f.keys())}"
        )

    # --- Verify FXI: partial 2-channel map → exactly enc1_pi_r, zebra_time ---
    fp_fxi = dev_fxi.full_file_path.get(timeout=10)
    assert fp_fxi, "FXI full_file_path PV is empty"
    assert Path(fp_fxi).is_file(), f"FXI HDF5 file not found: {fp_fxi}"
    with h5py.File(fp_fxi, "r") as f:
        assert set(f.keys()) == set(fxi_map.values()), (
            f"FXI: unexpected datasets {set(f.keys())}"
        )
        assert len(f.keys()) == 2, (
            f"FXI: expected exactly 2 datasets, got {len(f.keys())}: {set(f.keys())}"
        )

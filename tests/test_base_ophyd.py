from __future__ import annotations

import re
import shutil
import time as ttime
import uuid
from pathlib import Path

import h5py
import pytest

from srx_caproto_iocs.utils import now


@pytest.mark.cloud_friendly
@pytest.mark.parametrize(
    "date_template", ["%Y/%m/", "%Y/%m/%d", "mydir/%Y/%m/%d", "disguised_spaces_%c"]
)
def test_base_ophyd_templates(base_caproto_ioc, base_ophyd_device, date_template):
    num_frames = 50
    remove = False
    tmpdirname = f"/tmp/srx-caproto-iocs/{str(uuid.uuid4())[:2]}"
    date = now(as_object=True)
    write_dir_root = Path(tmpdirname)
    dir_template = f"{write_dir_root}/{date_template}"

    # We pre-create the test directory in advance as the IOC is not supposed to create one.
    # The assumption for the IOC is that the directory will exist before saving a file to that.
    # We need to substitute the unsupported characters below for it to work, as the IOC will do
    # the same in `full_file_path` before returning the value.
    sanitizer = re.compile(pattern=r"[\":<>|\*\?\s]")
    write_dir = Path(sanitizer.sub("_", date.strftime(dir_template)))
    write_dir.mkdir(parents=True, exist_ok=True)

    file_template = "scan_{num:06d}_{uid}.hdf5"

    dev = base_ophyd_device
    dev.write_dir.put(dir_template)
    dev.file_name.put(file_template)

    dev.set("stage").wait()

    full_file_path = dev.full_file_path.get()
    print(f"{full_file_path = }")

    for i in range(num_frames):
        print(f"Collecting frame {i}...")
        dev.set("acquire").wait()
        ttime.sleep(0.1)

    dev.set("unstage").wait()

    assert full_file_path, "The returned 'full_file_path' did not change."
    assert Path(full_file_path).is_file(), f"No such file '{full_file_path}'"

    with h5py.File(full_file_path, "r", swmr=True) as f:
        dataset = f["/entry/data/data"]
        assert dataset.shape == (num_frames, 256, 256)

        ttime.sleep(1.0)

    if remove:
        shutil.rmtree(tmpdirname)

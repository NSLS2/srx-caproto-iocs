from __future__ import annotations

import json
import os
import socket
import string
import subprocess
import sys
import time as ttime

import pytest

from srx_caproto_iocs.base import OphydDeviceWithCaprotoIOC
from srx_caproto_iocs.example.ophyd import OphydChannelTypes
from srx_caproto_iocs.zebra.ophyd import ZebraWithCaprotoIOC

CAPROTO_PV_PREFIX = "BASE:{{Dev:Save1}}:"
OPHYD_PV_PREFIX = CAPROTO_PV_PREFIX.replace("{{", "{").replace("}}", "}")

ZEBRA_CAPROTO_PV_PREFIX = "ZEBRA:{{Dev:Save1}}:"
ZEBRA_OPHYD_PV_PREFIX = ZEBRA_CAPROTO_PV_PREFIX.replace("{{", "{").replace("}}", "}")


def get_epics_env():
    first_three = ".".join(socket.gethostbyname(socket.gethostname()).split(".")[:3])
    broadcast = f"{first_three}.255"

    print(f"{broadcast = }")

    addr_list = os.getenv("EPICS_CA_ADDR_LIST", broadcast)
    return {
        # Server-side: where the IOC sends beacons
        "EPICS_CAS_BEACON_ADDR_LIST": addr_list,
        "EPICS_CAS_AUTO_BEACON_ADDR_LIST": "no",
        # Client-side: include the computed broadcast on top of auto-discovered addresses
        "EPICS_CA_ADDR_LIST": addr_list,
    }


def start_ioc_subprocess(
    ioc_name="srx_caproto_iocs.base", pv_prefix=CAPROTO_PV_PREFIX, extra_args=()
):
    env = get_epics_env()

    command = [
        sys.executable,
        "-m",
        ioc_name,
        f"--prefix={pv_prefix}",
        "--list-pvs",
        *extra_args,
    ]
    print(
        f"\nStarting caproto IOC in via a fixture using the following command:\n\n  {' '.join(command)}\n"
    )
    os.environ.update(env)
    return subprocess.Popen(
        command,
        start_new_session=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False,
        env=os.environ,
    )


@pytest.fixture(scope="session")
def base_caproto_ioc(wait=5):
    p = start_ioc_subprocess(
        ioc_name="srx_caproto_iocs.base", pv_prefix=CAPROTO_PV_PREFIX
    )

    print(f"Wait for {wait} seconds...")
    ttime.sleep(wait)

    yield p

    p.terminate()

    std_out, std_err = p.communicate()
    std_out = std_out.decode()
    sep = "=" * 80
    print(f"STDOUT:\n{sep}\n{std_out}")
    print(f"STDERR:\n{sep}\n{std_err}")


@pytest.fixture
def base_ophyd_device():
    dev = OphydDeviceWithCaprotoIOC(
        OPHYD_PV_PREFIX, name="ophyd_device_with_caproto_ioc"
    )
    yield dev
    dev.ioc_stage.put("unstaged")


@pytest.fixture(scope="session")
def caproto_ioc_channel_types(wait=5):
    p = start_ioc_subprocess(
        ioc_name="srx_caproto_iocs.example.caproto_ioc", pv_prefix=CAPROTO_PV_PREFIX
    )

    print(f"Wait for {wait} seconds...")
    ttime.sleep(wait)

    yield p

    p.terminate()

    std_out, std_err = p.communicate()
    std_out = std_out.decode()
    sep = "=" * 80
    print(f"STDOUT:\n{sep}\n{std_out}")
    print(f"STDERR:\n{sep}\n{std_err}")


@pytest.fixture
def ophyd_channel_types():
    dev = OphydChannelTypes(OPHYD_PV_PREFIX, name="ophyd_channel_type")
    letters = iter(string.ascii_letters)
    for cpt in sorted(dev.component_names):
        getattr(dev, cpt).put(next(letters))
    return dev


@pytest.fixture(scope="session")
def zebra_caproto_ioc(wait=5):
    p = start_ioc_subprocess(
        ioc_name="srx_caproto_iocs.zebra.caproto_ioc",
        pv_prefix=ZEBRA_CAPROTO_PV_PREFIX,
    )

    print(f"Wait for {wait} seconds...")
    ttime.sleep(wait)

    yield p

    p.terminate()

    std_out, std_err = p.communicate()
    std_out = std_out.decode()
    sep = "=" * 80
    print(f"STDOUT:\n{sep}\n{std_out}")
    print(f"STDERR:\n{sep}\n{std_err}")


@pytest.fixture(scope="session")
def zebra_caproto_ioc_custom_map(wait=5):
    """ZebraSaveIOC with a custom --dataset-map overriding the SRX defaults."""
    custom_map = {"ch1": "x_pos", "ch2": "y_pos", "ch3": "z_pos", "ch4": "t"}
    p = start_ioc_subprocess(
        ioc_name="srx_caproto_iocs.zebra.caproto_ioc",
        pv_prefix="ZEBRA_CUSTOM:{{Dev:Save1}}:",
        extra_args=(f"--dataset-map={json.dumps(custom_map)}",),
    )

    print(f"Wait for {wait} seconds...")
    ttime.sleep(wait)

    yield p, custom_map

    p.terminate()

    std_out, std_err = p.communicate()
    std_out = std_out.decode()
    sep = "=" * 80
    print(f"STDOUT:\n{sep}\n{std_out}")
    print(f"STDERR:\n{sep}\n{std_err}")


@pytest.fixture
def zebra_ophyd_device():
    dev = ZebraWithCaprotoIOC(ZEBRA_OPHYD_PV_PREFIX, name="zebra_with_caproto_ioc")
    dev.wait_for_connection(timeout=30)
    yield dev
    dev.ioc_stage.put("unstaged", timeout=10)


@pytest.fixture
def zebra_ophyd_device_custom_map():
    prefix = "ZEBRA_CUSTOM:{Dev:Save1}:"
    dev = ZebraWithCaprotoIOC(prefix, name="zebra_custom_map")
    dev.wait_for_connection(timeout=30)
    yield dev
    dev.ioc_stage.put("unstaged", timeout=10)

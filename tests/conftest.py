from __future__ import annotations

import os
import socket
import string
import subprocess
import sys
import time as ttime

import pytest

from srx_caproto_iocs.base import OphydDeviceWithCaprotoIOC
from srx_caproto_iocs.example.ophyd import OphydChannelTypes

CAPROTO_PV_PREFIX = "BASE:{{Dev:Save1}}:"
OPHYD_PV_PREFIX = CAPROTO_PV_PREFIX.replace("{{", "{").replace("}}", "}")


def get_epics_env():
    first_three = ".".join(socket.gethostbyname(socket.gethostname()).split(".")[:3])
    broadcast = f"{first_three}.255"

    print(f"{broadcast = }")

    # from pprint import pformat
    # import netifaces
    # interfaces = netifaces.interfaces()
    # print(f"{interfaces = }")
    # for interface in interfaces:
    #     addrs = netifaces.ifaddresses(interface)
    #     try:
    #         print(f"{interface = }: {pformat(addrs[netifaces.AF_INET])}")
    #     except Exception as e:
    #         print(f"{interface = }: exception:\n  {e}")

    return {
        "EPICS_CAS_BEACON_ADDR_LIST": os.getenv("EPICS_CA_ADDR_LIST", broadcast),
        "EPICS_CAS_AUTO_BEACON_ADDR_LIST": "no",
    }


def start_ioc_subprocess(ioc_name="srx_caproto_iocs.base", pv_prefix=CAPROTO_PV_PREFIX):
    env = get_epics_env()

    command = f"{sys.executable} -m {ioc_name} --prefix={pv_prefix} --list-pvs"
    print(
        f"\nStarting caproto IOC in via a fixture using the following command:\n\n  {command}\n"
    )
    os.environ.update(env)
    return subprocess.Popen(
        command.split(),
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

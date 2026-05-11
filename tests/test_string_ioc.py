from __future__ import annotations

import re
import string
import subprocess

import pytest

LIMIT = 39
STRING_39 = string.ascii_letters[:LIMIT]
STRING_LONGER = string.ascii_letters


@pytest.mark.cloud_friendly
@pytest.mark.parametrize("value", [STRING_39, STRING_LONGER])
def test_strings(
    caproto_ioc_channel_types,
    ophyd_channel_types,
    value,
):
    ophyd_channel_types.bare_string.put(value)

    if len(value) <= LIMIT:
        ophyd_channel_types.implicit_string_type.put(value)
    else:
        with pytest.raises(ValueError, match="byte string too long"):
            ophyd_channel_types.implicit_string_type.put(value)

    if len(value) <= LIMIT:
        ophyd_channel_types.string_type.put(value)
    else:
        with pytest.raises(ValueError, match="byte string too long"):
            ophyd_channel_types.string_type.put(value)

    if len(value) <= LIMIT:
        ophyd_channel_types.string_type_enum.put(value)
    else:
        with pytest.raises(ValueError, match="byte string too long"):
            ophyd_channel_types.string_type_enum.put(value)

    if len(value) <= LIMIT:
        ophyd_channel_types.char_type_as_string.put(value)
    else:
        with pytest.raises(ValueError, match="byte string too long"):
            ophyd_channel_types.char_type_as_string.put(value)

    ophyd_channel_types.char_type.put(value)


@pytest.mark.cloud_friendly
@pytest.mark.needs_epics_core
def test_cainfo(caproto_ioc_channel_types, ophyd_channel_types):
    for cpt in sorted(ophyd_channel_types.component_names):
        command = ["cainfo", getattr(ophyd_channel_types, cpt).pvname]
        command_str = " ".join(command)
        ret = subprocess.run(
            command,
            check=False,
            capture_output=True,
        )
        stdout = ret.stdout.decode()
        print(
            f"command: {command_str}\n  {ret.returncode=}\n  STDOUT:\n{ret.stdout.decode()}\n  STDERR:\n{ret.stderr.decode()}\n"
        )
        assert ret.returncode == 0
        if cpt in [
            "char_type_as_string",
            "implicit_string_type",
            "string_type",
            "string_type_enum",
        ]:
            assert "Native data type: DBF_STRING" in stdout
        else:
            assert "Native data type: DBF_CHAR" in stdout


@pytest.mark.cloud_friendly
@pytest.mark.needs_epics_core
@pytest.mark.parametrize("value", [STRING_39, STRING_LONGER])
def test_caput(caproto_ioc_channel_types, ophyd_channel_types, value):
    option = ""
    for cpt in sorted(ophyd_channel_types.component_names):
        if cpt in [
            "char_type_as_string",
            "implicit_string_type",
            "string_type",
            "string_type_enum",
        ]:
            option = "-s"
            would_trim = True
        else:
            option = "-S"
            would_trim = False
        command = ["caput", option, getattr(ophyd_channel_types, cpt).pvname, value]
        command_str = " ".join(command)
        ret = subprocess.run(
            command,
            check=False,
            capture_output=True,
        )
        stdout = ret.stdout.decode()
        print(
            f"command: {command_str}\n  {ret.returncode=}\n  STDOUT:\n{stdout}\n  STDERR:\n{ret.stderr.decode()}\n"
        )
        assert ret.returncode == 0
        actual = re.search("New : (.*)", stdout).group(1).split()[-1].rstrip()
        if not would_trim or len(value) == LIMIT:
            assert actual == value
        else:
            assert len(actual) < len(value)

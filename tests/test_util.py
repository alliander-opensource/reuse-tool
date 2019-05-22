# SPDX-Copyright: 2017-2019 Free Software Foundation Europe e.V.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for reuse._util"""

# pylint: disable=protected-access

import os
import pwd
from argparse import ArgumentTypeError
from pathlib import Path

import pytest
from boolean.boolean import ParseError
from license_expression import LicenseSymbol

from reuse import _util
from reuse._util import _LICENSING

# pylint: disable=invalid-name
git = pytest.mark.skipif(not _util.GIT_EXE, reason="requires git")
no_root = pytest.mark.xfail(
    pwd.getpwuid(os.getuid()).pw_name == "root",
    reason="fails when user is root",
)


def test_extract_expression():
    """Parse various expressions."""
    expressions = ["GPL-3.0+", "GPL-3.0 AND CC0-1.0", "nonsense"]
    for expression in expressions:
        result = _util.extract_spdx_info(
            "SPDX" "-License-Identifier: {}".format(expression)
        )
        assert result.spdx_expressions == {_LICENSING.parse(expression)}


def test_extract_erroneous_expression():
    """Parse an incorrect expression."""
    expression = "SPDX" "-License-Identifier: GPL-3.0-or-later AND (MIT OR)"
    with pytest.raises(ParseError):
        _util.extract_spdx_info(expression)


def test_extract_no_info():
    """Given a file without SPDX information, return an empty SpdxInfo
    object.
    """
    result = _util.extract_spdx_info("")
    assert result == _util.SpdxInfo(set(), set())


def test_extract_copyright():
    """Given a file with copyright information, have it return that copyright
    information.
    """
    copyright = "2019 Jane Doe"
    result = _util.extract_spdx_info("SPDX-Copyright: {}".format(copyright))
    assert result.copyright_lines == {copyright}


def test_extract_copyright_duplicate():
    """When a copyright line is duplicated, only yield one."""
    copyright = "2019 Jane Doe"
    result = _util.extract_spdx_info(
        "SPDX-Copyright: {}\n".format(copyright) * 2
    )
    assert result.copyright_lines == {copyright}


def test_extract_valid_license():
    """Correctly extract valid license identifier tag from file."""
    text = "Valid-License-Identifier: MIT"
    result = _util.extract_valid_license(text)
    assert result == {"MIT"}


def test_copyright_from_dep5(copyright):
    """Verify that the glob in the dep5 file is matched."""
    result = _util._copyright_from_dep5("doc/foo.rst", copyright)
    assert LicenseSymbol("CC0-1.0") in result.spdx_expressions
    assert "2017 Mary Sue" in result.copyright_lines


@git
def test_find_root_in_git_repo(git_repository):
    """When using reuse from a child directory in a Git repo, always find the
    root directory.
    """
    os.chdir("src")
    result = _util.find_root()

    assert Path(result).absolute().resolve() == git_repository


# pylint: disable=unused-argument


def test_pathtype_read_simple(fake_repository):
    """Get a Path to a readable file."""
    result = _util.PathType("r")("src/source_code.py")

    assert result == Path("src/source_code.py")


def test_pathtype_read_directory(fake_repository):
    """Get a Path to a readable directory."""
    result = _util.PathType("r")("src")

    assert result == Path("src")


def test_pathtype_read_directory_force_file(fake_repository):
    """Cannot read a directory when a file is forced."""
    with pytest.raises(ArgumentTypeError):
        _util.PathType("r", force_file=True)("src")


@root
def test_pathtype_read_not_readable(fake_repository):
    """Cannot read a nonreadable file."""
    os.chmod("src/source_code.py", 0o000)

    with pytest.raises(ArgumentTypeError):
        _util.PathType("r")("src/source_code.py")


def test_pathtype_read_not_exists(empty_directory):
    """Cannot read a file that does not exist."""
    with pytest.raises(ArgumentTypeError):
        _util.PathType("r")("foo.py")


def test_pathtype_write_not_exists(empty_directory):
    """Get a Path for a file that does not exist."""
    result = _util.PathType("w")("foo.py")

    assert result == Path("foo.py")


def test_pathtype_write_exists(fake_repository):
    """Get a Path for a file that exists."""
    result = _util.PathType("w")("src/source_code.py")

    assert result == Path("src/source_code.py")


def test_pathtype_write_directory(fake_repository):
    """Cannot write to directory."""
    with pytest.raises(ArgumentTypeError):
        _util.PathType("w")("src")


@root
def test_pathtype_write_exists_but_not_writeable(fake_repository):
    """Cannot get Path of file that exists but isn't writeable."""
    os.chmod("src/source_code.py", 0o000)

    with pytest.raises(ArgumentTypeError):
        _util.PathType("w")("src/source_code.py")


@root
def test_pathtype_write_not_exist_but_directory_not_writeable(fake_repository):
    """Cannot get Path of file that does not exist but directory isn't
    writeable.
    """
    os.chmod("src", 0o000)

    with pytest.raises(ArgumentTypeError):
        _util.PathType("w")("src/foo.py")


def test_pathtype_invalid_mode(empty_directory):
    """Only valid modes are 'r' and 'w'."""
    with pytest.raises(ValueError):
        _util.PathType("o")

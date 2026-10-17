'''Offline smoke tests for pyqbclient.

Run by default and make no network calls.
'''

import pytest

import pyqbclient as pyqbc

# Internal helpers/globals live in the submodule; `import *` does not re-export
# underscore names, and it snapshots module globals at import time.
from pyqbclient import pyqbclient as _impl


# ----------------------------------------------------------------- offline --

def test_package_imports_from_src():
    # Proves `import pyqbclient` resolves to the local src/ tree.
    assert pyqbc.__file__.endswith("src/pyqbclient/__init__.py")


def test_public_api_surface():
    for name in (
        "Client",
        "set_default",
        "Error",
        "ResponseError",
        "QuickBaseError",
    ):
        assert hasattr(pyqbc, name), f"missing public name: {name}"


def test_set_default_sets_module_defaults():
    pyqbc.set_default(
        realm_hostname="example-realm.quickbase.com", user_token="token"
    )
    try:
        assert _impl.default_realm_hostname == "example-realm.quickbase.com"
        assert _impl.default_user_token == "token"
    finally:
        pyqbc.set_default(realm_hostname=None, user_token=None)


def test_slice_list_returns_windows_of_100():
    values = list(range(250))
    assert _impl._slice_list(0, values) == values[:100]
    assert _impl._slice_list(100, values) == values[100:200]
    assert _impl._slice_list(200, values) == values[200:]


def test_client_without_credentials_raises():
    pyqbc.set_default(realm_hostname=None, user_token=None)
    with pytest.raises(ValueError):
        pyqbc.Client("bq12345")

import json
import os
from pathlib import Path

import pandas as pd
import pytest
from dotenv import load_dotenv

import pyqbclient as pyqbc

# Load credentials from test/.env regardless of the directory pytest runs from.
load_dotenv(Path(__file__).parent / ".env")

# A real 1x1 PNG, base64 encoded, so file tests need no external asset.
PNG_1X1_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk"
    "YAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


def pytest_addoption(parser):
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="run tests that hit the live QuickBase API",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "live: test that hits the live QuickBase API"
    )
    config.addinivalue_line(
        "markers", "slow: heavy live test (transfers a large payload)"
    )


# ------------------------------------------------------------- live client --

@pytest.fixture(scope='session')
def live(request):
    '''Skip unless the run was started with --live.'''
    if not request.config.getoption("--live"):
        pytest.skip("live test, run with: pytest --live")
    return True


@pytest.fixture(scope='session')
def creds():
    '''Realm/token/table pulled from tests/.env.'''
    realm = os.getenv("REALM")
    token = os.getenv("TOKEN")
    table = os.getenv("TEST_TABLE")
    if not all((realm, token, table)):
        pytest.skip("REALM, TOKEN and TEST_TABLE must be set in tests/.env")
    return realm, token, table


@pytest.fixture(scope='session')
def client(live, creds):
    '''A live Client. Only created when --live is passed.'''
    realm, token, table = creds
    return pyqbc.Client(table, realm_hostname=realm, user_token=token)


# ------------------------------------------------------- offline fake client --

class FakeResponse:
    '''Minimal stand-in for a requests.Response.'''

    def __init__(self, text='', status_code=200, payload=None):
        self.text = text
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if self._payload is not None:
            return self._payload
        return json.loads(self.text)

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')


@pytest.fixture
def fake_response():
    return FakeResponse


def _field_data():
    '''A synthetic stand-in for the fields API response.'''
    return pd.DataFrame({
        'id': [3, 6, 7, 8, 9, 10, 11, 12, 13, 14],
        'label': ['Record ID#', 'Name', 'Amount', 'Active', 'Created',
                  'Attachment', 'Serial', 'Count', 'CountU', 'DueDate'],
        'unique': [True, False, False, False, False, False, True, False, False,
                   False],
        'required': [False, False, False, False, False, False, False, False,
                     False, False],
        'fieldType': ['recordid', 'text', 'numeric', 'checkbox', 'datetime',
                      'file', 'text', 'numeric', 'numeric', 'date'],
    })


@pytest.fixture
def fake_client():
    '''A fully wired Client that never touches the network.'''
    c = pyqbc.Client.__new__(pyqbc.Client)
    c.table_id = 'bq123456'
    c.base_params = {'tableId': c.table_id}
    c.base_json_url = 'https://api.quickbase.com/v1/'
    c.realm_hostname = 'example-realm.quickbase.com'
    c.user_token = 'test-token'
    c.retries = 0
    c.dataframe = pd.DataFrame()
    c.headers = {
        'QB-Realm-Hostname': c.realm_hostname,
        'Authorization': c.user_token,
    }
    c._get_base_xml_request()
    c._get_base_xml_headers()
    c._get_xml_url()
    c.table_name = 'Sample Table'
    c.field_data = _field_data()
    c.column_dict = c._get_column_dict()
    c.label_dict = c._get_label_dict()
    c.rename_dict = c._get_rename_dict()
    c.inv_label_dict = c._get_inv_label_dict()
    c.reports = pd.DataFrame({
        'name': ['List All', 'New Table Report'],
        'type': ['table', 'table'],
        'query': [
            {'fields': [], 'filter': '', 'groupBy': [],
             'sortBy': [{'fieldId': 6, 'order': 'ASC'}]},
            {'fields': [3, 6], 'filter': "{'6'.EX.'alpha'}", 'groupBy': [],
             'sortBy': []},
        ],
    })
    c.valid_reports = c._get_valid_reports()
    c.merge_dicts = {}
    return c


# ---------------------------------------------------------------- sample data --

@pytest.fixture
def sample_df():
    '''Small tabular data spanning the pandas dtypes the client supports.'''
    return pd.DataFrame({
        'Name': pd.Series(['alpha', 'beta', 'gamma'], dtype='object'),
        'Amount': pd.Series([1.5, 2.25, 3.0], dtype='float64'),
        'Active': pd.Series([True, False, True], dtype='bool'),
        'Created': pd.to_datetime(['2024-01-01', '2024-02-01', '2024-03-01']),
        'Serial': pd.Series(['s1', 's2', 's3'], dtype='object'),
        'Count': pd.Series([1, 2, 3], dtype='Int32'),
        'CountU': pd.Series([4, 5, 6], dtype='UInt32'),
    })


@pytest.fixture
def new_fields_df():
    '''One column per supported dtype, none present in the fake table.

    Datetime is deliberately excluded here and covered by its own test, since
    its pandas dtype string varies by version.
    '''
    return pd.DataFrame({
        'NewText': pd.Series(['a', 'b'], dtype='object'),
        'NewNum': pd.Series([1.0, 2.0], dtype='float64'),
        'NewInt': pd.Series([1, 2], dtype='int64'),
        'NewBool': pd.Series([True, False], dtype='bool'),
        'NewI32': pd.Series([1, 2], dtype='Int32'),
        'NewU32': pd.Series([3, 4], dtype='UInt32'),
    })


@pytest.fixture
def png_b64():
    '''A base64 encoded 1x1 PNG.'''
    return PNG_1X1_B64

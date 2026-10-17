'''Self-contained, idempotent live flow against TEST_TABLE.

Only runs with ``pytest --live``. Every run starts from and returns to the
table's built-in fields only (ids 1-5):

    1. delete every record
    2. delete every field outside the built-ins
    3. create the fields the flow needs
    4. exercise records, filters, reports, field management and files
    5. clean up back to built-ins only

Because steps 1-2 run before seeding and again on teardown, running the suite
twice leaves the table in the same prov.

DESTRUCTIVE: point TEST_TABLE at a throwaway table.
'''

import numpy as np
import pandas as pd
import pytest

pytestmark = pytest.mark.live

BUILT_IN_IDS = {1, 2, 3, 4, 5}

# fields the flow creates up front and removes on teardown
FLOW_FIELDS = [
    {'label': 'name', 'fieldType': 'text'},
    {'label': 'prov', 'fieldType': 'text'},
    {'label': 'amount', 'fieldType': 'numeric'},
    {'label': 'test_field', 'fieldType': 'text'},
    {'label': 'blob', 'fieldType': 'text'},
    {'label': 'when', 'fieldType': 'datetime'},
    {'label': 'file_attachment', 'fieldType': 'file'},
]

SEED = pd.DataFrame({
    'name': ['alpha', 'beta', 'gamma', 'delta', 'epsilon'],
    'prov': ['ON', 'NS', 'NB', 'SK', 'PE'],
    'amount': [1.0, 2.0, 3.0, 4.0, 5.0],
    'test_field': ['seed-0', 'seed-1', 'seed-2', 'seed-3', 'seed-4'],
})


def _non_default_fields(client):
    '''Labels of every field that is not one of the built-ins.'''
    return [
        label for label, fid in client.inv_label_dict.items()
        if int(fid) not in BUILT_IN_IDS
    ]


def _reset(client):
    '''Wipe all records and every non-built-in field.'''
    client.delete_records(all_records=True)
    extra = _non_default_fields(client)
    if extra:
        client.delete_fields(extra)


@pytest.fixture(scope='module')
def flow(client):
    _reset(client)
    client.create_fields(field_dict=FLOW_FIELDS)
    client.post_data(external_df=SEED)
    yield client
    _reset(client)


# --------------------------------------------------------------- fetch data --

def test_01_fetch_seeded_records(flow):
    df = flow.get_data(columns=['name', 'prov', 'amount'])
    assert len(df) == len(SEED)
    assert set(df['name']) == set(SEED['name'])


def test_02_fetch_specific_columns(flow):
    df = flow.get_data(columns=['name'])
    assert list(df.columns) == ['name']


def test_03_fetch_all_columns(flow):
    df = flow.get_data(all_columns=True)
    assert len(df) == len(SEED)
    for col in ('name', 'prov', 'amount', 'test_field'):
        assert col in df.columns


def test_04_fetch_where(flow):
    df = flow.get_data(columns=['name'], where="{name.EX.'alpha'}")
    assert list(df['name']) == ['alpha']


def test_05_fetch_filter_list_dict(flow):
    df = flow.get_data(
        columns=['name'], filter_list_dict={'name': ['alpha', 'beta']}
    )
    assert set(df['name']) == {'alpha', 'beta'}


def test_06_fetch_from_report(flow):
    report = flow.valid_reports[0]
    df = flow.get_data(report=report)
    assert len(df) == len(SEED)


# --------------------------------------------------------------- write data --

def test_07_post_data_subset(flow):
    df = pd.DataFrame({'name': ['subset-row'], 'prov': ['TX'], 'amount': [9.0]})
    flow.post_data(external_df=df, subset=['name'])
    fetched = flow.get_data(
        columns=['name', 'prov'], where="{name.EX.'subset-row'}"
    )
    assert len(fetched) == 1
    prov = fetched['prov'].iloc[0]
    assert pd.isna(prov) or prov == ''


def test_08_post_data_exclude_columns(flow):
    df = pd.DataFrame({'name': ['exclude-row'], 'prov': ['TX'], 'amount': [8.0]})
    flow.post_data(external_df=df, exclude_columns=['prov'])
    fetched = flow.get_data(
        columns=['name', 'prov'], where="{name.EX.'exclude-row'}"
    )
    assert len(fetched) == 1
    prov = fetched['prov'].iloc[0]
    assert pd.isna(prov) or prov == ''


# ----------------------------------------------------------- field lifecycle --

def test_09_create_fields_from_dataframe(flow):
    df = pd.DataFrame({
        'df_text': pd.Series(['a'], dtype='object'),
        'df_num': pd.Series([1.0], dtype='float64'),
        'df_bool': pd.Series([True], dtype='bool'),
        'df_date': pd.to_datetime(['2024-01-01']),
    })
    created = flow.create_fields(external_df=df)
    try:
        labels = {f['label'] for f in created}
        assert {'df_text', 'df_num', 'df_bool', 'df_date'} <= labels
    finally:
        flow.delete_fields(['df_text', 'df_num', 'df_bool', 'df_date'])


def test_10_field_dict_create_update_delete(flow):
    created = flow.create_fields(
        field_dict={'label': 'temp_field', 'fieldType': 'text'}
    )
    assert any(f['label'] == 'temp_field' for f in created)
    assert 'temp_field' in flow.inv_label_dict

    flow.update_field('temp_field', fieldHelp='temporary field')

    deleted = flow.delete_fields(['temp_field'])
    assert deleted
    assert 'temp_field' not in flow.inv_label_dict


# -------------------------------------------------------------------- files --

def test_11_file_upload_download_roundtrip(flow, png_b64):
    df = flow.get_data(columns=['name', 'Record ID#'], where="{name.EX.'alpha'}")
    rid = int(df['Record ID#'].iloc[0])

    uploaded = flow.upload_files(
        'file_attachment',
        {'roundtrip.png': {'file_str': png_b64, 'merge_value': rid}},
        merge_field='Record ID#',
    )
    assert uploaded and uploaded[0]['rid'] == str(rid)

    files = flow.download_files(
        'file_attachment', where=f'{{Record ID#.EX.{rid}}}'
    )
    match = [f for f in files if f['file_name'] == 'roundtrip.png']
    assert match, f'uploaded file not found, got {files}'
    assert match[0]['file_str'] == png_b64


# ---------------------------------------------------------------- pagination --

@pytest.mark.slow
def test_12_large_dataframe_roundtrip_paginates(flow, monkeypatch):
    '''Exercise the chunked upload and the paginated download.

    Quickbase paginates by response size (~25MB per page), not by a fixed row
    count, so a large payload is the only way to make the download loop run.
    ~15,000 x 4KB rows is ~60MB, which reliably splits into several pages.
    '''
    n = 15000
    blob = 'x' * 4000
    rng = np.random.default_rng(20240101)
    df = pd.DataFrame({
        'name': [f'page-{i}' for i in range(n)],
        'test_field': ['page-marker'] * n,
        'amount': rng.integers(0, 1_000_000, n),
        'blob': [blob] * n,
    })

    calls = {'upload': 0, 'download': 0}
    original = flow._json_request

    def counting(*args, **kwargs):
        if args[3] == 'response':
            calls['upload'] += 1
        elif args[3] == 'dataframe':
            calls['download'] += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(flow, '_json_request', counting)

    # small step -> many upload requests
    result = flow.post_data(external_df=df, step=1000)
    assert result['totalNumberOfRecordsProcessed'] == n
    assert len(result['createdRecordIds']) == n
    assert calls['upload'] > 1, 'upload was not chunked'

    # large response -> the download loop pages through the results
    fetched = flow.get_data(
        columns=['name', 'amount', 'blob'],
        where="{test_field.EX.'page-marker'}",
    )
    assert calls['download'] > 1, 'download was not paginated'
    assert len(fetched) == n
    assert set(fetched['name']) == set(df['name'])
    assert set(fetched['blob']) == {blob}
    assert sorted(fetched['amount'].astype('int64').tolist()) == \
        sorted(df['amount'].tolist())


# ------------------------------------------------------------------ datetime --

def test_13_datetime_upload_roundtrip(flow):
    '''Quickbase rejects epoch ms; pyqbclient must send ISO 8601 UTC.'''
    df = pd.DataFrame({'name': ['dt-row'],
                       'when': pd.to_datetime(['2019-12-18 12:00:00'])})
    with pytest.warns(UserWarning, match='assumed to be UTC'):
        flow.post_data(external_df=df)
    fetched = flow.get_data(
        columns=['name', 'when'], where="{name.EX.'dt-row'}"
    )
    assert fetched['when'].iloc[0] == '2019-12-18T12:00:00Z'

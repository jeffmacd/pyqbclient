'''Offline tests: exercise client logic without hitting the QuickBase API.

These use the network-free ``fake_client`` fixture and monkeypatch
``_json_request`` / ``_xml_request`` where a call would otherwise be made.
'''

import json

import pandas as pd
import pytest
from lxml import etree


# ------------------------------------------------------- sample data & dtypes --

def test_sample_data_covers_supported_dtypes(sample_df):
    dtypes = {c: str(t) for c, t in sample_df.dtypes.items()}
    assert dtypes['Name'] == 'object'
    assert dtypes['Amount'] == 'float64'
    assert dtypes['Active'] == 'bool'
    assert dtypes['Created'].startswith('datetime64')
    assert dtypes['Serial'] == 'object'
    assert dtypes['Count'] == 'Int32'
    assert dtypes['CountU'] == 'UInt32'


# ----------------------------------------------------------- translation dicts --

def test_field_data_builds_translation_dicts(fake_client):
    assert fake_client.column_dict['Name'] == 6
    assert fake_client.label_dict['6.value'] == 'Name'
    assert fake_client.inv_label_dict['Name'] == '6'
    assert fake_client.rename_dict['6.value'] == 'Name'
    # file sub-columns get human readable names
    assert fake_client.rename_dict['10.value.url'] == 'Attachment - url'


def test_get_filter_translates_labels_to_ids(fake_client):
    assert fake_client._get_filter("{Name.EX.'alpha'}") == "{6.EX.'alpha'}"


def test_get_filter_unknown_label_raises(fake_client):
    with pytest.raises(ValueError):
        fake_client._get_filter("{Bogus.EX.'alpha'}")


def test_gen_filter_from_list_quotes_each_value(fake_client):
    assert (
        fake_client._gen_filter_from_list(['a', 2], 'Name')
        == '{Name.EX."a"}OR{Name.EX."2"}'
    )


# ------------------------------------------------------------------ get_data --

def test_get_data_maps_field_ids_to_labels(fake_client, monkeypatch):
    query = pd.DataFrame({'3.value': [1, 2], '6.value': ['alpha', 'beta']})
    monkeypatch.setattr(
        fake_client, '_json_request',
        lambda *a, **k: (query.copy(), {'numRecords': 2, 'totalRecords': 2}),
    )
    result = fake_client.get_data()
    assert list(result.columns) == ['Record ID#', 'Name']
    assert len(result) == 2


def test_get_data_translates_where_filter(fake_client, monkeypatch):
    captured = {}
    query = pd.DataFrame({'6.value': ['alpha']})

    def fake_json_request(body, *a, **k):
        captured['body'] = body
        return query.copy(), {'numRecords': 1, 'totalRecords': 1}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    fake_client.get_data(where="{Name.EX.'alpha'}")
    assert captured['body']['where'] == "{6.EX.'alpha'}"


def test_get_data_rejects_invalid_kwargs(fake_client):
    with pytest.raises(ValueError):
        fake_client.get_data(bogus=1)


# ----------------------------------------------------------------- post_data --

def test_post_data_serializes_records(fake_client, monkeypatch, sample_df,
                                      fake_response):
    captured = {}

    def fake_json_request(body, request_type, api_type, return_type, *args):
        captured['body'] = body
        n = len(body['data'])
        metadata = {
            'totalNumberOfRecordsProcessed': n,
            'createdRecordIds': list(range(1, n + 1)),
            'unchangedRecordIds': [],
            'updatedRecordIds': [],
        }
        return fake_response(text=json.dumps({'metadata': metadata}))

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    result = fake_client.post_data(external_df=sample_df)

    assert result['totalNumberOfRecordsProcessed'] == 3
    assert result['createdRecordIds'] == [1, 2, 3]

    record = captured['body']['data'][0]
    # keys are field ids and every value is wrapped for the API
    assert set(record) == {'6', '7', '8', '9', '11', '12', '13'}
    assert record['6'] == {'value': 'alpha'}
    assert record['8'] == {'value': True}
    assert captured['body']['to'] == fake_client.table_id


def test_post_data_drops_unknown_columns(fake_client, monkeypatch, sample_df,
                                         fake_response):
    captured = {}

    def fake_json_request(body, request_type, api_type, return_type, *args):
        captured['body'] = body
        n = len(body['data'])
        return fake_response(text=json.dumps({'metadata': {
            'totalNumberOfRecordsProcessed': n,
            'createdRecordIds': [],
            'unchangedRecordIds': [],
            'updatedRecordIds': [],
        }}))

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    sample_df['Bogus'] = 'nope'
    fake_client.post_data(external_df=sample_df)
    assert 'Bogus' not in captured['body']['data'][0]


def test_post_data_rejects_non_unique_merge(fake_client, monkeypatch, sample_df,
                                            fake_response):
    monkeypatch.setattr(
        fake_client, '_json_request',
        lambda *a, **k: fake_response(text=json.dumps({'metadata': {}})),
    )
    with pytest.raises(ValueError):
        fake_client.post_data(external_df=sample_df, merge='Name')


def test_post_data_serializes_datetimes_as_iso_utc(fake_client, monkeypatch,
                                                   sample_df, fake_response):
    '''Quickbase rejects epoch milliseconds for date/datetime fields, so
    datetimes must go out as ISO 8601. Naive values are assumed to be UTC.'''
    captured = {}

    def fake_json_request(body, request_type, api_type, return_type, *args):
        captured['body'] = body
        n = len(body['data'])
        return fake_response(text=json.dumps({'metadata': {
            'totalNumberOfRecordsProcessed': n,
            'createdRecordIds': [],
            'unchangedRecordIds': [],
            'updatedRecordIds': [],
        }}))

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    with pytest.warns(UserWarning, match='assumed to be UTC'):
        fake_client.post_data(external_df=sample_df)
    # 'Created' is field id 9; 2024-01-01 -> ISO 8601 UTC with milliseconds
    assert captured['body']['data'][0]['9'] == {
        'value': '2024-01-01T00:00:00.000Z'
    }


def test_post_data_encodes_date_field_as_date_only(fake_client, monkeypatch,
                                                   fake_response):
    captured = {}

    def fake_json_request(body, *a, **k):
        captured['body'] = body
        return fake_response(text=_post_metadata(len(body['data'])))

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    df = pd.DataFrame({'DueDate': pd.to_datetime(['2024-01-01'])})
    with pytest.warns(UserWarning):
        fake_client.post_data(external_df=df)
    # 'DueDate' is field id 14 and a date field -> date only, no time
    assert captured['body']['data'][0]['14'] == {'value': '2024-01-01'}


def test_post_data_converts_tz_aware_datetimes_to_utc(fake_client, monkeypatch,
                                                      fake_response):
    captured = {}

    def fake_json_request(body, *a, **k):
        captured['body'] = body
        return fake_response(text=_post_metadata(len(body['data'])))

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    series = pd.Series(pd.to_datetime(['2024-01-01 12:00:00']))
    df = pd.DataFrame({'Created': series.dt.tz_localize('US/Pacific')})
    fake_client.post_data(external_df=df)
    # 12:00 PST (UTC-8) -> 20:00 UTC
    assert captured['body']['data'][0]['9'] == {
        'value': '2024-01-01T20:00:00.000Z'
    }


def test_post_data_omits_nat_datetimes(fake_client, monkeypatch, fake_response):
    captured = {}

    def fake_json_request(body, *a, **k):
        captured['body'] = body
        return fake_response(text=_post_metadata(len(body['data'])))

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    df = pd.DataFrame({'Created': pd.Series([pd.NaT], dtype='datetime64[ns]')})
    with pytest.warns(UserWarning):
        fake_client.post_data(external_df=df)
    assert '9' not in captured['body']['data'][0]


# -------------------------------------------------------------- create_fields --

def test_create_fields_maps_dtypes(fake_client, monkeypatch, new_fields_df):
    monkeypatch.setattr(fake_client, '_fetch_field_info', lambda: None)
    created = []

    def fake_json_request(body, request_type, api_type, return_type, *args):
        created.append(dict(body))
        return {'id': 100 + len(created), 'label': body['label']}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    result = fake_client.create_fields(external_df=new_fields_df)

    assert {c['label']: c['fieldType'] for c in created} == {
        'NewText': 'text',
        'NewNum': 'numeric',
        'NewInt': 'numeric',
        'NewBool': 'checkbox',
        'NewI32': 'numeric',
        'NewU32': 'numeric',
    }
    assert len(result) == 6


def test_create_fields_unknown_dtype_raises(fake_client, monkeypatch):
    monkeypatch.setattr(fake_client, '_fetch_field_info', lambda: None)
    df = pd.DataFrame({
        'Good': pd.Series([1.0, 2.0], dtype='float64'),
        'Bad': pd.Series(['x', 'y'], dtype='category'),
    })
    with pytest.raises(ValueError):
        fake_client.create_fields(external_df=df)


def test_create_fields_unknown_dtype_ignore_errors(fake_client, monkeypatch):
    monkeypatch.setattr(fake_client, '_fetch_field_info', lambda: None)
    created = []

    def fake_json_request(body, request_type, api_type, return_type, *args):
        created.append(dict(body))
        return {'id': 1, 'label': body['label']}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    df = pd.DataFrame({
        'Good': pd.Series([1.0, 2.0], dtype='float64'),
        'Bad': pd.Series(['x', 'y'], dtype='category'),
    })
    fake_client.create_fields(external_df=df, ignore_errors=True)
    assert [c['label'] for c in created] == ['Good']


def test_create_fields_handles_datetime_dtype(fake_client, monkeypatch):
    monkeypatch.setattr(fake_client, '_fetch_field_info', lambda: None)
    created = []

    def fake_json_request(body, request_type, api_type, return_type, *args):
        created.append(dict(body))
        return {'id': 1, 'label': body['label']}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    df = pd.DataFrame({'NewDate': pd.to_datetime(['2024-01-01', '2024-01-02'])})
    fake_client.create_fields(external_df=df)
    assert [c['fieldType'] for c in created] == ['datetime']


# --------------------------------------------------------------- file helpers --

def test_download_files_returns_base64(fake_client, monkeypatch, png_b64,
                                       fake_response):
    result_df = pd.DataFrame({
        'Record ID#': [1],
        'Attachment - url': ['https://example.com/9/abc'],
        'Attachment - versions': [[{'fileName': 'pic.png'}]],
    })
    monkeypatch.setattr(fake_client, 'get_data', lambda **kw: result_df)
    monkeypatch.setattr(
        fake_client, '_json_request',
        lambda *a, **k: fake_response(text=png_b64),
    )
    files = fake_client.download_files('Attachment')
    assert files == [{'fid_3_value': 1,
                      'file_name': 'pic.png',
                      'file_str': png_b64}]


def test_get_files_returns_dict_and_warns(fake_client, monkeypatch, png_b64,
                                          fake_response):
    result_df = pd.DataFrame({
        'Record ID#': [7],
        'Attachment - url': ['https://example.com/9/abc'],
    })
    monkeypatch.setattr(fake_client, 'get_data', lambda **kw: result_df)
    monkeypatch.setattr(
        fake_client, '_json_request',
        lambda *a, **k: fake_response(text=png_b64),
    )
    with pytest.warns(FutureWarning):
        files = fake_client.get_files('Attachment')
    assert files == {7: png_b64}


def test_upload_files_sends_base64(fake_client, monkeypatch, png_b64):
    merge_df = pd.DataFrame({'Serial': ['s1', 's2'], 'Record ID#': [11, 12]})
    monkeypatch.setattr(fake_client, 'get_data', lambda **kw: merge_df)

    xml = etree.fromstring(
        b'<qdbapi><errcode>0</errcode>'
        b'<rid>11</rid><update_id>3</update_id></qdbapi>'
    )
    captured = {}

    def fake_xml_request(action, data, stream=True):
        captured['action'] = action
        captured['data'] = data
        return xml

    monkeypatch.setattr(fake_client, '_xml_request', fake_xml_request)
    file_dict = {'pic.png': {'file_str': png_b64, 'merge_value': 's1'}}
    result = fake_client.upload_files('Attachment', file_dict,
                                      merge_field='Serial')

    assert result == [{'rid': '11', 'update_id': '3'}]
    assert captured['action'] == 'API_EditRecord'
    assert png_b64.encode() in captured['data']


def test_upload_files_invalid_merge_field(fake_client, png_b64):
    file_dict = {'pic.png': {'file_str': png_b64, 'merge_value': 's1'}}
    with pytest.raises(ValueError):
        fake_client.upload_files('Attachment', file_dict, merge_field='Name')


# ------------------------------------------------------------------- slicing --

def test_slice_df_returns_requested_window(fake_client, sample_df):
    fake_client.dataframe = sample_df
    sliced = fake_client._slice_df(1, step=1)
    assert list(sliced.index) == [1]


# --------------------------------------------------------------- get_data opts --

def test_get_data_all_columns_selects_every_field(fake_client, monkeypatch):
    captured = {}

    def fake_json_request(body, *a, **k):
        captured['body'] = body
        return pd.DataFrame({'6.value': ['a']}), {'numRecords': 1, 'totalRecords': 1}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    fake_client.get_data(all_columns=True)
    assert captured['body']['select'] == list(fake_client.label_dict.keys())


def test_get_data_filter_list_dict(fake_client, monkeypatch):
    captured = {}

    def fake_json_request(body, *a, **k):
        captured['body'] = body
        return pd.DataFrame({'6.value': ['alpha']}), {'numRecords': 1, 'totalRecords': 1}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    fake_client.get_data(filter_list_dict={'Name': ['alpha', 'beta']})
    assert captured['body']['where'] == '{6.EX."alpha"}OR{6.EX."beta"}'


def test_get_data_paginates_until_all_records_fetched(fake_client, monkeypatch):
    calls = []
    pages = [
        (pd.DataFrame({'6.value': ['a']}), {'numRecords': 1, 'totalRecords': 2}),
        (pd.DataFrame({'6.value': ['b']}), {'numRecords': 1, 'totalRecords': 2}),
    ]

    def fake_json_request(body, *a, **k):
        calls.append(dict(body))
        return pages[len(calls) - 1]

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    result = fake_client.get_data()
    assert len(calls) == 2
    assert calls[1]['options'] == {'skip': 1}
    assert list(result['Name']) == ['a', 'b']


# -------------------------------------------------------------------- reports --

def test_get_filter_translates_quoted_report_ids(fake_client):
    # report filters use the {'6'.OP.'v'} form; the API wants {6.OP.'v'}
    assert (
        fake_client._get_filter("{'6'.EX.'alpha'}", record=True)
        == "{6.EX.'alpha'}"
    )


def test_get_data_from_report_uses_query(fake_client, monkeypatch):
    captured = {}

    def fake_json_request(body, *a, **k):
        captured['body'] = body
        return pd.DataFrame({'3.value': [1]}), {'numRecords': 1, 'totalRecords': 1}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    fake_client.get_data(report='New Table Report')
    assert captured['body']['select'] == [3, 6]
    assert captured['body']['where'] == "{6.EX.'alpha'}"


def test_get_data_from_report_uses_report_sort(fake_client, monkeypatch):
    captured = {}

    def fake_json_request(body, *a, **k):
        captured['body'] = body
        return pd.DataFrame({'3.value': [1]}), {'numRecords': 1, 'totalRecords': 1}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    fake_client.get_data(report='List All')
    assert captured['body']['sortBy'] == [{'fieldId': 6, 'order': 'ASC'}]


def test_get_data_report_rejects_other_args(fake_client):
    with pytest.raises(ValueError):
        fake_client.get_data(report='List All', columns=['Name'])


def test_get_data_invalid_report_raises(fake_client):
    with pytest.raises(ValueError):
        fake_client.get_data(report='Nope')


# -------------------------------------------------------- create_fields paths --

def test_create_fields_from_field_dict(fake_client, monkeypatch):
    monkeypatch.setattr(fake_client, '_fetch_field_info', lambda: None)
    created = []

    def fake_json_request(body, *a, **k):
        created.append(dict(body))
        return {'label': body['label'], 'id': 200}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    result = fake_client.create_fields(
        field_dict={'label': 'X', 'fieldType': 'text'}
    )
    assert created == [{'label': 'X', 'fieldType': 'text'}]
    assert result == [{'label': 'X', 'id': 200}]


def test_create_fields_from_field_dict_list(fake_client, monkeypatch):
    monkeypatch.setattr(fake_client, '_fetch_field_info', lambda: None)
    created = []

    def fake_json_request(body, *a, **k):
        created.append(dict(body))
        return {'label': body['label']}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    fake_client.create_fields(field_dict=[{'label': 'A'}, {'label': 'B'}])
    assert [c['label'] for c in created] == ['A', 'B']


def test_create_fields_appears_by_default_false(fake_client, monkeypatch):
    monkeypatch.setattr(fake_client, '_fetch_field_info', lambda: None)
    created = []

    def fake_json_request(body, *a, **k):
        created.append(dict(body))
        return {'label': body['label']}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    fake_client.create_fields(field_dict={'label': 'X'}, appearsByDefault=False)
    assert created[0]['appearsByDefault'] is False


# --------------------------------------------------------------- update_field --

def test_update_field_with_kwargs(fake_client, monkeypatch):
    monkeypatch.setattr(fake_client, '_fetch_field_info', lambda: None)
    captured = {}

    def fake_json_request(body, request_type, api_type, return_type, *args):
        captured['body'] = body
        captured['args'] = args
        return {'label': 'Name', 'required': True}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    result = fake_client.update_field('Name', required=True)
    assert captured['body'] == {'required': True}
    assert captured['args'] == ('6',)
    assert result == {'label': 'Name', 'required': True}


def test_update_field_with_dict(fake_client, monkeypatch):
    monkeypatch.setattr(fake_client, '_fetch_field_info', lambda: None)
    captured = {}

    def fake_json_request(body, request_type, api_type, return_type, *args):
        captured['body'] = body
        return {'label': 'Name'}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    fake_client.update_field('Name', field_dict={'bold': True})
    assert captured['body'] == {'bold': True}


def test_update_field_requires_args(fake_client):
    with pytest.raises(ValueError):
        fake_client.update_field('Name')


def test_update_field_rejects_invalid_kwarg(fake_client):
    with pytest.raises(ValueError):
        fake_client.update_field('Name', bogus=True)


def test_update_field_rejects_invalid_label(fake_client):
    with pytest.raises(ValueError):
        fake_client.update_field('Nope', bold=True)


def test_update_field_rejects_non_string_label(fake_client):
    with pytest.raises(TypeError):
        fake_client.update_field(6, bold=True)


# --------------------------------------------------------------- delete_fields --

def test_delete_fields_returns_deleted_ids(fake_client, monkeypatch):
    monkeypatch.setattr(fake_client, '_fetch_field_info', lambda: None)
    captured = {}

    def fake_json_request(body, request_type, api_type, return_type, *args):
        captured['body'] = body
        return {'deletedFieldIds': [12]}

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    result = fake_client.delete_fields(['Count'])
    assert result == [12]
    assert captured['body'] == {'fieldIds': [12]}


def test_delete_fields_rejects_builtin(fake_client):
    with pytest.raises(ValueError):
        fake_client.delete_fields(['Record ID#'])


def test_delete_fields_rejects_invalid_label(fake_client):
    with pytest.raises(ValueError):
        fake_client.delete_fields(['Nope'])


def test_delete_fields_requires_list(fake_client):
    with pytest.raises(ValueError):
        fake_client.delete_fields('Name')


# ------------------------------------------------------ post_data column selection --

def _post_metadata(n):
    return json.dumps({'metadata': {
        'totalNumberOfRecordsProcessed': n,
        'createdRecordIds': list(range(1, n + 1)),
        'unchangedRecordIds': [],
        'updatedRecordIds': [],
    }})


def test_post_data_subset_keeps_only_listed(fake_client, monkeypatch, sample_df,
                                            fake_response):
    captured = {}

    def fake_json_request(body, *a, **k):
        captured['body'] = body
        return fake_response(text=_post_metadata(len(body['data'])))

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    fake_client.post_data(external_df=sample_df, subset=['Name', 'Serial'])
    assert set(captured['body']['data'][0]) == {'6', '11'}


def test_post_data_exclude_columns(fake_client, monkeypatch, sample_df,
                                   fake_response):
    captured = {}

    def fake_json_request(body, *a, **k):
        captured['body'] = body
        return fake_response(text=_post_metadata(len(body['data'])))

    monkeypatch.setattr(fake_client, '_json_request', fake_json_request)
    fake_client.post_data(external_df=sample_df,
                          exclude_columns=['Name', 'Amount'])
    record = captured['body']['data'][0]
    assert '6' not in record and '7' not in record

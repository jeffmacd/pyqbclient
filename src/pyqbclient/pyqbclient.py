from __future__ import annotations
import json
import numpy as np
import requests
import pandas as pd
from io import StringIO
import requests
import re
from lxml import etree
import logging
from typing import Union, Tuple
import time
import warnings

logger = logging.getLogger("pyqbclient")


    
class Error(Exception):
    '''
    Base Error.
    '''

    def __init__(self, code, msg, response=None):
        self.args = (code, msg)
        self.msg = (code, msg)
        self.desc = code
        self.response = response

    def __str__(self):
        return f'{self.msg}: {self.desc}'



class ResponseError(Error):
    pass


class QuickBaseError(Error):
    pass


default_realm_hostname = None
default_user_token = None

def set_default(realm_hostname: str=None, user_token:str =None) -> None:
    '''
    Set default realm hostname and user token for use by any Client.

    Parameters
    ----------
    realm_hostname : str, optional
        The realm hostname of the QuickBase account.
    user_token : str, optional
        The user token of the QuickBase account.
    
    Returns
    -------
    None
    '''
    
    global default_realm_hostname
    global default_user_token

    default_realm_hostname = realm_hostname
    default_user_token = user_token

def _slice_list(start_index: int, filter_list: list) -> list:
    '''
    Get a slice of a list of len 100 or shorter.

    Parameters
    ----------
    start_index : int
        The index to start the slice from.
    filter_list : list
        The list to be sliced.

    Returns
    -------
    list
        A list of length 100 starting from the start_index.
    '''

    end_line = start_index + 100
    slice = filter_list[start_index:end_line:]
    return slice  

class Client(object):


    def _check_defaults(self, realm_hostname: str, user_token: str) -> None:
        '''
        Function that checks for default host and user token, uses arguments
        provided to Client if found.
        
        Parameters
        ----------
        realm_hostname : str
            The realm hostname of the QuickBase account.
        user_token : str
            The user token of the QuickBase account.
        
        Returns
        -------
        None

        Raises
        ------
        ValueError
            If realm_hostname not provided without a default set.
        ValueError
            If user_token not provided without a default set.
        '''

        if default_realm_hostname == None:
            if realm_hostname == None:
                raise ValueError('Must provide a realm hostname')
            self.realm_hostname = realm_hostname
        else:
            if realm_hostname != None:
                self.realm_hostname = realm_hostname
            else:
                self.realm_hostname = default_realm_hostname
        
        if default_user_token == None:
            if user_token == None:
                raise ValueError('Must provide a user token')
            self.user_token = f'QB-USER-TOKEN {user_token}'
        else:
            if user_token != None:
                self.user_token = f'QB-USER-TOKEN {user_token}'
            else:
                self.user_token = f'QB-USER-TOKEN {default_user_token}'


    def _set_retries(self, retries: int) -> None:
        '''
        Set the number of retries for this Client.

        Parameters
        ----------
        retries : int
            The number of retries to perform.

        Raises
        ------
        ValueError
            If the number of retries is less than 0.
        '''

        if retries < 0:
            raise ValueError('Retries must be 0 or greater')
        self.retries = retries
    

    def _json_request(self, body: str, request_type: str,
    api_type: str, return_type: str, *args) -> Union[requests.Response,
    pd.DataFrame, dict, Tuple[pd.DataFrame,dict]]:
        '''
        Make a request to the JSON API.

        Parameters
        ----------
        body : str
            The body of the request.
        request_type : str
            The type of request to make.
        api_type : str
            The type of API to make the request to.
        return_type : str
            The type of response to return.
        *args : list
            Additional string arguments for the URL.

        Returns
        -------
        Union[requests.Response, pd.DataFrame, dict, Tuple[pd.DataFrame, dict]]
            The response from the request.
        '''

        url =f'https://api.quickbase.com/v1/{api_type}'
        if  args:
            url = url + f'/{"/".join(args)}'
        
        for attempt in range(self.retries + 1):
            try:
                if request_type == 'post':
                    with requests.Session() as s:
                        r = s.post(
                        url, 
                        params = self.base_params, 
                        headers = self.headers, 
                        json = body
                        )

                    
                elif request_type == 'delete':
                    with requests.Session() as s:
                        r = s.delete(
                        url, 
                        params = self.base_params, 
                        headers = self.headers, 
                        json = body
                        )


                elif request_type == 'get':
                    with requests.Session() as s:
                        r = s.get(
                        url, 
                        params = self.base_params, 
                        headers = self.headers
                        )

                    
                try:
                    json_response = json.loads(r.text)
                except:

                    json_response = None
                

                if json_response and (request_type != 'get'): 
                    if "message" in json_response.keys():
                        raise QuickBaseError(
                         json_response['message'],
                         json_response['description']
                       ,
                        response=json_response
                        )
                    if "errors" in json_response.keys():
                        raise QuickBaseError(
                        'Request returned error(s):',
                        f'{", ".join(json_response["errors"])}',response=json_response
                        )
                if r.status_code not in [200,207]:
                        r.raise_for_status()
             

            except QuickBaseError:
                logger.critical('Quickbase Error')
                raise
            except Exception as e:    
                if attempt < self.retries:
                    logger.error(e)
                    logger.info(f'Retrying  - Attempt {attempt +1}')
                    time.sleep(10)
                    continue
                else:
                    logger.critical(e)
                    raise
            break

        if return_type == 'json':
            return json_response
        elif return_type == 'dataframe':
            df = pd.json_normalize(json_response['data'])
            metadata = json_response['metadata']
            return df, metadata
        elif return_type == 'properties':

            json_data = pd.read_json(StringIO(r.text))
            properties = json_data.join(
            pd.json_normalize(
            json_data.pop('properties')
            ))
            return properties
        
        elif return_type == 'response':
            return r
        
    
    def _get_fields(self) -> pd.DataFrame:
        '''
        This function retrieves field information for the table.

        Parameters
        ----------
        None

        Returns
        -------
        pd.DataFrame
            A Pandas dataframe containing the fields and their properties.
        '''

        params = self.base_params
        params['includeFieldPerms'] = 'false'
        return self._json_request(None,'get','fields','properties') 


    def _get_reports(self) -> pd.DataFrame:
        '''
        This function retrieves report information for the table.

        Parameters
        ----------
        None

        Returns
        -------
        pd.DataFrame
            A DataFrame of available reports.
        '''
        
        return self._json_request(
        None,
        'get',
        'reports',
        'properties'
        )  


    def _get_valid_reports(self) -> list:
        '''
        Parse the available reports for table type reports.

        Parameters
        ----------
        None

        Returns
        -------
        list
            A list of names of the table type reports available for the table.
        '''

        return     self.reports.loc[
        self.reports['type'].eq('table'),'name'].to_list()


    def _get_column_dict(self) -> dict:
        '''
        Get a dictionary for translating from field labels to field ids.

        Returns
        -------
        dict
            A dictionary with field label as key and field id as value.
        '''

        pared_fields = self.field_data.loc[:,['id','label',]].copy()
        pared_fields.loc[:,'id'] = pared_fields.loc[:,'id']
        column_dict  = pared_fields.set_index('label').to_dict()['id']
        
        return column_dict 


    def _get_label_dict(self) -> dict:
        '''
        Get a dictionary for translating from field ids to field labels.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            A dictionary with field id as key and field label as value.
        '''

        pared_fields = self.field_data.loc[:,['id','label',]].copy()
        pared_fields.loc[:,'id'] = pared_fields.loc[:,'id'].astype(str) + '.value'
        label_dict = pared_fields.set_index('id').to_dict()['label']
        
        return label_dict 


    def _get_rename_dict(self) -> dict:
        '''
        Get a dictionary for translating query response labels.

        Parameters
        ----------
        None

        Returns
        -------
        dict 
            A dictionary for translating query response labels.
        '''

        labels =list(self.label_dict.keys())
        values = list(self.label_dict.values())
        rename_dict = self.label_dict.copy()
        sub_values = [
            'name', 'id', 'email', 'userName', 'url','versions'
        ]
 
        for i  in range(0,len(labels)):
            rename_dict[
            int(f"{labels[i].replace('.value','')}")
            ] = values[i]

            rename_dict[
            f"'{labels[i].replace('.value','')}'"
            ] = int(f"{labels[i].replace('.value','')}")
            for j in range(0,len(sub_values)):
                rename_dict[
                f'{labels[i]}.{sub_values[j]}'
                ] = f'{values[i]} - {sub_values[j]}'
          
        return rename_dict


    def _get_inv_label_dict(self) -> dict:
        '''
        Returns dictionary for translating field labels to field id strings.

        Parameters
        ----------
        None

        Returns
        -------
        dict
            The inverse label dictionary.
        '''

        inv_label_dict = {
        v: str(k).replace('.value','') for k, v in self.label_dict.items()
        }
        return inv_label_dict
    

    def _get_base_xml_request(self) -> None:
        '''
        Sets base XML request parameters for the Client.

        Parameters
        ----------
        None

        Returns
        -------
        None 
        '''

        request = {}
        request['encoding'] = 'UTF-8'
        request['msInUTC'] = 1
        request['realmhost'] = self.realm_hostname
        request['apptoken'] = self.user_token
        self.base_xml_request = request


    def _get_base_xml_headers(self) -> None:
        '''
        Sets base XML headers for the Client.

        Parameters
        ----------
        None

        Returns
        -------
        None 
        '''

        self.base_xml_headers = {
        'User-Agent': '{User-Agent}',
        'Authorization': self.user_token,
        'Content-Type': 'application/xml'
        }
    

    def _get_xml_url(self) -> None:
        '''
        Sets the XML url of the table.

        Parameters
        ----------
        None

        Returns
        -------
        None
        '''

        self.xml_url = f'https://{self.realm_hostname}/db/{self.table_id}'


    def _build_request(self, **request_fields) -> str:
        r'''
        Build QuickBase request XML with given fields. Fields can be straight
        key=value, or if value is a 2-tuple it represents (attr_dict, value), or if
        value is a list of values or 2-tuples the output will contain multiple entries.

        Parameters
        ----------
        request_fields : dict
            A dictionary of key value pairs for the XML.

        Returns
        -------
        str
            An XML string for the request.
        '''

        request = etree.Element('qdbapi')
        doc = etree.ElementTree(request)

        def add_sub_element(field, value):
            if isinstance(value, tuple):
                attrib, value = value
                attrib = dict((k, str(v)) for k, v in attrib.items())
            else:
                attrib = {}
            sub_element = etree.SubElement(request, field, **attrib)
            if not isinstance(value, str):
                value = str(value)
            sub_element.text = value

        for field, values in request_fields.items():
            if not isinstance(values, list):
                values = [values]
            for value in values:
                add_sub_element(field, value)

        return etree.tostring(doc, xml_declaration=True, encoding="utf-8")


    def _xml_request(self, action: str, data: str, 
    stream: bool=True) -> etree.Element:
        '''
        Sends a request to Quickbase using the XML API.

        Parameters
        ----------
        action : str
            The name of the Quickbase action that is being performed.
        data : str
            The XML data being sent to Quickbase.
        stream : bool, default True
            Whether the response is streamed.

        Returns
        -------
        etree.Element
            Parsed XML element

        Raises
        ------
        ResponseError
            If the response from Quickbase contains an error code other than 0.
        HTTPError
            If the request status is not 200.
        '''

        headers = self.base_xml_headers
        headers['QUICKBASE-ACTION'] = action
        response = ""

        for attempt in range(self.retries + 1):
            try:

                response = requests.post(
                self.xml_url, data, headers=headers, stream=stream
                )
                if response.status_code != 200:
                    response.raise_for_status()

            except Exception as e:

                if attempt < self.retries:
                    logger.error(e)
                    logger.info(f'Retrying  - Attempt {attempt +1}')
                    continue
                else:
                    raise
            break

        parsed = etree.fromstring(
        response.text.encode('ascii',errors='replace')
        ) 
        error_code = parsed.findtext('errcode')
        if error_code is None:
            raise ResponseError(
            -4, '"errcode" not in response', response=response
            )
        if error_code != '0':
            error_text = parsed.find('errtext')
            error_text = error_text.text if error_text is not\
            None else '[no error text]'
            raise ResponseError(error_code, error_text, response=response)

        return parsed


    def _get_table_name(self) -> str:
        '''
        Returns table name of the QuickBase table.

        Parameters
        ----------
        None

        Returns:
        -------
        str
            The name of the QuickBase table.        
        '''

        request = self.base_xml_request
        data = self._build_request(**request)
        response = self._xml_request('API_GetSchema', data)
        return response.xpath('//table/name')[0].text
    

    def _fetch_field_info(self) -> None:
        '''
        Retrieves and stores field_data and creates dictionaries for translation.

        Parameters
        ----------
        None

        Returns:
        -------
        None
        '''

        self.field_data = self._get_fields()
        self.column_dict = self._get_column_dict()
        self.label_dict = self._get_label_dict()
        self.rename_dict = self._get_rename_dict()
        self.inv_label_dict = self._get_inv_label_dict()


    def __init__(self, table_id: str, realm_hostname: str=None,
    user_token: str=None, retries: int=3, 
    dataframe: pd.DataFrame=None) -> Client:
        '''
        A Client object for interacting with a Quickbase Table.

        Parameters
        ----------
        table_id : str
            The table ID of the Quickbase table
        realm_hostname : str, default None
            The realm hostname of the Quickbase table.
        user_token : str, default None
            The user token of the Quickbase table.
        retries : int, default 3
            The number of times to retry a request.
        dataframe : pd.DataFrame, optional
            A dataframe to use for the client.

        Returns
        -------
        Client
            A Client object for interacting with a Quickbase Table.

        Raises
        ------
        ValueError
            If realm_hostname not provided without a default set.
        ValueError
            If user_token not provided without a default set.
        '''

        self.table_id = table_id
        self.base_params = {
            'tableId': self.table_id
        }
        self.base_json_url = 'https://api.quickbase.com/v1/'

        self._check_defaults(realm_hostname, user_token)
        self._set_retries(retries)
        if not isinstance(dataframe, pd.DataFrame):
            dataframe = pd.DataFrame()
        self.dataframe =  dataframe
        self.headers = {
            'QB-Realm-Hostname': self.realm_hostname,
            'User-Agent': '{User-Agent}',
            'Authorization': self.user_token
        }
        self._get_base_xml_request()
        self._get_base_xml_headers()
        self._get_xml_url()
        self.table_name = self._get_table_name()
        self._fetch_field_info()
        self.reports = self._get_reports()
        self.valid_reports = self._get_valid_reports()
        self.merge_dicts = {}
        logger.info(f'Created Client for table "{self.table_name}"')
        

    def _get_filter(self, filter_criteria: str, record: bool=False) -> str:
        '''
        Translates between ids and labels for use in filters.

        Example: {My_Field_Label.EX.'My Value'} might become {6.EX.'My Value'}

        Parameters
        ----------
        filter_criteria : str
            A string containing the filter criteria.
        record : bool, default False
            Whether to translate to or from field labels.
    
        Returns
        -------
        str
            A translated query string.

        Raises
        ------
        ValueError
            If field labels provided are not found in field information.
        '''

        error_list = []
        pattern = re.compile(r'{(.*?)[.]')
        filter_list = []

        ## Extract field ids/labels to replace
        for m in re.finditer(pattern, filter_criteria):
            if str(m.group()).replace(
                '{',''
                ).replace('.','') not in filter_list:
                filter_list.append(str(m.group()).replace(
                '{','').replace('.','')
                )

        ## Translating labels to ids
        if record ==False:
            for k in filter_list:
                if k in filter_criteria:
                    try:
                        filter_criteria = filter_criteria.replace(
                        k,str(self.inv_label_dict[k])
                        )
                    except KeyError:
                        error_list.append(k)
            if len(error_list) > 0:
                raise ValueError(f'''Invalid field label(s) "{'", "'.join(error_list)}" '''
                                 f'''found in filter for {self.table_name}''')
        
        ## Translating id strings to ints
        else:
            for k in filter_list:
                if k in filter_criteria:
                    filter_criteria = filter_criteria.replace(
                    k,str(self.rename_dict[k])
                    )
        
        return filter_criteria


    def _gen_filter_from_list(self, filter_list: list, 
    filter_list_label: str) -> str:
        '''
        Generates a filter string with labels translated to field ids.

        Parameters
        ----------
        filter_list : list
            A list of strings to filter on.
        filter_list_label : str
            The label of the field being filered.

        Returns
        -------
        str
            The filter as a string.
        '''

        filter_list = [str(_) for _ in filter_list]
        where_str = f'{{{filter_list_label}.EX."' 
        join_str = f'"}}OR{{{filter_list_label}.EX."'
        return f'{where_str}{join_str.join(filter_list)}"}}'
         

    def get_data(self, report: str=None, columns: list=None, 
    all_columns: bool=False, overwrite_df: bool=True, return_copy: bool=True,
    filter_list_dict: dict=None, where: str=None, **kwargs) -> pd.DataFrame:
        '''
        Queries data from a Quickbase table and returns a DataFrame.

        Parameters
        ----------
        report : str, optional
            A report to retrieve data from. Reports must be found in the Client's
            valid_reports attribute, a list which can be accessed at 
            Client.valid_reports.
        columns : list, optional
            A list of field labels to return data for.
            Will raise a ValueError if specified when report is specified.
            If not specified default table fields will be returned.
            If all_columns is True this argument is ignored.
        all_columns : bool, default False
            If True all fields will be returned.
            Will raise a ValueError if specified when report is specified.
        overwrite_df : bool, default True
            If True the Client's dataframe attribute will be overwritten with the
            result.
        return_copy : bool, default True
            If True a copy of the result will be returned.
        filter_list_dict : dict, optional
            A dictionary of lists where the key is the column name and the list is
            a list of values to be filtered by.
            Will raise a ValueError if specified when report is specified.
        where : str, optional
            A string of the form "{My_Field_Label.EX.'My Value'}" to filter by,
            consult the documentation for more information.
            Will raise a ValueError if specified when report is specified.
            If filter_list_dict is specified this argument is ignored.
        **kwargs :
            kwargs can be used to specify the optional sortBy and groupBy arguments.
            The value must be a list of dictionaries.
            Will raise a ValueError if specified when report is specified.

            sortBy : list
                The sort order as a list of dictionaries.
                The dictionary keys are 'fieldId' and 'order'.
                The order must be 'ASC' or 'DESC'.
                The example listed below is provided as a default.
                Example: [{'fieldId': 2, 'order': 'DESC'}]

            groupBy : list, default None
                The group order as a list of dictionaries.
                The dictionary keys are 'fieldId' and 'order'.
                The order must be 'ASC', 'DESC' or 'equal-values'.
                Example: [{'fieldId': 2, 'grouping': 'ASC'}]

        Returns
        -------
        pd.DataFrame
            A pandas dataframe of the retrieved data.
        '''

        valid_kwargs = [
        'sortBy',
        'groupBy'
        ]
        body = {"from":self.table_id}
        # Without a default sort order does not behave as expected
        body['sortBy'] = [{'fieldId': 2, 'order': 'DESC'}]
        if report:
            if any([filter_list_dict,columns,all_columns,where,kwargs]):
                raise ValueError(
                'Columns,filters and kwargs can not be specified with a report'
                )
            if report not in self.valid_reports:
                raise ValueError(
                f'"{report}" is not a valid table type report for'
                f' {self.table_name}'
                )

            for k, v in self.reports.loc[
            self.reports['name'].eq(report),'query'
            ].to_dict().items():
                body['select'] = v['fields']
                body['where'] = self._get_filter(v['filter'],record=True)
                if len(v['sortBy']) > 0:
                    body['sortBy'] = v['sortBy']
                if len(v['groupBy']) > 0:
                    body['groupBy'] = v['groupBy']

        if columns:
            try:
                body['select'] = [self.column_dict[c] for c in columns]
            except KeyError as e:
                raise ValueError(
                f'Invalid Column {e} provided.'
                )
        if all_columns:
            body['select'] = list(self.label_dict.keys())
        if where:
            if not isinstance(filter_list_dict, type(None)):
                raise ValueError('Can not specify where with a filter list')
            body['where']  = self._get_filter(where)

  
        invalid_kwargs = []
        for kw in kwargs:
            if kw  in valid_kwargs:
                body[kw] = kwargs[kw]
            else:
                invalid_kwargs.append(kw)

        if len(invalid_kwargs)>0:
            raise ValueError(f'Invalid Kwargs {", ".join(invalid_kwargs)}')

        if isinstance(filter_list_dict, dict):
            df_list = []
            retrieved = 0 

            for k,v in filter_list_dict.items():

                list_length = len(v)
                iter_np = np.arange(0, list_length, 100)
                iter = list(iter_np)
                
                for i in iter:
                    slice = _slice_list(i,v)
                    body['where'] = self._get_filter(self._gen_filter_from_list(
                    slice,
                    k)
                    )
                    df, metadata = self._json_request(
                    body,
                    'post',
                    'records',
                    'dataframe',
                    'query',
                    )
                    df_list.append(df)
                    retrieved += metadata['numRecords']
        
        else:
            df_list = []
            retrieved = 0 
            df, metadata = self._json_request(
            body,
            'post',
            'records',
            'dataframe',
            'query',
            )
            df_list.append(df)
            retrieved = metadata['numRecords']
            if metadata['totalRecords'] > metadata['numRecords']:
                body['options'] = {"skip": retrieved}
                remaining = metadata['totalRecords'] -  metadata['numRecords']
                while remaining > 0:
                    df, metadata = self._json_request(
                    body,
                    'post',
                    'records',
                    'dataframe',
                    'query',
                    )
                    retrieved += metadata['numRecords']
                    remaining = metadata['totalRecords'] - retrieved
                    body['options'] = {"skip": retrieved}
                    df_list.append(df)

        result = pd.concat(df_list)
        logger.info(f'Retrieved {retrieved} records from {self.table_name}')
        result.columns = result.columns.to_series().map(self.rename_dict)

        if overwrite_df  == True:
            self.dataframe = result
        if return_copy == True:
            return result.copy()
        else:
            return result


    def download_files(self, file_field: str, where: str= None, 
    filter_list_dict: dict = None ) -> list:
        '''
        Get a list of dictionaries with Field ID 3 values, file names and 
        and base64 encoded file strings as values.

        Parameters
        ----------
        file_field : str
            The field label of the file field.
        where: str, optional
            A string of the form "{My_Field_Label.EX.'My Value'}" to filter by,
            consult the documentation for more information.
            If filter_list_dict is specified this argument is ignored.
        filter_list_dict : dict, optional
            A dictionary of lists where the key is the column name and the list is

        Returns
        -------
        list
            A list of dictionaries in the form:
            { 
                'fid_3_value': fid_3_value,
                'file_name': file_name,
                'file_str':  file_str
            }
        '''

        record_label = self.field_data.loc[
        self.field_data['id']==3,
        'label'
        ].to_string(index=False)

        columns = [record_label, file_field ]


        result = self.get_data(columns=columns,
                               where=where,
                               filter_list_dict=filter_list_dict)
        
        return_list = []
        retrieved = len(result.index)
        if retrieved == 0:
            logger.info(f'Found {retrieved} records from '
                        f'{self.table_name} matching the filter criteria')
            return return_list

        url_column = f'{file_field} - url'
        versions_column = f'{file_field} - versions'

        has_files = result.loc[result[url_column] != ''].copy()

        has_file_count = len(has_files.index)
        logger.info(f'Found {has_file_count} records from '
                    f'{self.table_name} with files in the {file_field} field')
        if has_file_count == 0:
            return return_list

        has_files['file_names'] = has_files[versions_column].apply(
            lambda x: x[-1]['fileName']
        )
        
        record_list = has_files[record_label].tolist()
        file_urls = has_files[url_column].tolist()
        file_names = has_files['file_names'].tolist()

        for index, url  in enumerate(file_urls):
            url = url[7:]
            file_str = self._json_request(None,
                                          'get',
                                          'files',
                                          'response',
                                          url
                                          ).text
            return_list.append({ 'fid_3_value': record_list[index],
                                 'file_name': file_names[index],
                                 'file_str':  file_str})

        return return_list


    def get_files(self, file_field: str, where: str= None, 
    filter_list_dict: dict = None ) -> list:
        '''
        Get a dict with Field Id 3 values as keys and 
        base64 encoded file strings as values.

        Parameters
        ----------
        file_field : str
            The field label of the file field.
        where : str, optional
            A string of the form "{My_Field_Label.EX.'My Value'}" to filter by,
            consult the documentation for more information.
            If filter_list_dict is specified this argument is ignored.
        filter_list_dict : dict, optional
            A dictionary of lists where the key is the column name and the list is
            a list of values to be filtered by.

        Returns
        -------
        dict
            A dictionary in the form:
            { 
                fid_3_value:  file_str
            }
        '''
        warnings.warn("This function will be deprecated in favor of download_files in v1.3.0", 
                      FutureWarning)
        record_label = self.field_data.loc[
        self.field_data['id']==3,
        'label'
        ].to_string(index=False)

        columns = [record_label, file_field ]


        result = self.get_data(columns=columns,
                               where=where,
                               filter_list_dict=filter_list_dict)
        
        return_dict = {}
        retrieved = len(result.index)
        if retrieved == 0:
            logger.info(f'Found {retrieved} records from '
                        f'{self.table_name} matching the filter criteria')
            return return_dict

        url_column = f'{file_field} - url'

        has_files = result.loc[result[url_column] != ''].copy()

        has_file_count = len(has_files.index)
        logger.info(f'Found {has_file_count} records from '
                    f'{self.table_name} with files in the {file_field} field')
        if has_file_count == 0:
            return return_dict


        record_list = has_files[record_label].tolist()
        file_urls = has_files[url_column].tolist()
        for index, url  in enumerate(file_urls):
            url = url[7:]
            file_str = self._json_request(None,
                                          'get',
                                          'files',
                                          'response',
                                          url
                                          ).text
            return_dict[record_list[index]] = file_str

        return return_dict

    def create_fields(self, field_dict: Union[dict,list]=None, 
    external_df: pd.DataFrame=None, ignore_errors: bool=False, 
    appearsByDefault: bool=True) -> list[dict]:
        '''
        Creates fields in a Quickbase table. Can create based on columns 
        in a DataFrame or based on a field_dict of desired attributes.

        Parameters
        ----------
        field_dict : Union[dict,list], optional
            A dictionary or list of dictionaries with the field information.
            Consult the Quickbase documentation for more info.
        external_df : pd.DataFrame, optional
            A Pandas DataFrame. If passed, the fields will be created       
            based on the columns of the DataFrame.
            The Pandas datatype must be one of the following:
            'float64', 'int64', 'datetime64[ns]', 'object', 'bool',
            'int32', 'UInt32', 'Int32'.
            If the datatype is not known, the field will not be created.   
        ignore_errors : bool, default False
            If True, the function will not fail if field creation fails. 
        appearsByDefault : bool, default True
            If True, the field will appear by default in the Table.     
            Default is True.

        Returns
        -------
        list
            A list of created field dictionaries.
        '''

        type_dict = {
        'float64': 'numeric',
        'int64': 'numeric',
        'datetime64[ns]': 'datetime',
        'object': 'text',
        'bool': 'checkbox',
        'int32': 'numeric',
        'UInt32': 'numeric',
        'Int32': 'numeric'
        }

        logger.info('Preparing to create fields')

        return_list = []
        if field_dict:
            if isinstance(field_dict, dict):
                field_dict = [field_dict]
            
            for fd in field_dict:
                body = fd
                if appearsByDefault == False:
                    body['appearsByDefault'] = False
                response = self._json_request(
                body,'post','fields','json'
                )
                logger.info(f'''Added field "{response['label']}"'''
                f' to {self.table_name}'
                )
                return_list.append(response)
                
            self._fetch_field_info()    
            return return_list
             
        if external_df is not None:
            self.dataframe = external_df.copy()
       
        body = {}

        unknown_columns = [
            col for col in self.dataframe.columns \
            if col not in self.rename_dict.values()
        ]

        
        if len(unknown_columns) > 0:
            
            dtypes_dict = self.dataframe.dtypes.to_dict()
            unknown_dict = {
            str(k): str(v) for k, v in dtypes_dict.items(
            ) if k in unknown_columns
            }

            counter = 0
            counter_dict = {}
            for k,v in unknown_dict.items():
                counter += 1
                if v not in type_dict.keys():
                    
                    counter_dict[k] =v

            if len(counter_dict) > 0 and len(counter_dict) < len(unknown_dict):
                if ignore_errors==False and len(counter_dict) > 0:
                    error_string = ''
                    for k,v in counter_dict.items():
                        error_string += f'Column: {k} datatype: {v}\n'
                    logger.error(
                    f'Unknown Pandas datatypes:\n'
                    f'{error_string}'   
                    )
                    raise ValueError(f'Unknown Pandas datatypes:\n'
                    f'{error_string}'
                    )
                else:
                    
                    for k,v in counter_dict.items():
                        logger.warning(
                            f'Unknown Pandas datatype {v} for column {k},'
                            f' field not created'
                        )
                        unknown_dict.pop(k)
                        
                    for k,v in unknown_dict.items():
  
                        if appearsByDefault == False:
                            body['appearsByDefault'] = False

                        body['label'] = k
                        body['fieldType']=type_dict[v]
                        response = self._json_request(
                        body,'post','fields','json'
                        )
                        return_list.append(response)
                        logger.info(
                        f'''Added field "{response['label']}"'''
                        f' to {self.table_name}'
                        )
                        
                    self._fetch_field_info()    
                    return return_list
             

            elif len(counter_dict) == len(unknown_dict):
                for k,v in counter_dict.items():
                    logger.warning(
                    f'Unknown Pandas datatype {v} for column {k},'
                    f' field not created'
                    )
                return return_list
            else:
                
                for k,v in unknown_dict.items():

                    if appearsByDefault == False:
                        body['appearsByDefault'] = False

                    body['label'] = k
                    body['fieldType']=type_dict[v]
                    response = self._json_request(
                    body,'post','fields','json'
                    )
                    return_list.append(response)
                    logger.info(
                    f'''Added field "{response['label']}"'''
                    f' to {self.table_name}'
                    )
                self._fetch_field_info()
                return return_list   
        else:
            
            logger.info('No unknown fields found')
            return return_list


    def update_field(self, field_label: str, field_dict: dict=None,
    **kwargs) -> dict:
        '''
        This function takes a field label and a field dictionary or key word 
        arguments and then updates the field with the provided information.

        Parameters
        ----------
        field_label : str
            The label of the field to be updated.
        field_dict : dict, default None
            A dictionary of the field information to be updated. Valid keys are:
            'label', 'noWrap', 'bold', 'required', 'appearsByDefault',
            'findEnabled', 'unique', 'fieldHelp', 'addToForms', 'properties'
        **kwargs
            Valid keys are: 'label', 'noWrap', 'bold', 'required', 
            'appearsByDefault', 'findEnabled', 'unique', 'fieldHelp', 
            'addToForms', 'properties'

        Returns
        -------
        dict
            A dictionary of the updated field information.

        Raises
        ------
        ValueError
            If neither field_dict or kwargs are passed to the function.
        ValueError
            If invalid keys are passed in kwargs or field_dict.
        TypeError
            If field_label is not a string.
        TypeError
            If field_dict is not a dictionary.
        ValueError
            If the field_label is not a valid  field label for the table.
        '''

        valid_args = [
        "label", "noWrap", "bold", "required", "appearsByDefault",
        "findEnabled", "unique", "fieldHelp", "addToForms", "properties"
        ]
        if  not any([kwargs,field_dict]):
            raise ValueError(
            'Must provide a field dict or a key word argument'
            )
        if kwargs:
            if not all([i in valid_args  for i in kwargs]):
                inv_args = [
                '"' + str(i) + '"' for i in kwargs if i not in valid_args
                ]
                raise ValueError(
                f'Invalid argument(s) {", ".join(inv_args)}.'
                )
        if field_dict:
            if type(field_dict) != dict:
                raise TypeError("'field_dict' must be a dictionary.")
            if not all([i in valid_args  for i in field_dict]):
                inv_args = [
                '"' + i + '"' for i in field_dict if i not in valid_args
                ]
                raise ValueError(f'Invalid argument(s) {", ".join(inv_args)}.')
        
        
        if type(field_label) != str:
            raise TypeError("'label' must be a string")
        if field_label not in self.inv_label_dict.keys():
            raise ValueError(
            f'{field_label} is not a valid label for table {self.table_id}'
            )
        body = {}
        if field_dict:
            body.update(field_dict)
        body.update(kwargs)
        

        response = self._json_request(
        body,
        'post',
        'fields',
        'json',
        f'{self.inv_label_dict[field_label]}'
        )
        
        
        logger.info(
            f'Updated field {self.inv_label_dict[field_label]} with'
            f' { {k: v for k, v in response.items() if k in body.keys()} }'
        )
        self._fetch_field_info()
        return response


    def delete_fields(self, field_labels: list) -> list:
        '''
        Delete field(s) from a Quickbase table.

        Parameters
        ----------
        field_labels : list
            A list of field labels.

        Returns
        -------
        list
            A list of deleted field ids.

        Raises
        ------
        ValueError
            If field_labels is not a list.
            If field_labels contains invalid field labels.
            If field_labels contains the label of a built in field.
        '''

        if not isinstance(field_labels,list):
            raise ValueError('Must supply a list of field labels to delete')

        invalid_labels = [
        l for l in field_labels if l not in list(self.inv_label_dict.keys())
        ]
        if len(invalid_labels)>0:
            raise ValueError(
            f'''Invalid fieldlabel(s) "{'", "'.join(invalid_labels)}".'''
            )

        body = {}
        body['fieldIds'] = [int(self.inv_label_dict[f]) for f in field_labels]
        built_ins = [_ for _ in range(1,6)]

        entered_built_ins = [
            self.rename_dict[i] for i in body['fieldIds'] if i in built_ins
        ]
        if len(entered_built_ins) > 0:
            err_str = ", ".join([f'"{b}"' for b in entered_built_ins])
            raise ValueError(f'Built in field(s) {err_str} can not be deleted')

        response = self._json_request(body,'delete','fields','json')
        deleted_field_ids = []
        for k, v in response.items():
            if k == 'deletedFieldIds':
                deleted_field_ids = v
                deleted_field_labels = [
                self.rename_dict[d] for d in v
                ]
                logger.info(f'''Deleted field(s) "{'", "'.join(deleted_field_labels)}"'''
                f' from {self.table_name}')

        self._fetch_field_info() 
        return deleted_field_ids
        

    def _slice_df(self, start_index: int, step: int=5000) -> pd.DataFrame:
        '''
        This method is used to slice the Client's dataframe by row.

        Parameters
        ----------
        start_index : int
            The index in the dataframe to start the slice from.
        step : int, default 5000
            The number of rows to slice.

        Returns
        -------
        pd.DataFrame
            The dataframe slice.
        '''

        end_index = start_index + step
        slice = self.dataframe.iloc[start_index:end_index,:]
        return slice


    def post_data(self, external_df: pd.DataFrame=None, step: int=5000, 
    merge: str=None, create_if_missing: bool=False, 
    exclude_columns: list=None, subset: list=None) -> dict:
        '''
        Upload a DataFrame to a Quickbase table.

        Parameters
        ----------
        external_df : pd.DataFrame
            Dataframe to be posted to Quickbase table.
        step : int, default 5000
            Number of rows to post per request.
        merge : str, optional
            Name of field to merge on.
        create_if_missing : bool, default False
            Create fields from DataFrame if they do not exist in the table.
        exclude_columns : list, optional
            List of columns to exclude from post.
        subset : list, optional
            List of columns to post.

        Returns
        -------
        dict
            createdRecordIds : list
                List of record ids that were created.
            unchangedRecordIds : list
                List of record ids that were unchanged.
            updatedRecordIds : list
                List of record ids that were updated.
            totalNumberOfRecordsProcessed : int
                Total number of records processed in the request.

        Raises
        -------
        ValueError
            If merge field is not unique.
        '''

        if  isinstance(external_df, pd.DataFrame):
            self.dataframe = external_df.copy()
        if exclude_columns:
            self.dataframe.drop(labels=exclude_columns, 
                                axis=1, 
                                inplace=True)
        if subset:
            
            labels_to_drop = [
            col for col in list(self.dataframe.columns)
            if col not in subset and col != merge
            ]
            self.dataframe.drop(
            labels=labels_to_drop,
            axis=1, 
            inplace=True
            )

        if create_if_missing ==True:
            self.create_fields(ignore_errors=True)

        self.dataframe = self.dataframe.rename(
        columns=self.inv_label_dict
        )
        if merge:
            if merge not in self.field_data.loc[
            self.field_data['unique']==True,'label'
            ].to_list():
                raise ValueError(
                'Merge columns must be unique, check Quickbase field settings'
                )

        unknown_columns = [
        col for col in self.dataframe.columns if col
        not in self.inv_label_dict.values()
        ]

        if len(unknown_columns) >= 1:
            logger.warning(f'Discovered unknown column(s) '
            f'''"{'", "'.join(unknown_columns)}".'''
            ' Unknown columns were dropped'
            )
            self.dataframe.drop(labels=unknown_columns, axis=1, inplace=True)

        dflength = len(self.dataframe.index)
        iter_np = np.arange(0, dflength, step)
        iter = list(iter_np)  
        req_total = int(np.ceil(dflength / step))
        req_nr = 1
        processed=0
        created = 0
        unchanged = 0
        updated = 0
        failed = 0

        id_lists = [
            'createdRecordIds',
            'unchangedRecordIds',
            'updatedRecordIds'
        ]
        response_dict = {}

        for id_list in id_lists:
            response_dict[id_list] = []

        for i in iter :
            slice = self._slice_df(i,step=step)
            logger.info(
            f'Sending Insert/ Update Records API request {req_nr} '
            f'out of {req_total}')
            df_json = slice.to_json(orient='records')
            df_json = json.loads(df_json)
            for l in df_json:
                for k,v in l.items():
                    v = str(v).replace('None','Null')
            df_json = [{key: {"value": value} for key, value in item.items(
            ) if value is not None} for item in df_json]
            data = {"to": self.table_id, "data": df_json}
            if merge:
                data["mergeFieldId"] = int(self.inv_label_dict[merge])
            
            response = self._json_request(
            data,
            'post',
            'records',
            'response'
            )
            metadata = json.loads(response.text)['metadata']
            processed  += metadata['totalNumberOfRecordsProcessed']
            created += len(metadata['createdRecordIds'])
            unchanged += len(metadata['unchangedRecordIds'])
            updated += len(metadata['updatedRecordIds'])

            for id_list in id_lists:
                response_dict[id_list] += metadata[id_list]
      
            if response.status_code == 200:
                logger.debug(f'Request {req_nr}: 0 no error')
            elif response.status_code == 207:
                count_dict={}
                for k,v in metadata["lineErrors"].items():
                    for item in v:
                        if item not in count_dict.keys():
                            count_dict[item] = 0;
                        count_dict[item] +=1
                for k,v in count_dict.items():
                    logger.error(f'Failed to insert {v} record(s) due to {k}')
                    failed +=v

                logger.debug(
                f'Request {req_nr}: {response}'
                f' {json.dumps(response.json())} \n'
                )
            else:
                logger.error(f'Failed to insert request {req_nr}. '
                 'Check debug logs for reason if enabled')

                logger.debug(f'Request {req_nr}: {response}' 
                f'{json.dumps(response.json())["description"]} \n')
            req_nr += 1
        
        response_dict['totalNumberOfRecordsProcessed'] = processed

        logger.info(f'Uploaded {processed} records to {self.table_name}, '
        f'created: {created}, unchanged: {unchanged}, updated: {updated}, '
        f'failed: {failed}'
        )

        return response_dict


    def delete_records(self, where: str=None, all_records: bool=False) -> dict:
        '''
        Deletes records from a Quickbase table.

        Parameters
        ----------
        where : str, optional
            A string of the form "{My_Field_Label.EX.'My Value'}" to filter by,
            consult the documentation for more information.
        all_records : bool, default False
            Deletes all records if set to True.

        Returns
        -------
        dict
            The API's response to the deletion request indicating the number 
            of records deleted.

        Raises
        ------
        ValueError
            Raised if where parameter is not provided and all_records is set to False.
        '''

        if where == None:
            if all_records == False:
                raise ValueError(
                'Must specify records to delete'
                )
        if all_records == True:
             body = {
            "from": self.table_id,
            "where": '{3.GT.0}'
            }
        elif where:
            body ={
            "from": self.table_id,
            "where":  f"{self._get_filter(where)}"
            }

        response = self._json_request(
        body,
        'delete',
        'records',
        'json'
        )
        
        logger.info(
        f'Deleted {response["numberDeleted"]} records from {self.table_name}'
        )

        return response


    def _get_merge_dict(self, merge_field: str, try_internal: bool) -> None:
        '''
        Creates a dictionary for use in uploading files.

        Parameters
        ----------
        merge_field : str
            The field that is used to match on.
        try_internal : bool
            If True will try to create the merge dict from the internal dataframe first.

        Returns
        -------
        None
        '''

        record_label = self.field_data.loc[
        self.field_data['id']==3,
        'label'
        ].to_string(index=False)
        if merge_field == record_label:
            if record_label in self.dataframe.columns and try_internal:
                self.merge_dicts[merge_field]  = dict(zip(
                self.dataframe[record_label].to_list(),
                self.dataframe[record_label].to_list()
                ))
                logger.debug(
                f'Created merge dict for {merge_field}'
                )
                return
            else:
                logger.info(
                'Downloading required fields to upload files'
                )
                merge_df = self.get_data(
                columns=[record_label],
                overwrite_df=False,
                return_copy=True
                )
                self.merge_dicts[merge_field]  = dict(zip(
                merge_df[record_label].to_list(),merge_df[record_label].to_list()
                ))
                logger.debug(
                f'Created merge dict for {merge_field}'
                )
                return

        if try_internal:
            if merge_field and record_label in self.dataframe.columns:
                self.merge_dicts[merge_field]  = dict(zip(
                self.dataframe[merge_field].to_list(),
                self.dataframe[record_label].to_list()
                ))
                logger.debug(
                f'Created merge dict for {merge_field}'
                )
                return
        logger.info(
        'Downloading required fields to upload files'
        )
        merge_df = self.get_data(
        columns=[merge_field,record_label],
        overwrite_df=False,
        return_copy=True
        )
        self.merge_dicts[merge_field]  = dict(zip(
        merge_df[merge_field].to_list(),merge_df[record_label].to_list()
        ))
        logger.debug(
        f'Created merge dict for {merge_field}'
        )
        
            
    def upload_files(self, field_label: str, file_dict: dict,
    merge_field: str, try_internal: bool=True) -> list[dict[str,str]]:
        '''
        Uploads files to Quickbase.

        Parameters
        ----------
        field_label : str
            The label of the field to upload to.
        file_dict : dict
            A dictionary containing files to be uploaded.
            The key is the filename with extension and the value should be a dictionary with 
            two keys:
            1. 'file_str' : The file as a Base64 encoded string.
            2. 'merge_value' : The value you are merging on in the merge_field.
            This must match the value of a record in the merge field.
        merge_field : str
            The field to merge the files on. This must be unique and in the table.
        try_internal : bool, default True
            Whether to use the internal merge dictionary.

        Returns
        -------
        list
            A list of dictionaries containing the record id and update id of the uploaded files.

        Raises
        ------
        ValueError
            If the merge field is not unique.
            If the merge value is not in the merge field.
        '''
    
        request = self.base_xml_request
        if merge_field not in self.field_data.loc[
        self.field_data['unique']==True,'label'
        ].to_list():
                raise ValueError(
                'Invalid merge field. Merge field must exist in the table'
                ' and be unique, check Quickbase field settings'
                )
       
        if merge_field not in self.merge_dicts.keys():
            self._get_merge_dict(merge_field,try_internal)

        uploaded_files = 0

        return_list = []

        for k, v in file_dict.items():
            try:
                request['rid'] = self.merge_dicts[merge_field][v['merge_value']]
            except KeyError:
                raise ValueError(
                f'"{v["merge_value"]}" not a valid value in {merge_field}'
                )
            request_field = (
            {'fid': self.inv_label_dict[field_label],
                'filename': k}, v['file_str'])
            request['field'] = [request_field]

            data = self._build_request(**request)
            response = self._xml_request('API_EditRecord',data)
            rid = response.xpath('//qdbapi/rid')[0].text
            update_id = response.xpath('//qdbapi/update_id')[0].text

            return_list.append({'rid': rid,
                                'update_id': update_id,
                                }
                            )
            uploaded_files +=1
        
        logger.info(f'Uploaded {uploaded_files} files to {self.table_name}')

        return return_list
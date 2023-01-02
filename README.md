<div id="top"></div>
<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Don't forget to give the project a star!
*** Thanks again! Now go create something AMAZING! :D
-->



<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
$~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~$[![Contributors][contributors-shield]][contributors-url]  [![Forks][forks-shield]][forks-url]  [![Stargazers][stars-shield]][stars-url]   [![Issues][issues-shield]][issues-url]   [![Downloads][downloads-shield]][downloads-url]   [![LinkedIn][linkedin-shield]][linkedin-url]    


<!-- PROJECT LOGO -->


<h3 align="center">pyqbclient</h3>

  <p align="center">
    Simple Quickbase Table client module
    <br />
    <br />
    <a href="https://github.com/jeffmacd/pyqbclient/issues">Report Bug</a>
    ·
    <a href="https://github.com/jeffmacd/pyqbclient/issues">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#requirements">Requirements</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contributing">Contributing</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>

## Version 1.2.0
* Added download_files function to client
* Added future deprecation warning for get_files
* Improved docstrings
* Refactored multiple functions
* Fixed bug in post_data where fields were created when subset was specified and field  was not in subset


## Version 1.1.1
* Added a function to download files
* Changed a docstring
* Added an error message for bad filter criteria


## Version 1.1.0
* Added return values for post_data, upload_files, create_fields, delete_fields, update_field, delete_records
* Added a ten second sleep before retrying JSON requests
* create_fields now allows for manual multiple field creation by accepting a list of field dicts to the argument field_dict, previously multiple fields were only created if called within post_data using a DataFrame
* Prefixed Client methods for internal use  with underscores


## Version 1.0.2
* Fixed an issue with columns in get_data where specifying a column with only sub columns would cause an Exception
* Added Type Hinting
* Added some docstrings
* Added a datatype

## Version 1.0.1
* Fixed a bug with columns in get_data
* Added support for UInt32
* Set a default sort option on queries as paginated queries were returning duplicates without it

<!-- ABOUT THE PROJECT -->
## About The Project



A  module for interacting with the Quickbase tables  via the API with an emphasis on
being easy to use. Everywhere the API calls for record or field IDs I have
changed it to work with values  or labels. Evolved from simple functions I wrote while getting started with python, has been useful for me, maybe you will find it useful as well.

<p align="right">(<a href="#top">back to top</a>)</p>





<!-- GETTING STARTED -->
## Getting Started


### Requirements
Older versions of below untested, below known to work.

Python (3.8+)

numpy (1.21.4+)

pandas (1.3.4+)

requests (2.26.0+)

lxml (4.6.4+)
   

### Installation

1: Can be installed using pip
```
pip install pyqbclient
```



<!-- USAGE EXAMPLES -->
## Usage
### set_default
Below we supply our realm and token as defaults for all subsequent Client
instantiation. Note that both realm_hostname and user_token can be supplied 
as arguments for the Client directly and that doing so will over-ride
any defaults set.  I have implemented some logging as well, so we will also configure that
```

import pyqbclient as pyqbc
import logging
logging.basicConfig(level = logging.INFO)


my_realm = 'example-realm.quickbase.com'
my_token = 'example_token_string'


pyqbc.set_default(realm_hostname=my_realm,user_token=my_token)

```

### Client
**Class pyqbclient.Client(**
        **table_id,**
        **realm_hostname=None,**
        **user_token=None,**
        **retries=3,**
        **dataframe=pd.DataFrame())**

#### Parameters:

#### table_id: *str*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**The Table ID you want to create a client for**

#### realm_hostname: *str*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Your quickbase realm hostname**

#### user_token: *str*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Your quickbase API user token**

#### retries: *int*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**The amount of retries desired for any given request**

#### dataframe: *pandas.DataFrame()*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**The DataFrame associated with the Client, empty DataFrame passed so the editor knows it is a DataFrame.**
\
Below we will instantiate our Client, relying on the defaults we set above
```
my_table_id = 'example_table_id'
my_table_client = pyqbc.Client(my_table_id)
```



### get_data
**pyqbclient.Client.get_data(report=None,columns=None,all_columns=False,**
**overwrite_df=True,return_copy=True,filter_list_dict=None,where=None,**
****kwargs)**

#### Parameters:

#### report: *str*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**The name of a report you wish to download, e.g "List All"**

#### columns: *list*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**A list of field labels corresponding to fields you wish to return, e.g ["Field1","Field2"]**

#### all_columns: *bool*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**When True returns all fields as well as any properties of attachment/built in fields (versions, userName etc.)**

#### overwrite_df: *bool*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Overwrites the Client's DataFrame**

#### return_copy: *bool*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Returns a copy of the Client's DataFrame**

#### filter_list_dict: *dict*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Query records based on a list of values. Takes a dictionary set up as below:**
     {
       'Field Label': ['Field_value_1','Field_value_2']
     }

#### where: *str*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Filter for queries using modified quickbase query language. Use the field label instead of the field ID, e.g. '{Record_ID#.EX.3}'**

#### \*\*kwargs: * (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Valid kwargs are  sortBy and groupBy,  consult documentation for utilization**

#### Returns: DataFrame 
\
Below we will get a DataFrame based on the fields and records available in the "List All" report 


```
df = my_table_client.get_data(report='List All')
```
\
Note: When called without any arguments returns default fields for all records\
\
_For more information on the quickbase query language, please refer to the [Documentation](https://help.quickbase.com/api-guide/componentsquery.html)_

_For more information on the query parameters, please refer to the [Documentation](https://developer.quickbase.com/operation/runQuery)_


### get_files
**pyqbclient.Client.get_files(file_field: str, where: str= None,**
**filter_list_dict: dict = None )**


#### Parameters:

#### file_field: *str*, 
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**The label of the field with the file you wish to download"**

#### where: *str*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Filter for queries using modified quickbase query language. Use the field label instead of the field ID, e.g. '{Record_ID#.EX.3}'**

#### filter_list_dict: *dict*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Query records based on a list of values. Takes a dictionary set up as below:**
     {
       'Field Label': ['Field_value_1','Field_value_2']
     }



#### Returns: Dict 
\
Function will return a dictionary with Field id 3 values as keys and base64 encoded files as values 


```
file_dict = my_table_client.get_files(filter_list_dict={'Record ID#': ['6225', '6224']})
```
\

\
_For more information on the quickbase query language, please refer to the [Documentation](https://help.quickbase.com/api-guide/componentsquery.html)_

_For more information on the query parameters, please refer to the [Documentation](https://developer.quickbase.com/operation/runQuery)_









### post_data
**pyqbclient.Client.post_data(external_df=None,step=5000, merge=None,**
**create_if_missing=False, exclude_columns=None, subset=None)**

#### Parameters:

#### external_df: *DataFrame*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**The DataFrame you wish to upload. Omitting uses the client's internal DataFrame**

#### step: *int*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**The amount of records to upload at a time. Quickbase has an upper limit of 10 MB per call, 5k has been pretty safe so far for my use.**

#### merge: *str*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**The label of the field you wish to merge on, must be a unique field. Updates where possible, creates where not.**


#### create_if_missing: *bool*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Create fields in table for any columns in the DataFrame that are not present in the table.**

#### exclude_columns: *list*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**A list of columns in your DataFrame you do not wish to be uploaded**

#### subset: *list*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**A list of columns in your DataFrame you wish to be uploaded while excluding all others (except merge if specified)**
 
#### Returns: dict
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Returns a dict with lists of created, updated and unchanged record ids as well as a count of processed records**

\
Will upload records to the table based on the DataFrame provided.

```
my_table_client.post_data(external_df=df)
```





### create_fields
**pyqbclient.Client.create_fields(field_dict=None,external_df=None,**
**ignore_errors=False, appearsByDefault=True)**

#### Parameters:

#### field_dict: *list or dict*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**A dict or list of dicts for field creation**

#### external_df: *dict*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Create columns based on a DataFrame**

#### ignore_errors: *bool*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Ignore errors in creation and continue**


#### appearsByDefault: *bool*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Whether or not this will be a default field**

#### Returns: list
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Returns a list with a dict for each field created**

Will create fields with the given arguments.

```
field_dict = {
  "label": "Field1",
  "fieldType": "text"
  }

my_table_client.create_fields(field_dict=field_dict)
```
_For more examples, please refer to the [Documentation](https://developer.quickbase.com/operation/createField)_

<p align="right">(<a href="#top">back to top</a>)</p>

### update_field
**pyqbclient.Client.update_field(field_label,field_dict = None,\*\*kwargs)**


#### Parameters:


#### field_label: *str*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**The label of the field to update**

#### field_dict: *dict*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**A dictionary for updating the field**

#### \*\*kwargs:  (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Accepts label, noWrap, bold, required, appearsByDefault, findEnabled, unique, fieldHelp, addToForms, properties**

#### Returns: dict
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Returns a dict with updated field characteristics**

Will update fields with the given arguments

```
my_table_client.update_field("Field1",unique=True)
```
_For more examples, please refer to the [Documentation](https://developer.quickbase.com/operation/createField)_





### delete_fields
**pyqbclient.Client.delete_fields(field_labels)**

#### Parameters:


#### field_labels: *list*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**A list of field labels corresponding to fields **

#### Returns: list
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Returns a list of deleted field ids**

Will delete the list of supplied fields

```
my_table_client.delete_fields(["Field1","Field2"])
```

### delete_records
**pyqbclient.Client.delete_records(where=None,all_records=False)**


#### Parameters:


#### where: *str*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Filter for deletion using modified quickbase query language. Use the field label instead of the field ID, e.g. '{Record_ID#.EX.3}'**


#### all_records: *bool*, (optional)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Delete all records from the table**

#### Returns: dict
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Returns a dict indicating the number of records deleted**

\
Will delete indicated records from the table
\
NOTE: One of where or all_records must be passed as an argument. Former default behaviour was to delete all records without an argument, thought it better to be explicit

```
my_table_client.delete_records(
  where='{Field1.EX."Some Value"}OR{Field1.EX."Some Other Value"}'
)
```


### upload_files
**pyqbclient.Client.upload_files(field_label, file_dict,
    merge_field,try_internal=True)**

#### Parameters:


#### field_label: *str*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**The label of the field we are uploading the file to**

#### file_dict: *dict*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; **A dictionary  setup as below:**
        {'*Filename with extension*':
         {
            'merge_value': '*The value you are merging on*',
            'file_str': '*Base64 encoded string of your file*'
         }
        }

#### merge_field: *str*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**The label of the field we are merging on**

#### try_internal: *bool*
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Whether or not we consult the Client's DataFrame for merge values.**

#### Returns: list
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;**Returns a list with a dict of record id and update id for each file uploaded**


\
Uploads files to the given file field based on a value in a unique field. 
When called, will create a dictionary using the supplied unique field 
and built in Record ID# to facilitate the upload. try_internal will attempt
to use the Client's DataFrame before resorting to downloading from the table.

\
Example usage below

```

picture_hash = base64.b64encode(picture_IObytes.read()).decode()


file_dict = {
    'pic.png': {
    'file_str': picture_hash,
    'merge_value': 49
    }
}

my_table_client.upload_files('Attachment',file_dict,merge_field='Field1')
```




<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Jeff MacDonald - jeffmacd@protonmail.com

Project Link: [https://github.com/jeffmacd/pyqbclient](https://github.com/jeffmacd/pyqbclient)

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

* Some XML functionality derived from https://github.com/pyQuickBase/pyQuickBase

<p align="right">(<a href="#top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/jeffmacd/pyqbclient.svg?style=flat
[contributors-url]: https://github.com/jeffmacd/pyqbclient/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/jeffmacd/pyqbclient.svg?style=flat
[forks-url]: https://github.com/jeffmacd/pyqbclient/network/members
[stars-shield]: https://img.shields.io/github/stars/jeffmacd/pyqbclient.svg?style=flat
[stars-url]: https://github.com/jeffmacd/pyqbclient/stargazers
[issues-shield]: https://img.shields.io/github/issues/jeffmacd/pyqbclient.svg?style=flat
[issues-url]: https://github.com/jeffmacd/pyqbclient/issues
[license-shield]: https://img.shields.io/badge/License-MIT-yellow.svg
[license-url]: https://github.com/jeffmacd/pyqbclient/blob/main/LICENSE
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=flat&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/in/jeff-macdonald-37202722a/
[product-screenshot]: images/screenshot.png
[downloads-shield]: https://pepy.tech/badge/pyqbclient
[downloads-url]: https://pepy.tech/project/pyqbclient
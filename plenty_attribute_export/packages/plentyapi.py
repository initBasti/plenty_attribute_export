"""
    Author: Sebastian Fricke (Panasiam)
    Date: 2020-07-30
    License: GPLv3

    Various calls to the PlentyMarkets API for ITEM data.
"""
import requests
import pandas
import simplejson

from plenty_attribute_export.packages.keyring import CredentialManager
from plenty_attribute_export.packages.progress import Progressbar

PROGRESS = Progressbar(size=80, prefix='Get Data..')

def get_request_plenty_api(route, url, headers):
    """ Simple wrapper to create a request route, get the response and
        parse it to JSON, if it is valid. """
    endpoint = url + route
    raw_response = requests.get(endpoint, headers=headers)
    try:
        response = raw_response.json()
    except simplejson.errors.JSONDecodeError:
        print(f'ERROR: No response for request: {route}')
        response = None
    return response

def get_attribute(data, dest, attribute_id):
    """
        Insert the attribute values for every required existing attribute
        append empty values for if it doesn't exist.
    """
    if not 'variationAttributeValues' in data.keys():
        dest += ['', '', '']
        return
    for attribute in data['variationAttributeValues']:
        if attribute['attributeId'] == attribute_id:
            dest += [attribute['attributeValue']['backendName'],
                     attribute['attributeValue']['id'], '']
            return
    dest += ['', '', '']

def for_each_entry_get_basic_data(entries, dest, config):
    """
        Move through the entries of the response (entries) and get the values,
        which are required by the data-set. Add these values to a list (dest)
        used for the creation of the pandas DataFrame.
    """
    for index, entry in enumerate(entries):
        PROGRESS.emit(index=index)
        if entry['isMain']:
            continue
        # Add 2 empty values for the SKUs by another GET request.
        variation = [entry['id'], entry['number'], '']
        for attr_id in config['PLENTY']['attribute_ids'].split(','):
            get_attribute(data=entry, dest=variation,
                          attribute_id=int(attr_id))
        variation += [entry['itemId']]
        dest.append(variation)

def get_market_parent_sku(response, config):
    """
        Get the parent SKU, used for the primary market specified in the
        configuration. In case a variation misses, that value use the
        alternative market.

        Parameter:
            response [Dict] : Response to variation_sku request

        Return:
            [String] : Parent SKU of the item / Not found
    """
    for entry in response:
        if str(entry['marketId']) == config['PLENTY']['primary_market_id']:
            if entry['parentSku']:
                return entry['parentSku']
        if str(entry['marketId']) == config['PLENTY']['alternative_market_id']:
            if entry['parentSku']:
                return entry['parentSku']
    return 'Not found'

def build_columns(attr, config):
    """
        Create the columns for the pandas DataFrame, depending on the
        number of atttributes chosen by the user.

        Parameter:
            attr [Dict] : Response to Attribute request

        Return:
            [List] : List of column names.
    """
    columns = ['variation-id', 'variation-number',
               'parent-variation']
    for entry in attr:
        if str(entry['id']) in config['PLENTY']['attribute_ids'].split(','):
            columns.append(str(f"{entry['name']}_name"))
            columns.append(str(f"{entry['name']}_id"))
            columns.append(str(f"{entry['name']}_lang"))
    columns.append('item-id')
    return columns

def get_route(scope):
    """
        Build the route for the different variation GET requests.
        Depending on the chosen option, apply the specified
        item_id or variation_id values.

        Parameter:
            scope [Dict] : User defined parameter from the CLI

        Return:
            [String] : Part of the HTTP request after the base URL.
    """
    if scope['name'] == 'all':
        route = '/rest/items/variations'
    elif scope['name'] == 'item':
        route = str(f"/rest/items/{scope['args']['item']}/variations")
    elif scope['name'] == 'variation':
        route = str("/rest/items/{0}/variations/{1}".format(
            scope['args']['item'], scope['args']['variation']))
    return route + "?with=variationAttributeValues"

def plenty_api_login(url):
    """
        Get the bearer token with the credentials saved in the data file.

        Parameter:
            url [String] : Base URL of the shop provided by the config
    """

    keyring = CredentialManager()
    creds = keyring.get_credentials()
    if not creds:
        keyring.set_credentials()
        creds = keyring.get_credentials()
    endpoint = url + '/rest/login'
    request = requests.post(endpoint, params=creds)
    token = request.json()['token_type'] + ' ' + request.json()['access_token']
    return {'Authorization': token}

def plenty_api_get_variations(url, headers, config, scope):
    """
        Get the attribute ID and backend name from plentymarkets
        with incremental data from the API.

        Parameter:
            url [String]    : Base URL of the shop provided by the config
            headers [Dict]  : HTTP header for the GET request
                              (has to contain atleast authorization)
            config [Dict]   : Config mapping of values used in
                              the plentymarkets client
            scope [Dict]    : User defined options about the breadth of the
                              data pull.
                              (name: {all, item, variation}),
                              (args: {item, variation})
    """
    variation_list = []
    columns = []

    route = get_route(scope=scope)
    response = get_request_plenty_api(route=route, url=url, headers=headers)
    attributes = plenty_api_get_attribute_ids(url=url, headers=headers)
    columns = build_columns(attr=attributes, config=config)

    if not 'totalsCount' in response.keys():
        # adjust the response of a single variation GET request
        # in order to compute properly with the functions
        response = {'entries':[response], 'lastPageNumber':1, 'page':1}
        PROGRESS.count = 1
    else:
        PROGRESS.count = response['totalsCount']

    for_each_entry_get_basic_data(entries=response['entries'],
                                  dest=variation_list, config=config)
    if response['lastPageNumber'] != response['page']:
        loop_range = range(2, response['lastPageNumber'])
        for page_num in loop_range:
            route = route + str(f'&page={page_num}')
            response = get_request_plenty_api(
                route=route, url=url, headers=headers)
            if not response:
                continue
            for_each_entry_get_basic_data(entries=response['entries'],
                                          dest=variation_list, config=config)
    frame = pandas.DataFrame(variation_list, columns=columns)
    return frame

def plenty_api_get_market_sku(url, headers, item, variation_id, config):
    """
        Get all market SKUs from Plentymarkets for a specific variation.
        Choose the one specified in the config as primary and return the
        parent SKU.

        Parameter:
            url [String]    : Base URL of the shop provided by the config
            headers [Dict]  : HTTP header for the GET request
                              (has to contain atleast authorization)
            config [Dict]   : Config mapping of values used in
                              the plentymarkets client

        Return:
            [String] : Parent SKU used in the item.
    """
    route = str(f'/rest/items/{item}/variations/{variation_id}/variation_skus')
    endpoint = url + route
    raw_response = requests.get(endpoint, headers=headers)
    response = raw_response.json()
    return get_market_parent_sku(response=response, config=config)

def plenty_api_get_childs_for_item(url, headers, item):
    """
        Get a list of children, that are bounded to a specific parent.

        Parameter:
            url [String]    : Base URL of the shop provided by the config
            headers [Dict]  : HTTP header for the GET request
            item [String]   : ID of the item (PlentyMarkets)

        Return:
            [List]
    """
    childs = []
    route = str(f'/rest/items/{item}/variations')
    endpoint = url + route
    raw_response = requests.get(endpoint, headers=headers)
    try:
        response = raw_response.json()
    except simplejson.errors.JSONDecodeError:
        print(f'''ERROR: No response for request:
              get child variation ids for ItemId: {item}''')
        return childs

    for entry in response['entries']:
        if not entry['isMain']:
            childs.append(entry['id'])
    return childs

def plenty_api_get_attribute_value_for_language(url, headers, value_id,
                                                lang, signal):
    if not value_id:
        return ''
    route = str(f'/rest/items/attribute_values/{value_id}/names/{lang}')
    endpoint = url + route
    signal.emit_increment()
    raw_response = requests.get(endpoint, headers=headers)
    try:
        response = raw_response.json()
    except simplejson.errors.JSONDecodeError:
        print(f'''ERROR: No response for request:
              get value name for attributeValue: {value_id} in language: {lang}
              ''')
        return 'Not found'

    if not 'name' in response:
        return 'Not found'
    return response['name']

def plenty_api_get_attribute_ids(url, headers):
    attributes = []
    response = get_request_plenty_api(route='/rest/items/attributes', url=url,
                                      headers=headers)
    if not response:
        return []

    for attribute in response['entries']:
        attributes.append({'name':attribute['backendName'],
                           'id': attribute['id']})

    return attributes

def plenty_api_get_itemid_for_variation(url, headers, variation):
    route = str(f'/rest/items/variations?id={variation}')
    response = get_request_plenty_api(route=route, url=url,
                                      headers=headers)
    if not response:
        return 0
    if response['entries']:
        return response['entries'][0]['itemId']
    return 0

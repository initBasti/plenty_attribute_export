"""
    Author: Sebastian Fricke (Panasiam)
    Date: 2020-07-30
    License: GPLv3

    The purpose of this script is to fix a short coming of the
    plentymarkets UI.
    In the current article tab (state:07-2020), it is not possible to
    find the matched attribute ID or the attribute translations.
    Especially, when performing translations it is quite useful to
    quickly get the correct value.

    Provide 3 different scopes:
        - all (literally every variation)
        - item (All variations of a single item)
        - variation
"""
import sys
import os
import configparser
import argparse
import datetime
import tabulate
import easygui

import plenty_attribute_export.packages.plentyapi as pa
import plenty_attribute_export.packages.progress as pro

if sys.platform == 'linux':
    linux_user = os.getlogin()
    CONFIG_FILE = os.path.join('/', 'home', str(f'{linux_user}'),
                               '.plenty_export_config.ini')
elif sys.platform == 'win32':
    win_user = os.getlogin()
    CONFIG_FILE = os.path.join('C:', 'Users', str(f'{win_user}'),
                               '.plenty_export_config.ini')

def create_argparser():
    """ Set up the argument parser, with the different arguments
        and check if dependencies of some commands are fulfilled. """
    argparser = argparse.ArgumentParser(
        description='Pull identity defining data for Plentymarkets items.')
    argparser.add_argument(
        '-s', '--scope', default='all',
        choices=['all', 'item', 'variation'],
        help='Pull all variations/A whole item/single variation',
        dest='scope_name')
    argparser.add_argument(
        '-i', '--item', default=0,
        help='Item ID for the scope = item option',
        dest='scope_item')
    argparser.add_argument(
        '-v', '--var', default=0,
        help='Variation ID for the scope = variaion option',
        dest='scope_variation')
    argparser.add_argument(
        '-l', '--lang', default='en',
        choices=['en', 'fr', 'it', 'es'],
        help='Language to be exported from PlentyMarkets',
        dest='lang')
    argparser.add_argument(
        '-o', '--stdout', action='store_true',
        help='Do not print to a file but to the console instead',
        dest='stdout')
    argparser.add_argument(
        '-c', '--config', action='store_true',
        help='Change elements of the configuration',
        dest='configuration')
    namespace = argparser.parse_args()
    if namespace.scope_name == 'item' and not namespace.scope_item:
        print("ERROR: The scope=item option requires: [-i/--item].")
    elif namespace.scope_name == 'variation' and not namespace.scope_variation:
        print("ERROR: The scope=variation option requires: [-v/--var].")

    if namespace.scope_name == 'all':
        scope = {'name':'all',
                 'args':{'item':'', 'variation': ''}}
    elif namespace.scope_name == 'item':
        scope = {'name':'item',
                 'args':{'item':namespace.scope_item, 'variation': ''}}
    elif namespace.scope_name == 'variation':
        scope = {'name':'variation',
                 'args':{'item':'', 'variation': namespace.scope_variation}}

    return {'scope':scope, 'namespace':namespace}

def get_item_set(data):
    """ Get a dictionary of every unique item id within the variation frame """
    unique_item_ids = data['item-id'].unique()
    return {str(key):None for key in unique_item_ids}

def get_parent_sku_for_item(url, headers, item, config):
    """ Get a random variation ID, which is present in the specified item.
        Then go on to get the parent SKU value, within primary/alternative
        market for that item. (The IDs for those markets are set in the config)
    """
    childs = pa.plenty_api_get_childs_for_item(
        url=url, headers=headers, item=item)
    parent_sku = pa.plenty_api_get_market_sku(
        url=url, headers=headers, item=item, variation_id=childs[0],
        config=config)
    return parent_sku

def get_parent_sku(url, headers, config, data):
    """
        Reduce the total amount of API GET requests by acquiring a
        set of unique item IDs and map parent SKUs to each.

        Parameter:
            url [String]    : Base URL of the shop provided by the config
            headers [Dict]  : HTTP header for the GET request
                              (has to contain atleast authorization)
            config [Dict]   : Config mapping of values used in
                              the plentymarkets client
            data [DataFrame]: pandas DataFrame of the variations.
    """
    item_ids = get_item_set(data=data)
    for key in item_ids.keys():
        parent_sku = get_parent_sku_for_item(url=url, headers=headers,
                                             item=int(key), config=config)
        item_ids[str(key)] = parent_sku
    data['parent-variation'] = data['item-id'].apply(
        lambda x: item_ids[str(x)])

def setup_config(path):
    """
        Run this, if the user has not pre-configured the required
        ID values for the attributes and the markets.

        Parameter:
            path [String] : Path to the configuration file.
    """
    config = configparser.ConfigParser()
    url = input('Base PlentyMarkets URL (Setup->API)')
    primary_market = input('ID of the primary market (amazon DE)')
    alt_market = input('ID of the secondary market')
    config['PLENTY'] = {
        'url':url,
        'attribute_ids' : '',
        'primary_market_id' : primary_market,
        'alternative_market_id' : alt_market
    }
    with open(path, mode='w') as configfile:
        config.write(configfile)

def edit_config(path):
    if sys.platform == 'linux':
        os.system(str(f'vim {path}'))
    elif sys.platform == 'win32':
        os.system(str(f'notepad {path}'))

def get_attribute_ids(config, headers):
    """
        Let the user choose, which attributes to include into the dataset.
        These can also be chosen within the config file.

        Parameter:
            config [Config object]
            headers [Dict] : HTTP headers used for the plenty API request.

        Return:
            [Dict] : Raw response data from the get attribute IDs request.
    """
    attributes = pa.plenty_api_get_attribute_ids(
        url=config['PLENTY']['url'], headers=headers)
    if not attributes:
        print(f"ERROR: No attribute IDs found")

    if not config['PLENTY']['attribute_ids']:
        print("Found the following plenty attributes, choose by letter:")
        for index, attribute in enumerate(attributes):
            print("({0}). {1} - ID: {2}"
                  .format(chr(ord('a')+index), attribute['name'],
                          attribute['id']))
        choice = input('>> ')
        config['PLENTY']['attribute_ids'] = ''
        for index, letter in enumerate(choice):
            config['PLENTY']['attribute_ids'] +=\
                str(attributes[ord(letter) - ord('a')]['id'])
            if index < len(choice) -1:
                config['PLENTY']['attribute_ids'] += ','
        with open(CONFIG_FILE, mode='w') as configfile:
            config.write(configfile)
    return attributes

def build_output_name(name):
    """ Create the file path for the CSV creation """
    while True:
        path = easygui.diropenbox()
        if not path:
            print('\nNo folder provided, exit? (y/n)')
            while True:
                choice = input('>> ')
                if choice.lower() == 'y' or choice.lower() == 'n':
                    break
            if choice == 'y':
                sys.exit(0)
        else:
            break
    date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
    filetype = '.csv'
    name = date + '_' + name + filetype
    return os.path.join(os.getcwd(), name)

def cli():
    """
        Load the argument and configuration data.
        Make the appropriate requests to fill the data set.
        And the print it to a file or stdout.
    """
    argparser = create_argparser()

    if not os.path.exists(CONFIG_FILE):
        setup_config(path=CONFIG_FILE)
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    url = config['PLENTY']['url']

    headers = pa.plenty_api_login(url=url)
    if not headers:
        sys.exit(1)

    if argparser['namespace'].configuration:
        if not edit_config(path=CONFIG_FILE):
            sys.exit(1)
        sys.exit(0)
    if argparser['scope']['name'] == 'variation':
        item = pa.plenty_api_get_itemid_for_variation(
            url=url, headers=headers,
            variation=argparser['scope']['args']['variation'])
        if not item:
            print("ERROR: No ItemID found for variation: {0}"
                  .format(argparser['scope']['args']['variation']))
            sys.exit(1)
        argparser['scope']['args']['item'] = item
    raw_attributes = get_attribute_ids(config=config, headers=headers)
    attribute_ids = config['PLENTY']['attribute_ids'].split(',')

    frame = pa.plenty_api_get_variations(
        url=url, headers=headers, config=config, scope=argparser['scope'])
    get_parent_sku(url=url, headers=headers,
                   config=config, data=frame)
    progress = pro.Progressbar(size=80, prefix='Get Translation..')

    for attribute in raw_attributes:
        if str(attribute['id']) in attribute_ids:
            progress.prefix = str(f"Get {attribute['name']} translation")
            progress.count =\
                len(frame[frame[attribute['name'] + '_name'] != ''].values)
            frame[attribute['name'] + '_lang'] =\
                frame[attribute['name'] + '_id'].apply(
                    lambda x: pa.plenty_api_get_attribute_value_for_language(
                        url=url, headers=headers, value_id=x,
                        lang=argparser['namespace'].lang,
                        signal=progress))

    if not argparser['namespace'].stdout or argparser['scope']['name'] == 'all':
        try:
            output_path = build_output_name(
                name=str(f"Attribute_{argparser['scope']['name']}"))
        except Exception as err:
            print(f"ERROR: couldn't build output name => {err}")
            output_path = easygui.filesavebox()
        frame.to_csv(output_path, sep=';', index=False)
    elif argparser['namespace'].stdout:
        print(tabulate.tabulate(frame, headers='keys', tablefmt='fancygrid',
                                showindex=False))

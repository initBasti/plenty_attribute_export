# plenty attribute export

## Description:  

This application was created for a specific use-case (but may be used in other circumstances):

The current version of PlentyMarkets (stable 2020-07-31) does not provide a simple way for the user to have an easy access to the exact attribute data for a variation.
Currently one has to look at the variation to find the attribute name (example: color_name: black), then go to setup -> item -> attributes -> go into the `color_name` attribute
and then search for the specific name, in order to get the following information: value id, value_name in another language.

These two pieces of information are quite valuable, if you try to create translations for a product on amazon. As it makes it easier to deny collisons of multiple translation values, that are supposed to point to the same backend attribute.

## Installation:  

In order to use this application you require the following pypi packages:

- pandas
- tabulate
- configparser
- argparse
- simplejson
- requests
- keyring
- signalslot
- easygui

These are either installed automatically, when you are installing via:  
`python3 -m pip install plenty_attribute_export --user --upgrade`

Or you have to install them, manually when you are doing the setup yourself:

    python3 -m pip install pandas tabulate configparser\
                           argparse simplejson requests\
                           keyring getpass signalslot easygui --user --upgrade`

Afterwards, you have to configure the tool to work properly with your plentymarkets system:

1. Create a user in PlentyMarkets with `REST-API` access (Setup -> settings -> User -> accounts)
2. Get the REST-API HTTP endpoint url (Setup -> settings -> API -> data)
3. Find the id of the market, which you want to use as data source for the parent_sku of each variation (Setup -> orders -> order-origin)

When you want to start the application for the first time:
You will be asked for the username of the newly created user, as well as it's password. This data will be saved into your system keyring.
The application will save your input of the base url (= REST-API HTTP enpoint url) and the primary + alternative market ID into a configuration.

## Usage:  

The usage is quite simple:  

Download all english atttribute values for every variation:  
`plenty_attribute_export --scope all --lang en` or  
`plenty_attribute_export -s all` (as english is the default)  

Download every french attribute value for a single item:  
`plenty_attribute_export --scope item --item 123456 --lang fr`

Download every italian attribute value for a single variation and print to screen:  
`plenty_attribute_export --scope variation --var 3456 --lang it --stdout`

_________________

[Read Latest Documentation](https://initBasti.github.io/plenty_attribute_export/) - [Browse GitHub Code Repository](https://github.com/initBasti/plenty_attribute_export/)

Contact: sebastian.fricke@panasiam.de

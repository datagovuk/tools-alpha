'''
Generates the location data for the data.gov.uk alpha.

'''
import argparse
import json
import traceback
import csv
from pprint import pprint

import requests
import requests_cache

from running_stats import Stats

stats_types = Stats()
stats = Stats()
args = None
max_pk = None

one_day = 60 * 60 * 24
requests_cache.install_cache('.drupal_dump', expire_after=one_day)

# Is there a register? Probably easier to hard-code
countries_of_the_uk = [
    ('England', ),  # leave room for geo-data
    ('Wales', ),
    ('Scotland', ),
    ('Northern Ireland', ),
    ]
regions_of_the_uk = [
    ('Great Britain', ),
    ('British Isles', ),
    ]

# http://register.alpha.openregister.org/record/local-authority-eng

def publish_data():
    '''
    Produces the location.json for publish_data form

    e.g. {"model":"datasets.location",
          "pk":0,
          "fields":{"name":"England"
                    "location_type":"country"}}
    '''
    try:
        locations = []

        # countries
        for country_tuple in countries_of_the_uk:
            name = country_tuple[0]
            locations.append(location_dict(name, 'country'))
            stats_types.add('Country added ok', name)
        for region_tuple in regions_of_the_uk:
            name = region_tuple[0]
            locations.append(location_dict(name, 'region of the UK'))
            stats_types.add('Region of the UK added ok', name)
        locations.append(location_dict('United Kingdom', 'UK'))
        stats_types.add('United Kingdom added ok', 'United Kingdom')


        # local authorities
        # The "name" field is the place
        la_eng = requests.get('https://local-authority-eng.register.gov.uk/records.json?page-size=5000').json()
        la_nir = requests.get('https://local-authority-nir.discovery.openregister.org/records.json?page-size=5000').json()
        la_wls = requests.get('https://local-authority-wls.discovery.openregister.org/records.json?page-size=5000').json()
        la_sct = requests.get('https://local-authority-sct.discovery.openregister.org/records.json?page-size=5000').json()
        # "STA": {
        #     "entry-number": "331",
        #     "entry-timestamp": "2016-10-21T16:11:20Z",
        #     "item-hash": "sha-256:0e6d3a5790abf0248d74e9e6cdacc422dea9f871f65587e62e6d3dca6964a344",
        #     "local-authority-type": "NMD",
        #     "official-name": "Stafford Borough Council",
        #     "local-authority-eng": "STA",
        #     "name": "Stafford"
        #   },
        try:
            def add_local_authorities(locations, la_dict, country):
                for la in la_dict.values():
                    name = la['name']
                    locations.append(dict(
                        model='datasets.location',
                        fields=dict(
                            name=name,
                            location_type='local authority'
                            )
                        )
                    )
                    stats_types.add('LA %s added ok' % country, name)
            add_local_authorities(locations, la_eng, 'eng')
            add_local_authorities(locations, la_nir, 'nir')
            add_local_authorities(locations, la_wls, 'wls')
            add_local_authorities(locations, la_sct, 'sct')
        except Exception:
            traceback.print_exc()
            import pdb; pdb.set_trace()

        # Clinical Commissioning Groups
        # Clinical Commissioning Groups (April 2016) Ultra Generalised Clipped Boundaries in England
        url = 'http://geoportal.statistics.gov.uk/datasets/1bc1e6a77cdd4b3a9a0458b64af1ade4_4'
        # objectid    ccg16cd ccg16nm st_areashape    st_lengthshape
        # 1   E38000001   NHS Airedale, Wharfedale and Craven CCG 1224636590  193149.7401
        def ccg_name_processor(name):
            assert name.startswith('NHS '), name
            assert name.endswith(' CCG'), name
            return name[4:-4]
        add_ons_data(url, 'ccg16cd', 'ccg16nm',
                     'NHS Clinical Commissioning Group area', locations,
                     name_processor=ccg_name_processor)

        # fill in 'pk' - keys
        existing_locations = []
        if args.existing_locations:
            with open(args.existing_locations, 'r', encoding='utf8') as f:
                existing_locations = json.load(f)
        global max_pk
        max_pk = max((l['pk'] for l in existing_locations)
                     if existing_locations else [0])

        add_keys_from_existing_data(locations, location_type='country',
                                    existing_locations=existing_locations)

        # write
        print('\nLocations:\n', stats_types)
        print('\nStats:\n', stats)
        with open(args.output_fpath, 'w', encoding='utf8') as output_f:
            json.dump(locations, output_f, ensure_ascii=False)
        print('Written %s' % args.output_fpath)

    except Exception:
        traceback.print_exc()
        import pdb; pdb.set_trace()

def add_keys_from_existing_data(locations, location_type, existing_locations):
    existing_keys_by_name = dict(
        (l['fields']['name'], l['pk'])
        for l in existing_locations
        if l['fields']['location_type'] == location_type)
    for location in locations:
        name = location['fields']['name']
        if name in existing_keys_by_name:
            location['pk'] = existing_keys_by_name[name]
            stats.add('Key reused', name)
        else:
            location['pk'] = get_new_pk(locations, existing_locations)
            stats.add('Key new', name)

def location_dict(name, location_type):
    return dict(
        model='datasets.location',
        fields=dict(
            name=name,
            location_type=location_type
            )
        )
def get_new_pk(locations, existing_locations):
    global max_pk
    max_pk += 1
    return max_pk

ons_codes_added = set()

def add_ons_data(page_url, column_with_code, column_with_name,
                 location_type, locations, name_processor=None):
    global ons_codes_added
    response = requests.get(page_url + '.csv')
    content = response.content
    # need to get rid of the bom which is first 3 bytes
    if content[:3] == b'\xef\xbb\xbf':
        content = content[3:]
    decoded_content = content.decode('utf8')
    csv_data = csv.DictReader(decoded_content.splitlines())
    for row in csv_data:
        code = row[column_with_code]
        name = row[column_with_name]
        if name_processor:
            name = name_processor(name)
        if code in ons_codes_added:
            stats.add('ONS place already added. Ignore %s dupe' %
                      location_type, name)
            continue
        ons_codes_added.add(code)
        locations.append(location_dict(name, location_type))
        stats_types.add('%s added ok' % location_type, name)

def administrative_areas():
    # administrative areas
    # Provided by ONS Geography http://geoportal.statistics.gov.uk/
    # under menus: Boundaries | Administrative Boundaries |
    # We want:
    #  * 'generalised resolution' - no need for full detail for searching
    #  * 'clipped to the coastline' - better to look good on a map than be
    #    perfectly accurate, when its only for searching anyway.
    # i.e. Generalised Clipped
    # We can start with CSVs and go to KMLs later when we need the outlines
    # License is OGL, with attribution:
    # Contains National Statistics data (c) Crown copyright and database right [year]
    # Contains OS data (c) Crown copyright and database right [year]

    # Combined Authorities - yes
    # Combined Authorities (June 2016) Ultra Generalised Clipped Boundaries in England
    url = 'http://geoportal.statistics.gov.uk/datasets/0293170f45ac4322868978b46dba822d_4'
    # objectid    cauth16cd   cauth16nm   st_areashape    st_lengthshape
    # 1   E47000001   Greater Manchester  1273598354  206057.3684
    add_ons_data(url, 'cauth16cd', 'cauth16nm', 'combined authority')

    # Local Authority Districts - yes
    # Local Authority Districts (December 2015) Ultra Generalised Clipped Boundaries in Great Britain
    url = 'http://geoportal.statistics.gov.uk/datasets/8edafbe3276d4b56aec60991cbddda50_4'
    # lad15cd lad15nm lad15nmw    objectid    st_lengthshape  st_areashape
    # E06000001   Hartlepool      1   50790.07333 96334979.59
    add_ons_data(url, 'lad15cd', 'lad15nm', 'district')

    # Counties - yes
    # Counties (December 2015) Ultra Generalised Clipped Boundaries in England
    url = 'http://geoportal.statistics.gov.uk/datasets/97e17cbdddcb4c98b960d41104ef02e9_4'
    # objectid    cty15cd cty15nm st_areashape    st_lengthshape
    # 1   E10000002   Buckinghamshire 1572148102  303282.187
    add_ons_data(url, 'cty15cd', 'cty15nm', 'county')

    # Counties and UAs - yes but some overlap with previous
    # Counties and Unitary Authorities (December 2015) Ultra Generalised Clipped Boundaries in England and Wales
    # "counties, metropolitan districts, London boroughs and unitary authorities in England and Wales"
    url = 'http://geoportal.statistics.gov.uk/datasets/0b09996863af4b5db78058225bac5d1b_4'
    # ctyua15cd   ctyua15nm   ctyua15nmw  objectid    st_lengthshape  st_areashape
    # E06000001   Hartlepool      1   50778.094   96339578.63
    add_ons_data(url, 'ctyua15cd', 'ctyua15nm', 'local authority area')

    # Countries - no - only has 3 anyway

    # Parishes - no - 11,000 of them
    # Parishes (December 2016) Generalised Clipped Boundaries in England and Wales
    url = 'http://geoportal.statistics.gov.uk/datasets/f13dad37854b4a1f869bf178489ff99a_2'

    # Parishes and non-civil areas - no - almost the same as parishes

    # Regions - no

    # Upper tier LAs - lots of overlap but has London
    # Upper Tier Local Authorities (December 2011) Boundaries
    # Upper Tier Local Authorities in England and Wales as at 31 December 2011
    url = 'http://geoportal.statistics.gov.uk/datasets/22264fcec9df4a7fafa56724ce14ad14_0'
    # objectid    utla11cd    utla11nm    st_areashape    st_lengthshape
    # 1   E06000001   Hartlepool  93886294.32 69010.01461
    add_ons_data(url, 'utla11cd', 'utla11nm', 'local authority')

    # Wards / Electoral Divisions - no

    # Ones that dont match the name in the England register:
    # ['Greater London', 'Kings Lynn and West Norfolk', 'City of Lincoln', 'Herefordshire', 'Kingston upon Hull', 'City of Bristol']
    location_names = [l['fields']['name'] for l in locations]
    la_eng = requests.get('https://local-authority-eng.register.gov.uk/records.json?page-size=5000').json()
    for la in la_eng.values():
        if la['name'] not in location_names:
            stats.add('non matching name', la['name'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers()

    subparser = subparsers.add_parser('publish_data')
    subparser.set_defaults(func=publish_data)
    subparser.add_argument(
        '--output_fpath',
        default='locations.json',
        help='Location of the output locations.json, that is destined for: '
        'src/datasets/fixtures/locations.json')
    subparser.add_argument(
        '--existing-locations',
        help='Filepath to existing locations.json, so that keys can be kept '
        'the same')
    # subparser.add_argument('--users-from-drupal-user-table-dump',
    #                        help='Filepath of drupal_users_table.csv.gz')
    # subparser.add_argument('--users-tried-sequentially',
    #                        action='store_true',
    #                        help='Rather than try a given list of user ids, '
    #                             'just try all ids in order from 1 to 500000.')
    # subparser.add_argument('-u', '--user',
    #                        help='Only do it for a single user (eg 845)')
    args = parser.parse_args()

    # if args.cache_requests:
    #     requests_cache.install_cache('.drupal_dump')  # doesn't expire

    # call the function
    args.func()
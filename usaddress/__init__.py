#!python3
"""
Tag an address string into word parts
"""

from functools import lru_cache
import os
import string
import re
from collections import OrderedDict
from typing import Any, Dict, Hashable, List, Optional, Tuple, Union, cast
import warnings
from sklearn_crfsuite.estimator import CRF
import probableparsing
from typing_extensions import Final

# The address components are based upon the `United States Thoroughfare,
# Landmark, and Postal Address Data Standard
# http://www.urisa.org/advocacy/united-states-thoroughfare-landmark-and-postal-address-data-standard

LABELS:Final = [
    'AddressNumberPrefix',
    'AddressNumber',
    'AddressNumberSuffix',
    'StreetNamePreModifier',
    'StreetNamePreDirectional',
    'StreetNamePreType',
    'StreetName',
    'StreetNamePostType',
    'StreetNamePostDirectional',
    'SubaddressType',
    'SubaddressIdentifier',
    'BuildingName',
    'OccupancyType',
    'OccupancyIdentifier',
    'CornerOf',
    'LandmarkName',
    'PlaceName',
    'StateName',
    'ZipCode',
    'USPSBoxType',
    'USPSBoxID',
    'USPSBoxGroupType',
    'USPSBoxGroupID',
    'IntersectionSeparator',
    'Recipient',
    'NotAddress',
]

PARENT_LABEL:Final = 'AddressString'
GROUP_LABEL:Final = 'AddressCollection'

MODEL_FILE:Final = 'usaddr.crfsuite'
MODEL_PATH:Final = os.path.join(os.path.split(os.path.abspath(__file__))[0], MODEL_FILE)

DIRECTIONS:Final = frozenset(['n', 's', 'e', 'w',
                    'ne', 'nw', 'se', 'sw',
                    'north', 'south', 'east', 'west',
                    'northeast', 'northwest', 'southeast', 'southwest'])

# cSpell: disable
STREET_NAMES:Final = frozenset({
    'allee', 'alley', 'ally', 'aly', 'anex', 'annex', 'annx', 'anx', 'arc',
    'arcade', 'av', 'ave', 'aven', 'avenu', 'avenue', 'avn', 'avnue', 'bayoo',
    'bayou', 'bch', 'beach', 'bend', 'bg', 'bgs', 'blf', 'blfs', 'bluf',
    'bluff', 'bluffs', 'blvd', 'bnd', 'bot', 'bottm', 'bottom', 'boul',
    'boulevard', 'boulv', 'br', 'branch', 'brdge', 'brg', 'bridge', 'brk',
    'brks', 'brnch', 'brook', 'brooks', 'btm', 'burg', 'burgs', 'byp', 'bypa',
    'bypas', 'bypass', 'byps', 'byu', 'camp', 'canyn', 'canyon', 'cape',
    'causeway', 'causwa', 'cen', 'cent', 'center', 'centers', 'centr',
    'centre', 'cir', 'circ', 'circl', 'circle', 'circles', 'cirs', 'clb',
    'clf', 'clfs', 'cliff', 'cliffs', 'club', 'cmn', 'cmns', 'cmp', 'cnter',
    'cntr', 'cnyn', 'common', 'commons', 'cor', 'corner', 'corners', 'cors',
    'course', 'court', 'courts', 'cove', 'coves', 'cp', 'cpe', 'crcl', 'crcle',
    'creek', 'cres', 'crescent', 'crest', 'crk', 'crossing', 'crossroad',
    'crossroads', 'crse', 'crsent', 'crsnt', 'crssng', 'crst', 'cswy', 'ct',
    'ctr', 'ctrs', 'cts', 'curv', 'curve', 'cv', 'cvs', 'cyn', 'dale', 'dam',
    'div', 'divide', 'dl', 'dm', 'dr', 'driv', 'drive', 'drives', 'drs', 'drv',
    'dv', 'dvd', 'est', 'estate', 'estates', 'ests', 'exp', 'expr', 'express',
    'expressway', 'expw', 'expy', 'ext', 'extension', 'extensions', 'extn',
    'extnsn', 'exts', 'fall', 'falls', 'ferry', 'field', 'fields', 'flat',
    'flats', 'fld', 'flds', 'fls', 'flt', 'flts', 'ford', 'fords', 'forest',
    'forests', 'forg', 'forge', 'forges', 'fork', 'forks', 'fort', 'frd',
    'frds', 'freeway', 'freewy', 'frg', 'frgs', 'frk', 'frks', 'frry', 'frst',
    'frt', 'frway', 'frwy', 'fry', 'ft', 'fwy', 'garden', 'gardens', 'gardn',
    'gateway', 'gatewy', 'gatway', 'gdn', 'gdns', 'glen', 'glens', 'gln',
    'glns', 'grden', 'grdn', 'grdns', 'green', 'greens', 'grn', 'grns', 'grov',
    'grove', 'groves', 'grv', 'grvs', 'gtway', 'gtwy', 'harb', 'harbor',
    'harbors', 'harbr', 'haven', 'hbr', 'hbrs', 'heights', 'highway', 'highwy',
    'hill', 'hills', 'hiway', 'hiwy', 'hl', 'hllw', 'hls', 'hollow', 'hollows',
    'holw', 'holws', 'hrbor', 'ht', 'hts', 'hvn', 'hway', 'hwy', 'inlet',
    'inlt', 'is', 'island', 'islands', 'isle', 'isles', 'islnd', 'islnds',
    'iss', 'jct', 'jction', 'jctn', 'jctns', 'jcts', 'junction', 'junctions',
    'junctn', 'juncton', 'key', 'keys', 'knl', 'knls', 'knol', 'knoll',
    'knolls', 'ky', 'kys', 'lake', 'lakes', 'land', 'landing', 'lane', 'lck',
    'lcks', 'ldg', 'ldge', 'lf', 'lgt', 'lgts', 'light', 'lights', 'lk', 'lks',
    'ln', 'lndg', 'lndng', 'loaf', 'lock', 'locks', 'lodg', 'lodge', 'loop',
    'loops', 'mall', 'manor', 'manors', 'mdw', 'mdws', 'meadow', 'meadows',
    'medows', 'mews', 'mill', 'mills', 'mission', 'missn', 'ml', 'mls', 'mnr',
    'mnrs', 'mnt', 'mntain', 'mntn', 'mntns', 'motorway', 'mount', 'mountain',
    'mountains', 'mountin', 'msn', 'mssn', 'mt', 'mtin', 'mtn', 'mtns', 'mtwy',
    'nck', 'neck', 'opas', 'orch', 'orchard', 'orchrd', 'oval', 'overpass',
    'ovl', 'park', 'parks', 'parkway', 'parkways', 'parkwy', 'pass', 'passage',
    'path', 'paths', 'pike', 'pikes', 'pine', 'pines', 'pkway', 'pkwy',
    'pkwys', 'pky', 'pl', 'place', 'plain', 'plains', 'plaza', 'pln', 'plns',
    'plz', 'plza', 'pne', 'pnes', 'point', 'points', 'port', 'ports', 'pr',
    'prairie', 'prk', 'prr', 'prt', 'prts', 'psge', 'pt', 'pts', 'rad',
    'radial', 'radiel', 'radl', 'ramp', 'ranch', 'ranches', 'rapid', 'rapids',
    'rd', 'rdg', 'rdge', 'rdgs', 'rds', 'rest', 'ridge', 'ridges', 'riv',
    'river', 'rivr', 'rnch', 'rnchs', 'road', 'roads', 'route', 'row', 'rpd',
    'rpds', 'rst', 'rte', 'rue', 'run', 'rvr', 'shl', 'shls', 'shoal',
    'shoals', 'shoar', 'shoars', 'shore', 'shores', 'shr', 'shrs', 'skwy',
    'skyway', 'smt', 'spg', 'spgs', 'spng', 'spngs', 'spring', 'springs',
    'sprng', 'sprngs', 'spur', 'spurs', 'sq', 'sqr', 'sqre', 'sqrs', 'sqs',
    'squ', 'square', 'squares', 'st', 'sta', 'station', 'statn', 'stn', 'str',
    'stra', 'strav', 'straven', 'stravenue', 'stravn', 'stream', 'street',
    'streets', 'streme', 'strm', 'strt', 'strvn', 'strvnue', 'sts', 'sumit',
    'sumitt', 'summit', 'ter', 'terr', 'terrace', 'throughway', 'tpke',
    'trace', 'traces', 'track', 'tracks', 'trafficway', 'trail', 'trailer',
    'trails', 'trak', 'trce', 'trfy', 'trk', 'trks', 'trl', 'trlr', 'trlrs',
    'trls', 'trnpk', 'trwy', 'tunel', 'tunl', 'tunls', 'tunnel', 'tunnels',
    'tunnl', 'turnpike', 'turnpk', 'un', 'underpass', 'union', 'unions', 'uns',
    'upas', 'valley', 'valleys', 'vally', 'vdct', 'via', 'viadct', 'viaduct',
    'view', 'views', 'vill', 'villag', 'village', 'villages', 'ville', 'villg',
    'villiage', 'vis', 'vist', 'vista', 'vl', 'vlg', 'vlgs', 'vlly', 'vly',
    'vlys', 'vst', 'vsta', 'vw', 'vws', 'walk', 'walks', 'wall', 'way', 'ways',
    'well', 'wells', 'wl', 'wls', 'wy', 'xing', 'xrd', 'xrds',
})
# cSpell:enable

ADDRESS_TOKEN_REGEX:Final = re.compile(r"""
\(*\b[^\s,;#&()]+[.,;)\n]*   # ['ab. cd,ef '] -> ['ab.', 'cd,', 'ef']
|
[#&]                       # [^'#abc'] -> ['#']
""",  re.VERBOSE | re.UNICODE)
TOKEN_CLEAN_REGEX:Final = re.compile(r'(^[\W]*)|([^.\w]*$)', re.UNICODE)

try:
    tagger = CRF(model_filename= MODEL_PATH)
except IOError:
    warnings.warn(f'You must train the model (parserator train --trainfile FILES) to create the {MODEL_FILE} file before you can use the parse  and tag methods') # cSpell: disable-line


def parse(address_string:str) -> List[Tuple[str, str]]:
    """
    Parse an address string into a list of (part, type) tuples.
    """
    tokens = tokenize(address_string)

    if not tokens:
        return []

    features = tokens2features(cast(Hashable, tokens))

    tags = tagger.predict(features)
    return list(zip(tokens, tags))


def tag(address_string:str, tag_mapping:Optional[Dict[str, str]]= None) -> Tuple["OrderedDict[str, str]", str]:
    """
    Tag an address string into word parts
    """
    tagged_address:OrderedDict[str, List[str]] = OrderedDict()

    last_label = None
    is_intersection = False
    og_labels:List[str] = []

    for token, label in parse(address_string):
        is_intersection = label == 'IntersectionSeparator'
        if 'StreetName' in label and is_intersection:
            label = f'Second {label}'

        # saving old label
        og_labels.append(label)
        # map tag to a new tag if tag mapping is provided
        if tag_mapping:
            newMapping = tag_mapping.get(label)
            if newMapping is not None:
                label = newMapping
        if label == last_label:
            tagged_address[label].append(token)
        elif label not in tagged_address:
            tagged_address[label] = [token]
        else:
            raise RepeatedLabelError(address_string, parse(address_string),  label)

        last_label = label

    taggedAddressJoined:OrderedDict[str, str] = OrderedDict()
    for token in tagged_address:
        component = ' '.join(tagged_address[token])
        component = component.strip().strip(",;")
        taggedAddressJoined[token] = component
    # Set up the AddressType literal
    if 'AddressNumber' in og_labels and not is_intersection:
        address_type = 'Street Address'
    elif is_intersection and 'AddressNumber' not in og_labels:
        address_type = 'Intersection'
    elif 'USPSBoxID' in og_labels:
        address_type = 'PO Box'
    else:
        address_type = 'Ambiguous'

    return taggedAddressJoined, address_type


@lru_cache(maxsize= None)
def tokenize(address_string:Union[str, bytes]) -> List[str]:
    """
    """
    if isinstance(address_string, bytes):
        address_string = str(address_string, encoding='utf-8')
    address_string = re.sub('(&#38;)|(&amp;)', '&', address_string)
    tokens:List[str] = ADDRESS_TOKEN_REGEX.findall(address_string)
    if not tokens:
        return []
    return tokens

@lru_cache(maxsize= 1024)
def tokenFeatures(token:str) -> Dict[str, Any]:
    """
    """
    if token in ('&', '#', '½'):
        token_clean = token
    else:
        token_clean = TOKEN_CLEAN_REGEX.sub('', token)

    token_abbrev = token_clean.lower().replace(".", "")
    features = {
        'abbrev': token_clean[-1] == '.',
        'digits': digits(token_clean),
        'word': (token_abbrev if not token_abbrev.isdigit()  else False),
        'trailing.zeros': (trailingZeros(token_abbrev) if token_abbrev.isdigit() else False),
        'length': ('d:' + str(len(token_abbrev)) if token_abbrev.isdigit() else 'w:' + str(len(token_abbrev))),
        'endsinpunc': (token[-1] if bool(re.match(r'.+[^.\w]', token, flags=re.UNICODE))  else False),
        'directional': token_abbrev in DIRECTIONS,
        'street_name': token_abbrev in STREET_NAMES,
        'has.vowels': bool(set(token_abbrev[1:]) & set('aeiou')),
    }

    return features

@lru_cache(maxsize= 4096)
def tokens2features(address):
    """
    """
    feature_sequence = [tokenFeatures(address[0])]
    previous_features = feature_sequence[-1].copy()

    for token in address[1:]:
        token_features = tokenFeatures(token)
        current_features = token_features.copy()

        feature_sequence[-1]['next'] = current_features
        token_features['previous'] = previous_features

        feature_sequence.append(token_features)

        previous_features = current_features

    feature_sequence[0]['address.start'] = True
    feature_sequence[-1]['address.end'] = True

    if len(feature_sequence) > 1:
        feature_sequence[1]['previous']['address.start'] = True
        feature_sequence[-2]['next']['address.end'] = True

    return feature_sequence

@lru_cache(maxsize= 1024)
def digits(token:str):
    """
    Return an identifier specifying if the token contains digits.
    """
    if token.isdigit():
        return 'all_digits'
    elif set(token) & set(string.digits):
        return 'some_digits'
    else:
        return 'no_digits'


def trailingZeros(token:str):
    """
    """
    if not token.endswith("0"):
        return ""
    return re.findall(r'(0+)$', token)[0]


class RepeatedLabelError(probableparsing.RepeatedLabelError):
    """
    """
    REPO_URL = 'https://github.com/datamade/usaddress/issues/new'
    DOCS_URL = 'https://usaddress.readthedocs.io/'

#!/usr/bin/env python3
"""
skuVocab.py - Pyrrhic Silva Shop

SINGLE SOURCE OF TRUTH for every SKU sub-part code (bead prefixes,
standalone prefixes, pride-flag/design codes, season/element/color
sub-variations, and earring findings).

skuParser.py, skuCostLookup.py, and salesToTrendsGen.py all import from
this module instead of keeping their own copies. To add, rename, or
retire a code: edit it HERE ONLY, then re-run
validate_against_trend_columns() (called automatically by
salesToTrendsGen.py) to confirm the trends CSV header still lines up.

skuKey.txt remains the human-readable reference doc and is not generated
from this file -- keep it in sync by hand when you edit here.

NOT covered by this module (deliberately -- these are structural/parsing
concerns, not vocabulary):
  - TREND_COLUMNS' literal order (lives in salesToTrendsGen.py; it encodes
    physical spreadsheet column layout)
  - NK[n] / BRAC[n] / BRAC-e[n] regex parsing (length is a number, not a
    fixed code)
  - RecipesData.csv (actual bead/material composition -- no code list can
    generate this, it has to be entered by hand)
"""

# ---------------------------------------------------------------------
# BEAD PREFIXES -- code -> (description, trend column name)
# ---------------------------------------------------------------------
BEAD_PREFIXES = {
    '4B':  ('Subtle series',      '4B'),
    '4C':  ('Cube series',        '4C'),
    '6P':  ('Pearlescent series', '6P'),
    '8R':  ('Bold series',        '8R'),
    'CHD': ("Upcycled",           'CHD'),
}

# ---------------------------------------------------------------------
# STANDALONE PREFIXES -- items that aren't bead-style based.
# trend column is None where the design only shows up via a more specific
# sub-column (e.g. KYO has no bare "KYO" column -- only KYO-Red/KYO-Black).
# ---------------------------------------------------------------------
STANDALONE_PREFIXES = {
    'AETHER':  ('Aether',                           'AETHER'),
    'CC':      ('Christmas candy cane',             'CC (Candy-Cane)'),
    'HOWLS':   ("Howl's Moving Castle cosplay",     'HOWLS'),
    'SEASONS': ('Seasons:',                         'SEASONS'),
    'KYO':     ('Kyo Soma',                         None),
    '10-13-STAR': ('twin shooting star chain',      '10-13-STAR'),
}

# ---------------------------------------------------------------------
# DESIGNS -- pride flags & misc designs that can appear on bead-prefixed
# items. code -> (description, trend column name)
#
# NOTE: 'MULTG' -> 'MULTIG' and 'MULTS' -> 'MULTIS' are NOT a typos. 
# The SKU code sold on Etsy is occasionally mispelled MULTG/MULTS, but 
# the trends CSV column is spelled MULTIG. Both scripts used to 
# assume the column name equals the code, so this sale was silently
# undercounted. Centralizing the mapping here fixes that for good.
# Additionally, ACE, CETERO, BI, and TRANS are old aliases that resolve 
# to their new proper name 
# ---------------------------------------------------------------------
DESIGNS = {
    'RAIN6':   ('6-stripe rainbow flag',                 'RAIN6'),
    'RAIN7':   ('7-stripe rainbow flag',                 'RAIN7'),
    'RAIN8':   ('8-stripe rainbow flag',                 'RAIN8'),
    'PROG':    ('progress pride flag',                   'PROG'),
    'PHILLY':  ('Philadelphia rainbow flag',             'PHILLY'),
    'LESBO5':  ('5-stripe lesbian flag',                 'LESBO5'),
    'GAY5':    ('5-stripe gay man flag',                 'GAY5'),
    'BI':     ('bisexual (mini) flag',                   'BI3'), # old alias backup
    'BI3':     ('bisexual (mini) flag',                  'BI3'),
    'BI5':     ('bisexual (full) flag',                  'BI5'),
    'PAN':     ('pansexual flag',                        'PAN'),
    'TRANS':  ('5-stripe transgender flag',              'TRANS5'), # old alias backup
    'TRANS3':  ('3-stripe transgender flag',             'TRANS3'),
    'TRANS5':  ('5-stripe transgender flag',             'TRANS5'),
    'GQUEER':  ('genderqueer flag',                      'GQUEER'),
    'GFLUID':  ('genderfluid flag',                      'GFLUID'),
    'ENBY':    ('nonbinary flag',                        'ENBY'),
    'INTSEX':  ('intersex flag',                         'INTSEX'),
    'AROACE':  ('aroace flag',                           'AROACE'),
    'ORAROACE':  ('oriented aroace flag',                'ORAROACE'),
    'ACE':    ('asexual flag',                           'ACE4'), # old alias backup
    'ACE4':    ('asexual flag',                          'ACE4'),
    'ACE6':    ('asexual (ace in grace) flag',           'ACE6'),
    'ARO':     ('aromantic flag',                        'ARO'),
    'CETERO': ('ceterosexual flag',                      'CETERO4'), # old alias backup
    'CETERO4': ('ceterosexual flag',                     'CETERO4'),
    'CETERO5': ('ceterosexual (alt) flag',               'CETERO5'),
    'MAV':     ('maverique flag',                        'MAV'),
    'AGEND':   ('agender flag',                          'AGEND'),
    'BIGEND':  ('bigender flag',                         'BIGEND'),
    'ANGY':    ('androgyne flag',                        'ANGY'),
    'GNEUT':   ('gender neutral flag',                   'GNEUT'),
    'TROIS':   ('neutrois flag',                         'TROIS'),
    'OMNIS':   ('omnisexual flag',                       'OMNIS'),
    'MULTG':   ('multigender flag',                      'MULTIG'),  # see note above
    'MULTIG':   ('multigender flag',                     'MULTIG'),
    'MULTS':   ('multisexual flag',                      'MULTIS'),  # see note above
    'MULTIS':   ('multisexual flag',                     'MULTIS'),
    'POLYG':   ('polygender flag',                       'POLYG'),
    'POLYS':   ('polysexual flag',                       'POLYS'),
    'BERRI':   ('berrisexual flag',                      'BERRI'),
    'ALMD':    ('almondsexual flag',                     'ALMD'),
    'ABRO':    ('abrosexual flag',                       'ABRO'),
    'QPR':     ('queer-platonic relationships flag',     'QPR'),
    'GAYBO':   ('gaybian flag',                          'GAYBO'),
    'GFLUX':   ('genderflux flag',                       'GFLUX'),
    'ANDRO':   ('androsexual flag',                      'ANDRO'),
    'GYNE':    ('gynesexual flag',                       'GYNE'),
    'QUEER':   ('queer flag',                            'QUEER'),
    'USA':     ('American flag',                         'USA'),
    'KRIS':    ('Kris/Chara shirt inspired',             'KRIS'),
    'FRISK':   ('Frisk shirt inspired',                  'FRISK'),
}

# ---------------------------------------------------------------------
# Sub-variations for prefixes that need a second, more specific token.
# Each is code -> (description, trend column name).
# ---------------------------------------------------------------------
SEASON_NAMES = {
    'WINTER': ('Winter', 'winter'),
    'SPRING': ('Spring', 'spring'),
    'SUMMER': ('Summer', 'summer'),
    'FALL':   ('Fall',   'fall'),
}

AETHER_ELEMENTS = {
    'ANEMO':   ('anemo',   'ANEMO'),
    'GEO':     ('geo',     'GEO'),
    'ELECTRO': ('electro', 'ELECTRO'),
    'DENDRO':  ('dendro',  'DENDRO'),
    'HYDRO':   ('hydro',   'HYDRO'),
    'PYRO':    ('pyro',    'PYRO'),
    'CRYO':    ('cryo',    'CRYO'),
    'NONE':    ('none',    'NONE'),
    'ALL':     ('all',     'ALL'),
}

CC_COLORS = {
    'RWG': ('red, white, green', 'RWG'),
    'RW':  ('red & white',       'RW'),
    'RG':  ('red & green',       'RG'),
}

KYO_COLORS = {
    'RED':   ('red bracelet inspired',   'KYO-Red'),
    'BLACK': ('black bracelet inspired', 'KYO-Black'),
}

# ---------------------------------------------------------------------
# FINDINGS -- earring/charm findings. This is the one dict that unifies
# ALL THREE consumers: description (skuParser), trend column
# (salesToTrendsGen), and packaging/multiplier cost data (skuCostLookup),
# because those are all just different attributes of the same finding.
# ---------------------------------------------------------------------
FINDINGS = {
    'LV': {
        'description': 'leverback earring',
        'trend_column': 'LV (lever back earrings)',
        'packaging': ('ear-card', 1),
        'charm_mult': 2, 'finding_mult': 2,
    },
    'WR': {
        'description': 'French wire earring',
        'trend_column': 'WR (fish hook earrings)',
        'packaging': ('ear-card', 1),
        'charm_mult': 2, 'finding_mult': 2,
    },
    'BP': {
        'description': '4mm ball post stud earring',
        'trend_column': 'BP (4mm ball post studs)',
        'packaging': ('ear-card', 1),
        'charm_mult': 2, 'finding_mult': 2,
    },
    'DK': {
        'description': 'earring (Aether outfit standard)',
        'trend_column': None,  # intentionally no trends column
        'packaging': ('ear-card', 1),
        'charm_mult': 1, 'finding_mult': 1,
    },
    'CH': {
        'description': 'phone charm',
        'trend_column': 'CH (phone charm)',
        'packaging': ('bag', 1),
        'charm_mult': 1, 'finding_mult': 1,
    },
}

# ---------------------------------------------------------------------
# FINDINGS_LEN -- finding types that pair a fixed material profile with
# a customer-chosen LENGTH (unlike FINDINGS above, which have no such
# variable). Any future finding type with a numeric suffix belongs HERE,
# not as a new bespoke *_INFO dict.
#
# NOTE ON PARSING: this dict does NOT make NK/BRAC/BRAC-e detection
# data-driven the way FINDINGS does for skuParser.py's _finding_patterns()
# loop. Each still needs its own regex with a numeric capture group
# (_NK_PATTERN, _BRAC_PATTERN, _BRAC_E_PATTERN in skuParser.py), because
# the "code" here is a category name plus a variable, not a fixed literal
# token the way 'LV' is. This dict centralizes the DATA only.
# ---------------------------------------------------------------------
FINDINGS_LEN = {
    'NK': {
        'trend_column': 'NK (necklace)',
        'length_trend_column': 'Chain (inches)',
        'packaging': {
            'zero': ('bag', 1),
            'nonzero': ('chain-card', 1),
        },
        'charm_mult': 1,
        'finding_mult': 1,
    },
    'BRAC': {
        'trend_column': 'BRAC (chain bracelets & chokers)',
        # Shared with BRAC-E below -- sales format uses ONE physical
        # column for both bracelet types' lengths. Nothing enforces these
        # two strings staying identical if you edit one later.
        'length_trend_column': 'BRAC (inches)',
        'packaging': None,   # TODO: not yet standardized
        'charm_mult': None,
        'finding_mult': None,
    },
    'BRAC-E': {
        'trend_column': 'BRAC-e (elastic bracelets)',
        'length_trend_column': 'BRAC (inches)',  # see BRAC note above
        'packaging': None,   # TODO: idea in progress, not finalized
        'charm_mult': None,
        'finding_mult': None,
    },
}


# ---------------------------------------------------------------------
# Non-finding structural item types, kept here mainly so their
# descriptions/trend columns aren't ALSO re-typed in three places.
# The parsing logic for these (regexes, single-vs-pair branching, length
# math) stays in each script -- only the fixed strings live here.
# ---------------------------------------------------------------------
TART_INFO = {
    'description_single': 'Tartaglia cosplay earring (single)',
    'description_pair': 'Tartaglia cosplay earrings (pair)',
    'trend_column': 'TART',
    'packaging': ('ear-card', 1),
}


# ---------------------------------------------------------------------
# CANONICAL-FORM HELPERS -- several code_map dicts above (DESIGNS,
# SEASON_NAMES, AETHER_ELEMENTS, CC_COLORS, KYO_COLORS, BEAD_PREFIXES,
# STANDALONE_PREFIXES) share the same code -> (description, trend_column)
# shape, and more than one code can point at the same trend_column (old
# aliases like BI/BI3, misspellings like MULTG/MULTIG). These two
# functions answer "what's the canonical identity behind this code (or
# these codes)?" for any dict of that shape -- not just DESIGNS -- so
# any script working with SKU codes can resolve aliases consistently
# instead of re-deriving the same code.upper() == trend_column.upper()
# check locally.
# ---------------------------------------------------------------------
def group_designs_by_trend_column(code_map):
    """Group a code -> (description, trend_column) dict by trend_column
    (the actual design/identity), since multiple codes can point at the
    same one (e.g. BI/BI3 both -> BI3).

    Returns dict trend_column -> {'codes': set of all codes for it,
    'canonical': the code where code == trend_column (or None if somehow
    absent), 'description': description text from the canonical code, or
    from whichever code is available if no canonical one exists}.
    """
    groups = {}
    for code, (desc, trend_col) in code_map.items():
        group = groups.setdefault(trend_col, {'codes': set(), 'canonical': None, 'description': None})
        group['codes'].add(code)
        if code.upper() == trend_col.upper():
            group['canonical'] = code
            group['description'] = desc
        elif group['description'] is None:
            group['description'] = desc
    return groups


def flag_identity(code, code_map):
    """Return the canonical grouping identity for a single code: the
    trend_column if it's a known key in code_map (so aliases like 'BI'
    and 'BI3' are recognized as the same design), or the raw code itself
    if it isn't in code_map at all (nothing to canonicalize to yet).
    """
    if code in code_map:
        return code_map[code][1]
    return code

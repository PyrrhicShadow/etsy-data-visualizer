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
# code: {'description', 'trend column', 'category'}
# ---------------------------------------------------------------------
STANDALONE_PREFIXES = {
    'AETHER':     {'desc': 'Aether',                       'trend_col': 'AETHER',          'category': 'Cosplay'},
    'CC':         {'desc': 'Christmas candy cane',         'trend_col': 'CC (Candy-Cane)', 'category': 'Holiday'},
    'HOWLS':      {'desc': "Howl's Moving Castle cosplay", 'trend_col': 'HOWLS',           'category': 'Cosplay'},
    'SEASONS':    {'desc': 'Seasons:',                     'trend_col':'SEASONS',          'category': 'Cottagecore'},
    'KYO':        {'desc': 'Kyo Soma',                     'trend_col': 'KYO',             'category': 'Cosplay'},
    '10-13-STAR': {'desc': 'twin shooting star chain',     'trend_col': '10-13-STAR',      'category': 'Cottagecore'},
}

# ---------------------------------------------------------------------
# DESIGNS -- pride flags & misc designs that can appear on bead-prefixed
# items. code -> (description, trend column name)
# NOTE: see aliases in DESIGN_ALIASES
# ---------------------------------------------------------------------
PRIDE_DESIGNS = {
    'RAIN6':    {'desc': '6-stripe rainbow flag',                 'trend_col': 'RAIN6',    'category': 'Pride'},
    'RAIN7':    {'desc': '7-stripe rainbow flag',                 'trend_col': 'RAIN7',    'category': 'Pride'},
    'RAIN8':    {'desc': '8-stripe rainbow flag',                 'trend_col': 'RAIN8',    'category': 'Pride'},
    'PROG':     {'desc': 'progress pride flag',                   'trend_col': 'PROG',     'category': 'Pride'},
    'PHILLY':   {'desc': 'Philadelphia rainbow flag',             'trend_col': 'PHILLY',   'category': 'Pride'},
    'LESBO5':   {'desc': '5-stripe lesbian flag',                 'trend_col': 'LESBO5',   'category': 'Pride'},
    'GAY5':     {'desc': '5-stripe gay man flag',                 'trend_col': 'GAY5',     'category': 'Pride'},
    'BI3':      {'desc': 'bisexual (mini) flag',                  'trend_col': 'BI3',      'category': 'Pride'},
    'BI5':      {'desc': 'bisexual (full) flag',                  'trend_col': 'BI5',      'category': 'Pride'},
    'PAN':      {'desc': 'pansexual flag',                        'trend_col': 'PAN',      'category': 'Pride'},
    'TRANS3':   {'desc': '3-stripe transgender flag',             'trend_col': 'TRANS3',   'category': 'Pride'},
    'TRANS5':   {'desc': '5-stripe transgender flag',             'trend_col': 'TRANS5',   'category': 'Pride'},
    'GQUEER':   {'desc': 'genderqueer flag',                      'trend_col': 'GQUEER',   'category': 'Pride'},
    'GFLUID':   {'desc': 'genderfluid flag',                      'trend_col': 'GFLUID',   'category': 'Pride'},
    'ENBY':     {'desc': 'nonbinary flag',                        'trend_col': 'ENBY',     'category': 'Pride'},
    'INTSEX':   {'desc': 'intersex flag',                         'trend_col': 'INTSEX',   'category': 'Pride'},
    'AROACE':   {'desc': 'aroace flag',                           'trend_col': 'AROACE',   'category': 'Pride'},
    'ORAROACE': {'desc': 'oriented aroace flag',                  'trend_col': 'ORAROACE', 'category': 'Pride'},
    'ACE4':     {'desc': 'asexual flag',                          'trend_col': 'ACE4',     'category': 'Pride'},
    'ACE6':     {'desc': 'asexual (ace in grace) flag',           'trend_col': 'ACE6',     'category': 'Pride'},
    'ARO':      {'desc': 'aromantic flag',                        'trend_col': 'ARO',      'category': 'Pride'},
    'CETERO4':  {'desc': 'ceterosexual flag',                     'trend_col': 'CETERO4',  'category': 'Pride'},
    'CETERO5':  {'desc': 'ceterosexual (alt) flag',               'trend_col': 'CETERO5',  'category': 'Pride'},
    'MAV':      {'desc': 'maverique flag',                        'trend_col': 'MAV',      'category': 'Pride'},
    'AGEND':    {'desc': 'agender flag',                          'trend_col': 'AGEND',    'category': 'Pride'},
    'BIGEND':   {'desc': 'bigender flag',                         'trend_col': 'BIGEND',   'category': 'Pride'},
    'ANGY':     {'desc': 'androgyne flag',                        'trend_col': 'ANGY',     'category': 'Pride'},
    'GNEUT':    {'desc': 'gender neutral flag',                   'trend_col': 'GNEUT',    'category': 'Pride'},
    'TROIS':    {'desc': 'neutrois flag',                         'trend_col': 'TROIS',    'category': 'Pride'},
    'OMNIS':    {'desc': 'omnisexual flag',                       'trend_col': 'OMNIS',    'category': 'Pride'},
    'MULTIG':   {'desc': 'multigender flag',                      'trend_col': 'MULTIG',   'category': 'Pride'},
    'MULTIS':   {'desc': 'multisexual flag',                      'trend_col': 'MULTIS',   'category': 'Pride'},
    'POLYG':    {'desc': 'polygender flag',                       'trend_col': 'POLYG',    'category': 'Pride'},
    'POLYS':    {'desc': 'polysexual flag',                       'trend_col': 'POLYS',    'category': 'Pride'},
    'BERRI':    {'desc': 'berrisexual flag',                      'trend_col': 'BERRI',    'category': 'Pride'},
    'ALMD':     {'desc': 'almondsexual flag',                     'trend_col': 'ALMD',     'category': 'Pride'},
    'ABRO':     {'desc': 'abrosexual flag',                       'trend_col': 'ABRO',     'category': 'Pride'},
    'QPR':      {'desc': 'queer-platonic relationships flag',     'trend_col': 'QPR',      'category': 'Pride'},
    'GAYBO':    {'desc': 'gaybian flag',                          'trend_col': 'GAYBO',    'category': 'Pride'},
    'GFLUX':    {'desc': 'genderflux flag',                       'trend_col': 'GFLUX',    'category': 'Pride'},
    'ANDRO':    {'desc': 'androsexual flag',                      'trend_col': 'ANDRO',    'category': 'Pride'},
    'GYNE':     {'desc': 'gynesexual flag',                       'trend_col': 'GYNE',     'category': 'Pride'},
    'QUEER':    {'desc': 'queer flag',                            'trend_col': 'QUEER',    'category': 'Pride'},
}

MISC_DESIGNS = {
    'USA':     {'desc': 'American flag',             'trend_col': 'USA',   'category': 'Holiday'},
    'KRIS':    {'desc': 'Kris/Chara shirt inspired', 'trend_col': 'KRIS',  'category': 'Cosplay'},
    'FRISK':   {'desc': 'Frisk shirt inspired',      'trend_col': 'FRISK', 'category': 'Cosplay'},
}

# ---------------------------------------------------------------------
# PRIDE ALIASES -- aliases or misspellings of canonical PRIDE DESIGNS
# 'MULTG' -> 'MULTIG' and 'MULTS' -> 'MULTIS' are NOT a typos. 
# The SKU code sold on Etsy is occasionally mispelled MULTG/MULTS, but 
# the trends CSV column is spelled MULTIG. Both scripts used to 
# assume the column name equals the code, so this sale was silently
# undercounted. Centralizing the mapping here fixes that for good.
# Additionally, ACE, CETERO, BI, and TRANS are old aliases that resolve 
# to their new proper name 

PRIDE_ALIASES = {
    'BI':     {'desc': 'bisexual (mini) flag',      'trend_col': 'BI3',     'category': 'Pride'},  # old alias backup
    'TRANS':  {'desc': '5-stripe transgender flag', 'trend_col': 'TRANS5',  'category': 'Pride'},  # old alias backup
    'ACE':    {'desc': 'asexual flag',              'trend_col': 'ACE4',    'category': 'Pride'},  # old alias backup
    'CETERO': {'desc': 'ceterosexual flag',         'trend_col': 'CETERO4', 'category': 'Pride'},  # old alias backup
    'MULTG':  {'desc': 'multigender flag',          'trend_col': 'MULTIG',  'category': 'Pride'},  # see note above
    'MULTS':  {'desc': 'multisexual flag',          'trend_col': 'MULTIS',  'category': 'Pride'},  # see note above
}

# ---------------------------------------------------------------------
# Sub-variations for prefixes that need a second, more specific token.
# Each is code -> (description, trend column name).
# ---------------------------------------------------------------------
SEASON_NAMES = {
    'WINTER': {'desc': 'Winter', 'trend_col': 'winter', 'category': 'Cottagecore'},
    'SPRING': {'desc': 'Spring', 'trend_col': 'spring', 'category': 'Cottagecore'},
    'SUMMER': {'desc': 'Summer', 'trend_col': 'summer', 'category': 'Cottagecore'},
    'FALL':   {'desc': 'Fall',   'trend_col': 'fall',   'category': 'Cottagecore'},
}

AETHER_ELEMENTS = {
    'ANEMO':   {'desc': 'anemo',   'trend_col': 'ANEMO',   'category': 'Cosplay'},
    'GEO':     {'desc': 'geo',     'trend_col': 'GEO',     'category': 'Cosplay'},
    'ELECTRO': {'desc': 'electro', 'trend_col': 'ELECTRO', 'category': 'Cosplay'},
    'DENDRO':  {'desc': 'dendro',  'trend_col': 'DENDRO',  'category': 'Cosplay'},
    'HYDRO':   {'desc': 'hydro',   'trend_col': 'HYDRO',   'category': 'Cosplay'},
    'PYRO':    {'desc': 'pyro',    'trend_col': 'PYRO',    'category': 'Cosplay'},
    'CRYO':    {'desc': 'cryo',    'trend_col': 'CRYO',    'category': 'Cosplay'},
    'NONE':    {'desc': 'none',    'trend_col': 'NONE',    'category': 'Cosplay'},
    'ALL':     {'desc': 'all',     'trend_col': 'ALL',     'category': 'Cosplay'},
}

CC_COLORS = {
    'RWG': {'desc': 'red, white, green', 'trend_col': 'RWG', 'category': 'Holiday'},
    'RW':  {'desc': 'red & white',       'trend_col': 'RW',  'category': 'Holiday'},
    'RG':  {'desc': 'red & green',       'trend_col': 'RG',  'category': 'Holiday'},
}

KYO_COLORS = {
    'RED':   {'desc': 'red bracelet inspired',   'trend_col': 'KYO-Red',  'category': 'Cosplay'},
    'BLACK': {'desc': 'black bracelet inspired', 'trend_col': 'KYO-Black', 'category': 'Cosplay'},
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
        'jewelry_type': 'earrings',
    },
    'WR': {
        'description': 'French wire earring',
        'trend_column': 'WR (fish hook earrings)',
        'packaging': ('ear-card', 1),
        'charm_mult': 2, 'finding_mult': 2,
        'jewelry_type': 'earrings',
    },
    'BP': {
        'description': '4mm ball post stud earring',
        'trend_column': 'BP (4mm ball post studs)',
        'packaging': ('ear-card', 1),
        'charm_mult': 2, 'finding_mult': 2,
        'jewelry_type': 'earrings',
    },
    'DK': {
        'description': 'earring (Aether outfit standard)',
        'trend_column': None,  # intentionally no trends column
        'packaging': ('ear-card', 1),
        'charm_mult': 1, 'finding_mult': 1,
        'jewelry_type': 'earrings',
    },
    'CH': {
        'description': 'phone charm',
        'trend_column': 'CH (phone charm)',
        'packaging': ('bag', 1),
        'charm_mult': 1, 'finding_mult': 1,
        'jewelry_type': 'phone charm',
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
        'description': {
            'zero': 'necklace charm with bail only',
            'nonzero': 'necklace with {length}-inch chain',
        },
        'packaging': {
            'zero': ('bag', 1),
            'nonzero': ('chain-card', 1),
        },
        'charm_mult': 1,
        'finding_mult': 1,
        'jewelry_type': 'necklace',
    },
    'BRAC': {
        'trend_column': 'BRAC (chain bracelets & chokers)',
        'length_trend_column': 'BRAC (inches)',
        'description': 'chain bracelet or choker ({length}-inch long)',
        'packaging': None,   # TODO: not yet standardized
        'charm_mult': None,
        'finding_mult': None,
        'jewelry_type': 'bracelet',
    },
    'BRAC-E': {
        'trend_column': 'BRAC-e (elastic bracelets)',
        'length_trend_column': 'BRAC (inches)',
        'description': 'elastic bracelet ({length}-inch long)',
        'packaging': None,   # TODO: idea in progress, not finalized
        'charm_mult': None,
        'finding_mult': None,
        'jewelry_type': 'bracelet',
    },
}

# ---------------------------------------------------------------------
# DEFAULT PACKAGING -- fallback packaging for any SKU with no suffix and
# no category-specific rule (e.g. standalone recipe keys). This is a 
# specific, deliberate choice (a generic bag), not a universal default 
# other rules should be assumed to derive from.
# NK's zero-length packaging and CH's packaging both also happen to use
# 'bag' right now, but that's coincidence, not inheritance -- each was
# decided independently and can diverge from this one at any time.
# ---------------------------------------------------------------------
DEFAULT_PACKAGING = ('bag', 1)

# ---------------------------------------------------------------------
# Item types with an implicit finding, kept here mainly so their
# descriptions/trend columns aren't ALSO re-typed in three places.
# The parsing logic for these (regexes, single-vs-pair branching, length
# math) stays in each script -- only the fixed strings live here.
# ---------------------------------------------------------------------
TART_INFO = {
    'description_single': 'Tartaglia cosplay earring (single)',
    'description_pair': 'Tartaglia cosplay earrings (pair)',
    'trend_column': 'TART',
    'packaging': ('ear-card', 1),
    'jewelry_type': 'earrings',
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
def group_designs_by_trend_column(code_map, alias_map=None):
    """Group a code -> (description, trend_column) dict by trend_column
    (the actual design/identity), since multiple codes can point at the
    same one.

    If alias_map is given (DESIGN_ALIASES is the only current case), its
    codes are merged into the group of the canonical design they resolve
    to, so e.g. 'BI' shows up as an alias of the 'BI3' group even though
    'BI' is no longer a key in code_map itself.

    Returns dict trend_column -> {'codes': set of all codes for it,
    'canonical': the code where code == trend_column (or None if somehow
    absent), 'description': description text from the canonical code, or
    from whichever code is available if no canonical one exists}.
    """
    groups = {}
    for code, entry in code_map.items():
        trend_col = entry['trend_col']
        desc = entry['desc']
        group = groups.setdefault(trend_col, {'codes': set(), 'canonical': None, 'description': None})
        group['codes'].add(code)
        if code.upper() == trend_col.upper():
            group['canonical'] = code
            group['description'] = desc
        elif group['description'] is None:
            group['description'] = desc

    if alias_map:
        for alias_code, entry in alias_map.items():
            trend_col = entry['trend_col']
            desc = entry['desc']
            group = groups.setdefault(trend_col, {'codes': set(), 'canonical': None, 'description': None})
            group['codes'].add(alias_code)
            if group['description'] is None:
                group['description'] = desc

    return groups


def flag_identity(code, code_map, alias_map=None):
    """Return the canonical grouping identity for a single code.

    Checks code_map first: if `code` is a key there, its own
    trend_column is the identity.

    If `code` isn't in code_map at all and alias_map is given, falls back
    to alias_map -- a hit there resolves to ITS trend_column, so an alias
    like 'BI' groups with the canonical 'BI3' design even though 'BI' is
    not a code_map key anymore.

    Falls back to the raw code if it's in neither -- nothing to
    canonicalize to yet.
    """
    if code in code_map:
        return code_map[code]['trend_col']
    if alias_map and code in alias_map:
        return alias_map[code]['trend_col']
    return code

def resolve_design_category(prefix, design, type=None):
    """Resolve a parsed SKU's (prefix, design, type) into a design
    category for trend reporting, spanning PRIDE_DESIGNS, MISC_DESIGNS,
    and STANDALONE_PREFIXES (plus their sub-variation dicts) uniformly.

    Inputs are the already-parsed primitives from skuParser.parse_sku()
    -- NOT a raw SKU string. This function must never import or call
    parse_sku() itself: skuParser.py imports skuVocab.py, so the reverse
    import would be circular. type is needed (not just prefix)
    because TART parses with prefix=None; type=='TART' is the only
    signal that carries.

    Returns (result, warning):
      result is None, warning is None  -- this SKU has no design axis at
        all (bare packaging/recipe keys, findings with no attached
        design). Expected, not an error.
      result is None, warning is a str -- prefix/type indicated a
        design SHOULD be present but `design` didn't resolve against any
        known vocab (new/misspelled flag, or a standalone sub-variation
        code not yet in skuVocab.py). Surface this the same way every
        other warning in this project gets surfaced -- it's a
        checkNewFlags.py-shaped gap, not a crash.
      result is a dict, warning is None -- resolved. Shape:
        {'identity': str, 'coarse_identity': str or None,
         'category': 'pride' | 'misc', 'description': str}
        coarse_identity == identity when there's no finer breakdown
        available (pride/misc designs, HOWLS, 10-13-STAR, TART).
    """
    if type == 'TART':
        return {
            'identity': 'TART', 'coarse_identity': 'TART',
            'category': 'Cosplay', 'description': TART_INFO['trend_column'],
        }, None

    if prefix in STANDALONE_PREFIXES:
        entry = STANDALONE_PREFIXES[prefix]

        if prefix in ('HOWLS', '10-13-STAR'):
            return {
                'identity': prefix, 'coarse_identity': entry['trend_col'],
                'category': entry['category'], 'description': entry['desc'],
            }, None

        sub_map = {
            'AETHER': AETHER_ELEMENTS, 'SEASONS': SEASON_NAMES,
            'CC': CC_COLORS, 'KYO': KYO_COLORS,
        }.get(prefix)

        if sub_map is None:
            # A STANDALONE_PREFIXES entry with no sub-variation dict
            # wired up here -- a real gap, not an expected shape.
            return None, (
                f"'{prefix}' is a STANDALONE_PREFIXES entry with no "
                f"sub-variation lookup registered in resolve_design_identity()."
            )

        if design is None or design not in sub_map:
            return None, (
                f"'{prefix}' sub-variation '{design}' not found in its "
                f"vocab dict -- may be new or misspelled."
            )

        return {
            'identity': design, 'coarse_identity': entry['trend_col'],
            'category': entry['category'], 'description': entry['desc'],
        }, None

    if prefix in BEAD_PREFIXES:
        if design is None:
            return None, None  # bead-prefixed item with no design token at all -- unusual but not this function's concern to flag; parse_sku already tracks unmatched_design_token separately.

        if design in PRIDE_DESIGNS:
            entry = PRIDE_DESIGNS[design]
            return {
                'identity': design, 'coarse_identity': entry['trend_col'],
                'category': entry['category'], 'description': entry['desc'],
            }, None

        if design in MISC_DESIGNS:
            entry = MISC_DESIGNS[design]
            return {
                'identity': design, 'coarse_identity': entry['trend_col'],
                'category': entry['category'], 'description': entry['desc'],
            }, None

        return None, (
            f"Design '{design}' not found in PRIDE_DESIGNS or "
            f"MISC_DESIGNS -- may be new or misspelled."
        )

    return None, None
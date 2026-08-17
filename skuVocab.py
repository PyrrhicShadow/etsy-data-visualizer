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
# NOTE: see aliases in DESIGN_ALIASES
# ---------------------------------------------------------------------
PRIDE_DESIGNS = {
    'RAIN6':   ('6-stripe rainbow flag',                 'RAIN6'),
    'RAIN7':   ('7-stripe rainbow flag',                 'RAIN7'),
    'RAIN8':   ('8-stripe rainbow flag',                 'RAIN8'),
    'PROG':    ('progress pride flag',                   'PROG'),
    'PHILLY':  ('Philadelphia rainbow flag',             'PHILLY'),
    'LESBO5':  ('5-stripe lesbian flag',                 'LESBO5'),
    'GAY5':    ('5-stripe gay man flag',                 'GAY5'),
    'BI3':     ('bisexual (mini) flag',                  'BI3'),
    'BI5':     ('bisexual (full) flag',                  'BI5'),
    'PAN':     ('pansexual flag',                        'PAN'),
    'TRANS3':  ('3-stripe transgender flag',             'TRANS3'),
    'TRANS5':  ('5-stripe transgender flag',             'TRANS5'),
    'GQUEER':  ('genderqueer flag',                      'GQUEER'),
    'GFLUID':  ('genderfluid flag',                      'GFLUID'),
    'ENBY':    ('nonbinary flag',                        'ENBY'),
    'INTSEX':  ('intersex flag',                         'INTSEX'),
    'AROACE':  ('aroace flag',                           'AROACE'),
    'ORAROACE':  ('oriented aroace flag',                'ORAROACE'),
    'ACE4':    ('asexual flag',                          'ACE4'),
    'ACE6':    ('asexual (ace in grace) flag',           'ACE6'),
    'ARO':     ('aromantic flag',                        'ARO'),
    'CETERO4': ('ceterosexual flag',                     'CETERO4'),
    'CETERO5': ('ceterosexual (alt) flag',               'CETERO5'),
    'MAV':     ('maverique flag',                        'MAV'),
    'AGEND':   ('agender flag',                          'AGEND'),
    'BIGEND':  ('bigender flag',                         'BIGEND'),
    'ANGY':    ('androgyne flag',                        'ANGY'),
    'GNEUT':   ('gender neutral flag',                   'GNEUT'),
    'TROIS':   ('neutrois flag',                         'TROIS'),
    'OMNIS':   ('omnisexual flag',                       'OMNIS'),
    'MULTIG':   ('multigender flag',                     'MULTIG'),
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
}

MISC_DESIGNS = {
    'USA':     ('American flag',                         'USA'),
    'KRIS':    ('Kris/Chara shirt inspired',             'KRIS'),
    'FRISK':   ('Frisk shirt inspired',                  'FRISK'),
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
    'BI':     ('bisexual (mini) flag',                   'BI3'), # old alias backup
    'TRANS':  ('5-stripe transgender flag',              'TRANS5'), # old alias backup
    'ACE':    ('asexual flag',                           'ACE4'), # old alias backup
    'CETERO': ('ceterosexual flag',                      'CETERO4'), # old alias backup
    'MULTG':   ('multigender flag',                      'MULTIG'),  # see note above
    'MULTS':   ('multisexual flag',                      'MULTIS'),  # see note above
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
        'jewelry_type': 'phone_charm',
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
    for code, (desc, trend_col) in code_map.items():
        group = groups.setdefault(trend_col, {'codes': set(), 'canonical': None, 'description': None})
        group['codes'].add(code)
        if code.upper() == trend_col.upper():
            group['canonical'] = code
            group['description'] = desc
        elif group['description'] is None:
            group['description'] = desc

    if alias_map:
        for alias_code, (desc, trend_col) in alias_map.items():
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
        return code_map[code][1]
    if alias_map and code in alias_map:
        return alias_map[code][1]
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
         'kind': 'pride' | 'misc', 'description': str}
        coarse_identity == identity when there's no finer breakdown
        available (pride/misc designs, HOWLS, 10-13-STAR, TART).
        coarse_identity is None ONLY for KYO, which per
        STANDALONE_PREFIXES has no bare trend column -- only
        KYO-Red/KYO-Black exist. That's correct, not a bug.

    OPTION A SCOPE NOTE: `kind` is presently a flat 'pride'/'misc' split
    derived from which dict the design was found in -- NOT the
    finer holiday/cosplay/fairycore taxonomy Julien wants eventually.
    Every STANDALONE_PREFIXES-sourced identity (TART, HOWLS, 10-13-STAR,
    AETHER/CC/KYO/SEASONS and their sub-variations) is 'misc' here,
    undifferentiated. Revisit alongside the planned PRIDE_DESIGNS/
    MISC_DESIGNS/STANDALONE_PREFIXES tuple-to-dict migration (Option B),
    NOT by patching special cases into this function in the meantime --
    that migration is where a real 'kind' field belongs, adjacent to
    where 'jewelry_type' already lives on FINDINGS.
    """
    if type == 'TART':
        return {
            'identity': 'TART', 'coarse_identity': 'TART',
            'kind': 'misc', 'description': TART_INFO['trend_column'],
        }, None

    if prefix in STANDALONE_PREFIXES:
        coarse_desc, coarse_col = STANDALONE_PREFIXES[prefix]

        if prefix in ('HOWLS', '10-13-STAR'):
            return {
                'identity': coarse_col, 'coarse_identity': coarse_col,
                'kind': 'misc', 'description': coarse_desc,
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

        fine_desc, fine_col = sub_map[design]
        return {
            'identity': fine_col, 'coarse_identity': coarse_col,
            'kind': 'misc', 'description': fine_desc,
        }, None

    if prefix in BEAD_PREFIXES:
        if design is None:
            return None, None  # bead-prefixed item with no design token at all -- unusual but not this function's concern to flag; parse_sku already tracks unmatched_design_token separately.

        if design in PRIDE_DESIGNS:
            desc, col = PRIDE_DESIGNS[design]
            return {
                'identity': col, 'coarse_identity': col,
                'kind': 'pride', 'description': desc,
            }, None

        if design in MISC_DESIGNS:
            desc, col = MISC_DESIGNS[design]
            return {
                'identity': col, 'coarse_identity': col,
                'kind': 'misc', 'description': desc,
            }, None

        return None, (
            f"Design '{design}' not found in PRIDE_DESIGNS or "
            f"MISC_DESIGNS -- may be new or misspelled."
        )

    return None, None
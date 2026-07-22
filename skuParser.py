# SKU Parser - Unified Architecture (Draft 5)

from skuVocab import (
    BEAD_PREFIXES as _BEAD, STANDALONE_PREFIXES as _STANDALONE, DESIGNS,
    SEASON_NAMES, AETHER_ELEMENTS, CC_COLORS, KYO_COLORS, FINDINGS,
)

# skuParser needs code -> description only; derive it from the vocabulary.
BEAD_PREFIXES = {**{k: v[0] for k, v in _BEAD.items()},
                  **{k: v[0] for k, v in _STANDALONE.items()}}

MIDDLE_VARIATIONS = {
    **{k: v[0] for k, v in SEASON_NAMES.items()},
    **{k: v[0] for k, v in KYO_COLORS.items()},
    **{k: v[0] for k, v in AETHER_ELEMENTS.items()},
    **{k: v[0] for k, v in CC_COLORS.items()},
    **{k: v[0] for k, v in DESIGNS.items()},
}

SUFFIX_FINDINGS = {k: v['description'] for k, v in FINDINGS.items()}

# Suffix patterns for NK and BRAC
SUFFIX_PATTERNS = [
    ('BRAC_E', r'BRAC[-]?e[-]?(\d+(?:\.\d+)?)$', 'elastic', None),
    ('BRAC_CHAIN', r'BRAC(\d+(?:\.\d+)?)$', 'chain', None),
    ('NK', r'NK(\d+)$', None, int),
]

TART_VALUES = {'1': 'earring (single)', '2': 'earrings (pair)'}

def parse_sku(sku_input):
    """Parse a SKU string into its components."""
    sku_original = sku_input.strip()
    sku = sku_input.strip().upper()
    
    import re
    
    # == Step 1: Check for TART (standalone, no suffixes) ==
    tart_match = re.match(r'^TART-(\d+)$', sku)
    if tart_match:
        n_val = tart_match.group(1)
        return {
            'sku': sku_original,
            'formatted_description': f"Tartaglia cosplay {TART_VALUES.get(n_val, 'unknown')}",
        }
    
    # == Step 2: Find matching base prefix ==
    matched_prefix = None
    remainder = None
    
    for prefix in BEAD_PREFIXES:
        if sku.startswith(prefix + '-') or sku == prefix:
            matched_prefix = prefix
            remainder = sku[len(prefix):].strip('-')
            break
    
    if not matched_prefix:
        return {'error': f'Could not parse SKU: {sku_original}. Check the SKU format.'}
    
    # == Step 3: Parse middle variation (UNIFIED FOR ALL PREFIX TYPES) ==
    middle_variation = None
    variation_desc = None
    
    if remainder:
        for var in MIDDLE_VARIATIONS:
            if remainder.startswith(var):
                middle_variation = var
                variation_desc = MIDDLE_VARIATIONS[var]
                remainder = remainder[len(var):].strip('-')
                break
    
    # == Step 4: Parse suffix (finding or spec pattern) ==
    finding = None
    chain_length = None
    brace_length = None
    brace_type = None
    
    if remainder:
        # CHECK 1: Is remainder exactly a finding?
        if remainder in SUFFIX_FINDINGS:
            finding = remainder
            remainder = ''
        # CHECK 2: Is remainder ending with a finding?
        else:
            finding_match = re.match(r'^(.+)-?(LV|WR|BP|CH)$', remainder)
            if finding_match:
                middle_part = finding_match.group(1).strip('-')
                finding = finding_match.group(2)
                # If we got a middle part we didn't expect, treat as unknown design
                if middle_part and middle_variation is None:
                    # Unexpected design token before finding
                    pass
                remainder = ''
            else:
                # CHECK 3: Spec patterns (BRAC, NK)
                for _name, pattern, brace_val, chain_val in SUFFIX_PATTERNS:
                    spec_match = re.search(f'{pattern}$', remainder, re.IGNORECASE)
                    if spec_match:
                        remainder = remainder[:spec_match.start()]
                        if brace_val:
                            brace_length = float(spec_match.group(1))
                            brace_type = brace_val
                        elif chain_val:
                            chain_length = chain_val(spec_match.group(1))
                        break
    
    # == Step 5: Build description ==
    desc_parts = []
    
    # Add prefix description
    prefix_desc = BEAD_PREFIXES.get(matched_prefix, matched_prefix.lower())
    desc_parts.append(prefix_desc)
    
    # Add middle variation description (uniform for ALL types)
    if middle_variation:
        # Special formatting for certain types
        if matched_prefix == 'AETHER':
            desc_parts[-1] += f' ({variation_desc}) cosplay'
        elif matched_prefix == 'SEASONS':
            desc_parts.append(f"{variation_desc} themed cottage-core")
        elif matched_prefix == 'KYO':
            desc_parts.append(f"({variation_desc})")
        elif matched_prefix == 'CC':
            desc_parts.append(f"({variation_desc})")
        else:
            desc_parts.append(variation_desc)
    
    # Add specs (finding OR chain OR bracelet)
    if finding:
        finding_desc = SUFFIX_FINDINGS[finding]
        desc_parts.append(finding_desc)
        if matched_prefix != 'AETHER' and finding != 'CH':
            desc_parts[-1] += 's'  # Plural for non-Aether earring items
    
    elif chain_length is not None:
        if chain_length == 0:
            desc_parts.append('necklace charm with bail only')
        else:
            desc_parts.append(f'necklace with {chain_length}-inch chain')
    
    elif brace_length is not None:
        if brace_type == 'elastic':
            desc_parts.append(f'elastic bracelet ({brace_length}-inch long)')
        else:
            desc_parts.append(f'chain bracelet or choker ({brace_length}-inch long)')
    
    formatted_desc = ' '.join(desc_parts)
    
    return {
        'sku': sku_original,
        'matched_prefix': matched_prefix,
        'middle_variation': middle_variation,
        'finding': finding,
        'chain_length': chain_length,
        'brace_length': brace_length,
        'brace_type': brace_type,
        'formatted_description': formatted_desc,
    }

def main():
    print("=" * 60)
    print("SKU PARSER - Pyrrhic Silva Shop")
    print("=" * 60)
    print("\nEnter a SKU (or 'quit' to exit):\n")
    
    while True:
        user_input = input(">>> ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\nGoodbye!\n")
            break
        
        if not user_input:
            continue
        
        result = parse_sku(user_input)
        
        if 'error' in result:
            print(f"\n❌ {result['error']}\n")
        else:
            print(f"\n✅ SKU: {result['sku']}")
            print(f"   {result['formatted_description']}")
    
    print()

if __name__ == "__main__":
    main()
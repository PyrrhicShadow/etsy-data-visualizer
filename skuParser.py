# SKU Parser - Bug Fixed (Draft 4)

SKU_KEY = {
    # == Bead styles / Design prefixes ==
    '4B': '4mm bicone beads',
    '4C': '4mm cube beads',
    '6P': '6mm pearl beads',
    '8R': '8mm round beads',
    'CHD': "children's bracelet kit beads",
    'AETHER': 'Aether cosplay',
    'CC-RW': 'candy cane (red & white)',
    'CC-RWG': 'candy cane (red, white, green)',
    
    # == Pride flags ==
    'RAIN6': '6-stripe rainbow',
    'RAIN7': '7-stripe rainbow',
    'RAIN8': '8-stripe rainbow',
    'PROG': 'progress pride',
    'PHILLY': 'Philadelphia rainbow',
    'LESBO5': '5-stripe lesbian',
    'GAY5': '5-stripe gay man',
    'BI3': 'bisexual (mini)',
    'BI5': 'bisexual (full)',
    'PAN': 'pansexual',
    'TRANS3': '3-stripe transgender',
    'TRANS5': '5-stripe transgender',
    'GQUEER': 'genderqueer',
    'GFLUID': 'genderfluid',
    'ENBY': 'nonbinary',
    'INTSEX': 'intersex',
    'AROACE': 'aroace',
    'ACE4': 'asexual',
    'ACE6': 'asexual (ace in grace)',
    'ARO': 'aromantic',
    'CETERO4': 'ceterosexual',
    'CETERO5': 'ceterosexual (alt)',
    'MAV': 'maverique',
    'AGEND': 'agender',
    'BIGEND': 'bigender',
    'ANGY': 'androgyne',
    'GNEUT': 'genderneutral',
    'TROIS': 'neutrois',
    'OMNIS': 'omnisexual',
    'MULTG': 'multigender',
    'MULTS': 'multisexual',
    'POLYG': 'polygender',
    'POLYS': 'polysexual',
    'BERRI': 'berrisexual',
    'ALMD': 'almondsexual',
    'ABRO': 'abrosexual',
    'QPR': 'queer-platonic relationships',
    'GAYBO': 'gaybian',
    'GFLUX': 'genderflux',
    'ANDRO': 'androsexual',
    'GYNE': 'gynesexual',
    'USA': 'American flag',
    
    # == Findings ==
    'LV': 'leverback earring',
    'WR': 'French wire earring',
    'BP': '4mm ball post stud earring',
}

# Element variants for AETHER
AETHER_ELEMENTS = ['ANEMO', 'GEO', 'ELECTRO', 'DENDRO', 'HYDRO', 'PYRO', 'CRYO', 'NONE', 'ALL']

# Special designs without bead prefix
SPECIAL_DESIGNS = {
    'HOWLS': "Howl's moving castle",
    'KYO-RED': 'Kyo Soma (red)',
    'KYO-BLACK': 'Kyo Soma (black)',
    'SEASONS-WINTER': 'winter cottage-core',
    'SEASONS-SPRING': 'spring cottage-core',
    'SEASONS-SUMMER': 'summer cottage-core',
    'SEASONS-FALL': 'fall cottage-core',
}

TART_VALUES = {'1': 'single', '2': 'pair'}


def parse_sku(sku_input):
    """Parse a SKU string into its components."""
    sku_original = sku_input.strip()
    sku = sku_input.strip().upper()
    
    bead_style = None
    design = None
    finding = None
    chain_length = None
    brace_length = None
    element = None
    
    import re
    
    # == Step 1: Check for special standalone designs ==
    # TART-[n]
    tart_match = re.match(r'^TART-(\d+)$', sku)
    if tart_match:
        n_val = tart_match.group(1)
        return {
            'sku': sku_original,
            'formatted_description': f"Tartaglia cosplay earrings ({TART_VALUES.get(n_val, 'unknown')})",
        }
    
    # HOWLS (may have suffix like NK, WR, etc.)
    howls_match = re.match(r'^HOWLS(?:-(.+))?$', sku)
    if howls_match:
        suffix = howls_match.group(1)
        desc_parts = ["Howl's moving castle"]
        
        if suffix:
            nk_match = re.match(r'NK(\d+)$', suffix)
            if nk_match:
                chain_length = int(nk_match.group(1))
                if chain_length == 0:
                    desc_parts.append('necklace charm with bail only')
                else:
                    desc_parts.append(f'necklace with {chain_length}-inch chain')
            elif suffix in ['LV', 'WR', 'BP']:
                desc_parts.append(SKU_KEY.get(suffix, suffix.lower()))
        
        return {
            'sku': sku_original,
            'formatted_description': ' '.join(desc_parts),
        }
    
    # == Step 2: Check for bead/design prefixes ==
    prefixes = ['AETHER', '4B', '4C', '6P', '8R', 'CHD']
    
    matched_prefix = None
    remainder = None
    
    for prefix in prefixes:
        if sku.startswith(prefix + '-') or sku == prefix:
            matched_prefix = prefix
            remainder = sku[len(prefix):].strip('-')
            break
    
    # CC- pattern (two-part prefix like CC-RW)
    cc_match = re.match(r'^CC-(RW|RWG)-(.+)$', sku)
    if cc_match:
        color = cc_match.group(1)
        remainder = cc_match.group(2)
        matched_prefix = f'CC-{color}'
    elif sku.startswith('CC-'):
        matched_prefix = sku.split('-')[0:2]
    
    if not matched_prefix:
        if sku.startswith('CC-'):
            pass
        else:
            return {'error': f'Could not parse SKU: {sku_original}. Check the SKU format.'}
    
    # == Step 3: Parse AETHER element ==
    if matched_prefix == 'AETHER':
        for elem in AETHER_ELEMENTS:
            if remainder.startswith(elem):
                element = elem.lower()
                remainder = remainder[len(elem):].strip('-')
                break
    
    # == Step 4: Parse remainder for design + specs ==
    if remainder:
        parts = remainder.split('-')
        
        # Check for necklace chain suffix first (NK[n])
        for i, part in enumerate(parts[:]):
            if part is None:  # Skip None values
                continue
            nk_match = re.match(r'NK(\d+)$', part)
            if nk_match:
                chain_length = int(nk_match.group(1))
                parts[i] = None
                break
        
        # Check for bracelet suffix (BRAC[n] or BRAC-e[n])
        for i, part in enumerate(parts[:]):
            if part is None:  # Skip None values
                continue
            br_match = re.match(r'BRAC[-]?e?(\d+(?:\.\d+)?)$', part)
            if br_match:
                brace_length = float(br_match.group(1))
                parts[i] = None
                break
        
        # Find finding (LV/WR/BP) - check last component first
        if not chain_length and not brace_length:
            if parts[-1] in ['LV', 'WR', 'BP']:
                finding = parts[-1]
                parts = parts[:-1]
        
        # Remove None entries
        parts = [p for p in parts if p is not None]
        
        # Join remaining as design
        if parts:
            design = '-'.join(parts)
    
    # == Step 5: Build description ==
    desc_parts = []
    
    # Add bead/design prefix
    if matched_prefix:
        if matched_prefix.startswith('CC-'):
            desc_parts.append(SKU_KEY.get(matched_prefix, matched_prefix).lower())
        elif matched_prefix == 'AETHER':
            base_desc = SKU_KEY.get('AETHER', 'Aether cosplay')
            if element:
                desc_parts.append(f"{base_desc} ({element})")
            else:
                desc_parts.append(base_desc.lower())
        else:
            desc_parts.append(SKU_KEY.get(matched_prefix, f'{matched_prefix} style').lower())
    
    # Add design (flag, color combo, etc.)
    if design:
        design_desc = SKU_KEY.get(design, design.lower())
        desc_parts.append(design_desc)
    
    # Add specs (finding OR chain OR bracelet)
    if finding:
        finding_desc = SKU_KEY.get(finding, finding.lower())
        desc_parts.append(finding_desc)
    
    elif chain_length is not None:
        if chain_length == 0:
            desc_parts.append('necklace charm with bail only')
        else:
            desc_parts.append(f'necklace with {chain_length}-inch chain')
    
    elif brace_length is not None:
        desc_parts.append(f'bracelet ({brace_length}-inch)')
    
    formatted_desc = ' '.join(desc_parts)
    
    return {
        'sku': sku_original,
        'bead_style': matched_prefix,
        'design': design,
        'finding': finding,
        'chain_length': chain_length,
        'brace_length': brace_length,
        'element': element,
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
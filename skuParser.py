# SKU Parser - BRAC Type + CC Color Separation (Draft 4)

SKU_KEY = {
    # == All prefixes (bead styles + special designs) ==
    '4B': '4mm bicone beads',
    '4C': '4mm cube beads',
    '6P': '6mm pearl beads',
    '8R': '8mm round beads',
    'CHD': "children's bracelet kit beads",
    'AETHER': 'Aether cosplay',
    'CC': 'candy cane',
    'HOWLS': "Howl's moving castle",
    'SEASONS-WINTER': 'winter cottage-core',
    'SEASONS-SPRING': 'spring cottage-core',
    'SEASONS-SUMMER': 'summer cottage-core',
    'SEASONS-FALL': 'fall cottage-core',
    'KYO-RED': 'Kyo Soma (red)',
    'KYO-BLACK': 'Kyo Soma (black)',
    
    # == Color codes for CC ==
    'RW': 'red & white',
    'RWG': 'red, white, green',
    
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
    'KRIS': 'Kris Dreemurr inspired',
    
    # == Findings ==
    'LV': 'leverback earring',
    'WR': 'French wire earring',
    'BP': '4mm ball post stud earring',
}

# Element variants for AETHER
AETHER_ELEMENTS = ['ANEMO', 'GEO', 'ELECTRO', 'DENDRO', 'HYDRO', 'PYRO', 'CRYO', 'NONE', 'ALL']

# Color codes for CC
CC_COLORS = ['RW', 'RWG', 'RAINBOW', 'BLACK', 'WHITE', 'GOLD', 'SILVER', 'PINK', 'BLUE']

TART_VALUES = {'1': 'single', '2': 'pair'}

# All valid prefixes ordered from longest to shortest (for correct matching)
PREFIXES = [
    'SEASONS-WINTER', 'SEASONS-SPRING', 'SEASONS-SUMMER', 'SEASONS-FALL',
    'KYO-RED', 'KYO-BLACK',
    'AETHER', 'CC', '4B', '4C', '6P', '8R', 'CHD', 'HOWLS'
]


def parse_sku(sku_input):
    """Parse a SKU string into its components."""
    sku_original = sku_input.strip()
    sku = sku_input.strip().upper()
    
    bead_style = None
    design = None
    finding = None
    chain_length = None
    brace_length = None
    brace_type = None  # 'elastic' or 'chain'
    element = None
    color_code = None
    
    import re
    
    # == Step 1: Check for TART (standalone, no suffixes) ==
    tart_match = re.match(r'^TART-(\d+)$', sku)
    if tart_match:
        n_val = tart_match.group(1)
        return {
            'sku': sku_original,
            'formatted_description': f"Tartaglia cosplay earrings ({TART_VALUES.get(n_val, 'unknown')})",
        }
    
    # == Step 2: Find matching prefix ==
    matched_prefix = None
    remainder = None
    
    for prefix in PREFIXES:
        if sku.startswith(prefix + '-') or sku == prefix:
            matched_prefix = prefix
            remainder = sku[len(prefix):].strip('-')
            break
    
    if not matched_prefix:
        return {'error': f'Could not parse SKU: {sku_original}. Check the SKU format.'}
    
    # == Step 3: Parse AETHER element (only AETHER has this) ==
    if matched_prefix == 'AETHER':
        for elem in AETHER_ELEMENTS:
            if remainder.startswith(elem):
                element = elem.lower()
                remainder = remainder[len(elem):].strip('-')
                break
    
    # == Step 4: Parse CC color (only CC has this) ==
    if matched_prefix == 'CC':
        for color in CC_COLORS:
            if remainder.startswith(color):
                color_code = color
                remainder = remainder[len(color):].strip('-')
                break
    
    # == Step 5: Parse remainder for specs ==
    if remainder:
        # CHECK: Is remainder itself just a finding?
        if remainder in ['LV', 'WR', 'BP']:
            finding = remainder
            parts = []  # No design part
        else:
            # FIRST: Check for BRAC pattern
            br_match = re.match(r'^(.+)-?BRAC[-]?e[-]?(\d+(?:\.\d+)?)$', remainder, re.IGNORECASE)
            if br_match:
                design_part = br_match.group(1)
                brace_length = float(br_match.group(2))
                brace_type = 'elastic'
                parts = [p for p in design_part.split('-') if p]
            else:
                # Check for non-elastic BRAC
                br_match_chain = re.match(r'^(.+)-?BRAC(\d+(?:\.\d+)?)$', remainder)
                if br_match_chain:
                    design_part = br_match_chain.group(1)
                    brace_length = float(br_match_chain.group(2))
                    brace_type = 'chain'
                    parts = [p for p in design_part.split('-') if p]
                else:
                    # Check for NK pattern
                    nk_match = re.match(r'^(.+)-NK(\d+)$', remainder)
                    if nk_match:
                        design_part = nk_match.group(1)
                        chain_length = int(nk_match.group(2))
                        parts = [p for p in design_part.split('-') if p]
                    else:
                        # Check for finding at the end (something-DASH-LV)
                        finding_match = re.match(r'^(.+)-(LV|WR|BP)$', remainder)
                        if finding_match:
                            design_part = finding_match.group(1)
                            finding = finding_match.group(2)
                            parts = [p for p in design_part.split('-') if p]
                        else:
                            # No recognized suffix, entire remainder is design
                            parts = remainder.split('-')
    
    # Join remaining parts as design
    if parts:
        design = '-'.join(parts)
    
    # == Step 6: Build description ==
    desc_parts = []
    
    # Add prefix description
    prefix_desc = SKU_KEY.get(matched_prefix, matched_prefix.lower())
    desc_parts.append(prefix_desc)
    
    # Add design (flag, KRIS, USA, etc.) if present
    if design:
        design_desc = SKU_KEY.get(design, design.lower())
        desc_parts.append(design_desc)
    
    # Add color for CC
    if color_code:
        color_desc = SKU_KEY.get(color_code, color_code.lower())
        desc_parts.append(f"({color_desc})")
    
    # Add element for AETHER
    if element:
        if len(desc_parts) > 0:
            desc_parts[-1] += f' ({element})'
    
    # Add specs (finding OR chain OR bracelet)
    if finding:
        finding_desc = SKU_KEY.get(finding, finding.lower())
        desc_parts.append(finding_desc)
        if matched_prefix != 'AETHER': 
            desc_parts[-1] += f's'
    
    elif chain_length is not None:
        if chain_length == 0:
            desc_parts.append('necklace charm with bail only')
        else:
            desc_parts.append(f'necklace with {chain_length}-inch chain')
    
    elif brace_length is not None:
        if brace_type == 'elastic':
            desc_parts.append(f'elastic bracelet ({brace_length}-inch)')
        else:
            desc_parts.append(f'chain bracelet ({brace_length}-inch)')
    
    formatted_desc = ' '.join(desc_parts)
    
    return {
        'sku': sku_original,
        'bead_style': matched_prefix,
        'design': design,
        'finding': finding,
        'chain_length': chain_length,
        'brace_length': brace_length,
        'brace_type': brace_type,
        'element': element,
        'color_code': color_code,
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
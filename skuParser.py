# SKU Parser - Converts SKUs to human-readable descriptions (Draft 4)

SKU_KEY = {
    # == Bead styles ==
    '4B': '4mm bicone beads',
    '4C': '4mm cube beads',
    '6P': '6mm pearl beads',
    '8R': '8mm round beads',
    'CHD': "children's bracelet kit beads",
    
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
    
    # == Color combos ==
    'KRIS': 'Kris Dreemurr inspired',
    'CC-RW': 'candy cane red & white',
    'CC-RWG': 'candy cane red, white, green',
    
    # == Findings ==
    'LV': 'leverback earring',
    'WR': 'French wire earring',
    'BP': '4mm ball post stud earring',
    
    # == Necklace/bracelet suffixes ==
    'NK0': 'charm with bail only',
}

# Special designs without bead prefix
SPECIAL_DESIGNS = [
    ('HOWLS', "Howl's moving castle"),
    ('KYO-RED', 'Kyo Soma (red)'),
    ('KYO-BLACK', 'Kyo Soma (black)'),
    ('SEASONS-WINTER', 'winter cottage-core'),
    ('SEASONS-SPRING', 'spring cottage-core'),
    ('SEASONS-SUMMER', 'summer cottage-core'),
    ('SEASONS-FALL', 'fall cottage-core'),
]

TART_VALUES = {'1': 'single', '2': 'pair'}
AETHER_ELEMENTS = {'NONE': 'none', 'ALL': 'all', 'ANEMO': 'anemo', 'GEO': 'geo', 
                   'ELECTRO': 'electro', 'DENDRO': 'dendro', 'HYDRO': 'hydro', 
                   'PYRO': 'pyro', 'CRYO': 'cryo'}


def parse_sku(sku_input):
    """Parse a SKU string into its components."""
    sku_original = sku_input.strip()
    sku = sku_input.strip().upper()
    
    bead_style = None
    design = None
    design_desc = None
    finding = None
    finding_desc = None
    numeric_suffix = None
    element_suffix = None
    
    # == Step 1: Check for bead prefix ==
    bead_prefixes = ['4B', '4C', '6P', '8R', 'CHD']
    
    for prefix in bead_prefixes:
        if sku.startswith(prefix + '-') or sku == prefix:
            bead_style = prefix
            remainder = sku[len(prefix):].strip('-')
            break
    
    if bead_style:
        # == Step 2: Parse remaining parts (Design-Finding or Design-Finding-Suffix) ==
        parts = remainder.split('-')
        
        # Work backwards to find finding first
        finding = None
        if parts[-1] in ['LV', 'WR', 'BP']:
            finding = parts[-1]
            finding_desc = SKU_KEY.get(finding, finding)
            parts = parts[:-1]
        
        # Check for necklace/bracelet suffix
        chain_len = None
        brace_len = None
        for i, part in enumerate(parts):
            import re
            nk_match = re.match(r'NK(\d+)$', part)
            if nk_match:
                chain_len = int(nk_match.group(1))
                numeric_suffix = ('chain_length', chain_len)
                parts[i] = None
                continue
            
            br_match = re.match(r'BRAC\-?e?(\d+(?:\.\d+)?)$', part)
            if br_match:
                brace_len = float(br_match.group(1))
                numeric_suffix = ('bracelet_length', brace_len)
                parts[i] = None
                continue
        
        parts = [p for p in parts if p is not None]
        
        # Remaining part should be the design/flag
        if parts:
            design = '-'.join(parts)
            design_desc = SKU_KEY.get(design, design)
    
    else:
        # == Step 3: Check for special designs (no bead prefix) ==
        for code, desc in SPECIAL_DESIGNS:
            if sku.startswith(code):
                design = code
                design_desc = desc
                remainder = sku[len(code):].strip('-')
                
                # Parse any finding or suffix from remainder
                if remainder:
                    parts = remainder.split('-')
                    
                    # Check for finding
                    if parts[-1] in ['LV', 'WR', 'BP']:
                        finding = parts[-1]
                        finding_desc = SKU_KEY.get(finding, finding)
                        parts = parts[:-1]
                    
                    # Check for necklace suffix
                    if parts:
                        for part in parts:
                            import re
                            nk_match = re.match(r'NK(\d+)$', part)
                            if nk_match:
                                chain_len = int(nk_match.group(1))
                                numeric_suffix = ('chain_length', chain_len)
                                break
        
        # Check for TART
        if sku.startswith('TART'):
            import re
            tart_match = re.match(r'TART-(\d+)$', sku)
            if tart_match:
                design = 'TART-' + tart_match.group(1)
                design_desc = f"Tartaglia cosplay ({TART_VALUES.get(tart_match.group(1), 'unknown')})"
        
        # Check for AETHER
        if sku.startswith('AETHER'):
            import re
            aether_match = re.match(r'AETHER-([A-Z]+)$', sku)
            if aether_match:
                element = aether_match.group(1)
                element_suffix = element.lower()
                design = 'AETHER-' + element
                design_desc = f"Aether cosplay ({element_suffix})"
                
                # Check if there's a finding after
                remainder = sku[aether_match.end():].strip('-')
                if remainder and remainder in ['LV', 'WR', 'BP']:
                    finding = remainder
                    finding_desc = SKU_KEY.get(finding, finding)
    
    if not design and not bead_style:
        return {'error': f'Could not parse SKU: {sku_original}. Check the SKU format.'}
    
    # == Step 4: Build description ==
    description_parts = []
    
    if bead_style:
        description_parts.append(SKU_KEY.get(bead_style, f'{bead_style} style'))
    
    if design_desc:
        description_parts.append(design_desc.lower())
    
    if finding_desc:
        # Insert chain info inline for necklaces
        if numeric_suffix and numeric_suffix[0] == 'chain_length':
            chain_val = numeric_suffix[1]
            if chain_val == 0:
                description_parts.append('charm with bail only')
            else:
                description_parts[-1] += f' with {chain_val}-inch chain'
        else:
            description_parts.append(finding_desc)
    elif numeric_suffix:
        suffix_type, value = numeric_suffix
        if suffix_type == 'bracelet_length':
            if design_desc:
                description_parts[-1] += f' bracelet ({value}-inch)'
            else:
                description_parts.append(f'bracelet ({value}-inch)')
    
    formatted_desc = ' '.join(description_parts)
    
    return {
        'sku': sku_original,
        'bead_style': bead_style,
        'bead_style_desc': SKU_KEY.get(bead_style) if bead_style else None,
        'design': design,
        'design_desc': design_desc,
        'finding': finding,
        'finding_desc': finding_desc,
        'numeric_suffix': numeric_suffix,
        'element_suffix': element_suffix,
        'formatted_description': formatted_desc
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
            
            if result.get('element_suffix'):
                print(f"   Element: {result['element_suffix']}")
            
            print()


if __name__ == "__main__":
    main()
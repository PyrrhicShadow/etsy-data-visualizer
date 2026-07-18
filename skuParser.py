# SKU Parser - Converts SKUs to human-readable descriptions

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
    'PROGPRIDE': 'progress pride',
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
    'KRIS': 'Kris Dreemurr colored',
    'CC-RW': 'candy cane red & white',
    'CC-RWG': 'candy cane red, white, green',
    
    # == Special designs (no bead prefix) ==
    'HOWLS': "Howl's moving castle",
    'KYO-RED': 'Kyo Soma (red)',
    'KYO-BLACK': 'Kyo Soma (black)',
    'SEASONS-winter': 'winter cottage-core',
    'SEASONS-spring': 'spring cottage-core',
    'SEASONS-summer': 'summer cottage-core',
    'SEASONS-fall': 'fall cottage-core',
    
    # == Findings ==
    'LV': 'leverback earrings',
    'WR': 'French wire earrings',
    'BP': '4mm ball post stud earrings',
}

def parse_sku(sku):
    """Parse a SKU string into its components."""
    sku = sku.strip().upper()
    
    # Extract numeric suffixes for variants
    numeric_suffix = None
    element_suffix = None
    
    # Handle NK[n] - extract number
    if 'NK' in sku:
        import re
        match = re.search(r'NK(\d+)$', sku, re.IGNORECASE)
        if match:
            numeric_suffix = ('chain_length', int(match.group(1)))
            sku = sku[:-len(match.group(0))]
    
    # Handle BRAC[n] - extract number
    elif 'BRAC' in sku:
        import re
        match = re.search(r'BRAC\-?e?(\d+(?:\.\d+)?)$', sku, re.IGNORECASE)
        if match:
            numeric_suffix = ('bracelet_length', float(match.group(1)))
            sku = sku[:-len(match.group(0))]
    
    # Handle TART-[n] - extract number
    if 'TART' in sku:
        import re
        match = re.search(r'TART\-?(\d+)$', sku, re.IGNORECASE)
        if match:
            numeric_suffix = ('tartaglia_pair', int(match.group(1)))
            sku = sku.replace(match.group(0), '')
    
    # Handle AETHER[element] - extract element
    if 'AETHER' in sku:
        import re
        match = re.search(r'AETHER\-?([A-Z]+)$', sku, re.IGNORECASE)
        if match:
            element_suffix = match.group(1).lower()
            sku = sku.replace(match.group(0), '')
    
    # Clean up SKU for matching
    sku_clean = sku.strip('-').upper()
    
    # == Parsing Logic ==
    
    # Check for standard format: [BeadStyle]-[Design]-[Finding]
    bead_prefixes = ['4B', '4C', '6P', '8R', 'CHD']
    
    for prefix in bead_prefixes:
        if sku_clean.startswith(prefix + '-') or sku_clean == prefix:
            parts = sku_clean.split('-')
            if len(parts) >= 2:
                bead_style = parts[0]
                remaining = '-'.join(parts[1:])
                
                # Try to match finding first (last component)
                finding = None
                for f in ['LV', 'WR', 'BP']:
                    if remaining.endswith(f):
                        finding = f
                        remaining = remaining[:-len(f)].rstrip('-')
                        break
                
                # Now remaining should be the design/flag
                design = remaining.upper()
                
                # Build description
                bead_desc = SKU_KEY.get(bead_style, f'{bead_style} beads')
                design_desc = SKU_KEY.get(design, design.lower())
                finding_desc = SKU_KEY.get(finding, finding.lower()) if finding else ''
                
                return {
                    'sku': sku,
                    'bead_style': bead_desc,
                    'design': design_desc,
                    'finding': finding_desc,
                    'numeric_suffix': numeric_suffix,
                    'element_suffix': element_suffix,
                    'formatted_description': format_description(bead_style, design, finding, numeric_suffix, element_suffix)
                }
    
    # Check for special designs (no bead prefix)
    special_designs = ['HOWLS', 'TART', 'KYO-RED', 'KYO-BLACK', 'SEASONS-WINTER', 
                       'SEASONS-SPRING', 'SEASONS-SUMMER', 'SEASONS-FALL']
    
    for design in special_designs:
        if sku_clean.startswith(design):
            remaining = sku_clean[len(design):].strip('-')
            finding = None
            for f in ['LV', 'WR', 'BP']:
                if remaining.endswith(f):
                    finding = f
                    remaining = remaining[:-len(f)].strip('-')
                    break
            
            design_desc = SKU_KEY.get(design, design.lower())
            finding_desc = SKU_KEY.get(finding, finding.lower()) if finding else ''
            
            return {
                'sku': sku,
                'bead_style': None,
                'design': design_desc,
                'finding': finding_desc,
                'numeric_suffix': numeric_suffix,
                'element_suffix': element_suffix,
                'formatted_description': format_special_design(design, finding, numeric_suffix, element_suffix)
            }
    
    return {'error': f'Could not parse SKU: {sku}. Check the SKU format.'}


def format_description(bead_style, design, finding, numeric_suffix, element_suffix):
    """Build a human-readable description."""
    parts = []
    
    if bead_style:
        parts.append(SKU_KEY.get(bead_style, f'{bead_style} style'))
    
    if design:
        parts.append(design)
    
    if element_suffix:
        parts.append(f'{element_suffix} element')
    
    if finding:
        finding_map = {
            'LV': 'leverback earring',
            'WR': 'wire earring',
            'BP': 'stud earring'
        }
        parts.append(finding_map.get(finding, finding))
        
        # Convert to singular form for readability
        if numeric_suffix:
            suffix_type, value = numeric_suffix
            
            if suffix_type == 'chain_length':
                parts[-1] += ' with {}-inch chain'.format(value)
            elif suffix_type == 'bracelet_length':
                # Remove 'earring' and add bracelet info
                parts[-2] = f"{parts[-2]} bracelet ({value}-inch)"
                parts.pop(-1)  # Remove the finding descriptor
    
    return ' '.join(parts).replace('  ', ' ').strip()


def format_special_design(design, finding, numeric_suffix, element_suffix):
    """Build description for special designs without bead prefix."""
    parts = [SKU_KEY.get(design, design)]
    
    if element_suffix:
        parts.append(f'{element_suffix} element')
    
    if finding:
        finding_map = {
            'LV': 'leverback earring',
            'WR': 'wire earring',
            'BP': 'stud earring'
        }
        parts.append(finding_map.get(finding, finding))
        
        if numeric_suffix:
            suffix_type, value = numeric_suffix
            if suffix_type == 'chain_length':
                parts[-1] += ' with {}-inch chain'.format(value)
    
    return ' '.join(parts).replace('  ', ' ').strip()


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
            print(f"   Description: {result['formatted_description']}")
            
            if result.get('numeric_suffix'):
                suffix_type, value = result['numeric_suffix']
                print(f"   Numeric: {suffix_type} = {value}")
            
            if result.get('element_suffix'):
                print(f"   Element: {result['element_suffix']}")
            
            print()


if __name__ == "__main__":
    main()
import re
from collections import defaultdict

def main():
    with open('ISSUES.md', 'r', encoding='utf-8') as f:
        content = f.read()

    issues = re.findall(r'>> Issue: \[([^\]]+)\](.*?)\n   Location: ([^\n]+)', content, re.DOTALL)
    grouped = defaultdict(list)
    for code_name, desc, loc in issues:
        loc = loc.strip()
        code = code_name.split(':')[0]
        grouped[code].append((loc, desc.strip()))

    for code, locs in grouped.items():
        print(f'\n--- {code} ---')
        for loc, desc in locs:
            print(f'{loc} - {desc}')

if __name__ == "__main__":
    main()

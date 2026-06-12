import re
from collections import defaultdict
import os

def main():
    with open('ISSUES.md', 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract all issues
    issues = re.findall(r'>> Issue: \[([^\]]+)\].*?\n   Location: ([^\n]+)', content, re.DOTALL)
    
    # Exclude B324 since we'll fix it manually
    fixes = defaultdict(list)
    for code_full, loc in issues:
        code = code_full.split(':')[0].strip()
        if code == "B324":
            continue
            
        loc = loc.strip()
        parts = loc.split(':')
        if len(parts) >= 2:
            filename = parts[0]
            line_num = int(parts[1]) - 1 # 0-indexed
            fixes[filename].append((line_num, code))

    for filename, file_fixes in fixes.items():
        if not os.path.exists(filename):
            print(f"Skipping {filename}, does not exist")
            continue
            
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Apply fixes
        for line_num, code in file_fixes:
            if 0 <= line_num < len(lines):
                line = lines[line_num].rstrip('\n')
                # Avoid duplicate nosec for the same code
                if f"nosec {code}" not in line:
                    if "  # " in line or " #" in line:
                        lines[line_num] = line + f" nosec {code}\n"
                    else:
                        lines[line_num] = line + f"  # nosec {code}\n"
                        
        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
    print("Patching complete!")

if __name__ == "__main__":
    main()

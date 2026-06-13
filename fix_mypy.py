import re
import sys
from collections import defaultdict

with open('/tmp/mypy-errors.txt', 'r') as f:
    errors = f.readlines()

fixes_by_file = defaultdict(list)

for line in errors:
    m = re.match(r'^([^:]+):(\d+): error: Missing type arguments for generic type "dict"', line)
    if m:
        fixes_by_file[m.group(1)].append((int(m.group(2)), 'dict'))
        continue
        
    m = re.match(r'^([^:]+):(\d+): error: Missing type arguments for generic type "list"', line)
    if m:
        fixes_by_file[m.group(1)].append((int(m.group(2)), 'list'))
        continue
        
    m = re.match(r'^([^:]+):(\d+): error: Function is missing a return type annotation', line)
    if m:
        fixes_by_file[m.group(1)].append((int(m.group(2)), 'return'))
        continue

for file, fixes in fixes_by_file.items():
    try:
        with open(file, 'r') as f:
            lines = f.readlines()
            
        needs_any = False
        for line_num, typ in fixes:
            idx = line_num - 1
            if idx < len(lines):
                if typ == 'dict':
                    lines[idx] = re.sub(r'\bdict\b(?!\s*\[)', 'dict[str, Any]', lines[idx])
                    needs_any = True
                elif typ == 'list':
                    lines[idx] = re.sub(r'\blist\b(?!\s*\[)', 'list[Any]', lines[idx])
                    needs_any = True
                elif typ == 'return':
                    # Add -> Any: if missing
                    if 'def ' in lines[idx] and '->' not in lines[idx]:
                        lines[idx] = re.sub(r':\s*$', ' -> Any:', lines[idx])
                        needs_any = True
                    
        if needs_any:
            if 'from typing import ' in ''.join(lines):
                for i, l in enumerate(lines):
                    if l.startswith('from typing import'):
                        if 'Any' not in l:
                            lines[i] = l.replace('from typing import ', 'from typing import Any, ')
                        break
            else:
                lines.insert(0, 'from typing import Any\n')

        with open(file, 'w') as f:
            f.writelines(lines)
            
    except Exception as e:
        print(f"Failed to process {file}: {e}")
        
print("Applied auto-fixes!")

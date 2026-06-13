"""Fix lines where '-> Any:        \"\"\"' got merged onto one line by the auto-fix script."""
import re
import pathlib

root = pathlib.Path("src")
pattern = re.compile(r'^(\s*(?:async\s+)?def\s+\S+\(.*?\)\s*->\s*Any:)\s{2,}(""".*)')

fixed_total = 0
for pyfile in root.rglob("*.py"):
    text = pyfile.read_text()
    lines = text.split("\n")
    changed = False
    new_lines = []
    for line in lines:
        m = pattern.match(line)
        if m:
            sig = m.group(1)
            docstring = m.group(2)
            # Compute indentation of the def line, add 4 spaces for body
            indent = len(sig) - len(sig.lstrip()) + 4
            new_lines.append(sig)
            new_lines.append(" " * indent + docstring)
            changed = True
            fixed_total += 1
        else:
            new_lines.append(line)
    if changed:
        pyfile.write_text("\n".join(new_lines))
        print(f"  Fixed {pyfile}")

print(f"\nTotal lines fixed: {fixed_total}")

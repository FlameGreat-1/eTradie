import os
import glob

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Simple string replacements
    new_content = content.replace('v.upper().replace', 'v.replace')
    new_content = new_content.replace('symbol.upper().replace', 'symbol.replace')
    new_content = new_content.replace('raw.upper().replace', 'raw.replace')
    
    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)
        print(f"Updated {filepath}")

def main():
    search_dirs = [
        "src/engine/ta/models",
        "src/engine/shared/models",
        "src/engine/rag/retrieval",
        "src/engine/ta/common/utils/price"
    ]
    
    for d in search_dirs:
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith('.py'):
                    process_file(os.path.join(root, file))

if __name__ == "__main__":
    main()

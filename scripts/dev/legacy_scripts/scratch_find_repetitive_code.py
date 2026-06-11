import subprocess
import re

def main():
    # Get modified files list from git status
    output = subprocess.check_output(["git", "status", "--porcelain"]).decode("utf-8")
    modified_files = []
    for line in output.splitlines():
        if line.startswith(" M") or line.startswith("M "):
            file_path = line[3:].strip()
            modified_files.append(file_path)
            
    print(f"Checking {len(modified_files)} modified files...")
    
    for file_path in modified_files:
        if not file_path.endswith(('.py', '.tsx', '.ts', '.js', '.dart')):
            continue
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()
        except Exception as e:
            print(f"Could not read {file_path}: {e}")
            continue
            
        # Find consecutive duplicate lines or blocks
        # Let's check for repeated functions or blocks of 5+ lines
        print(f"\n--- Analyzing {file_path} ---")
        
        # Simple sliding window check for identical blocks of 5+ lines
        block_size = 6
        seen_blocks = {}
        duplicates_found = 0
        
        for i in range(len(lines) - block_size + 1):
            block = tuple(lines[i:i+block_size])
            # Filter out empty blocks or blocks of only curly braces/comments
            is_trivial = all(not line.strip() or line.strip() in ("}", "{", ");", "],", "},", "const", "return", "import") for line in block)
            if is_trivial:
                continue
                
            block_str = "\n".join(block)
            if block in seen_blocks:
                first_occurrence = seen_blocks[block]
                if i >= first_occurrence + block_size:
                    print(f"Potential duplicate block found (lines {first_occurrence+1}-{first_occurrence+block_size} and lines {i+1}-{i+block_size}):")
                    print("```")
                    print("\n".join(lines[i:i+3]) + "\n...")
                    print("```")
                    duplicates_found += 1
            else:
                seen_blocks[block] = i
                
        if duplicates_found == 0:
            print("No significant duplicate blocks found.")

if __name__ == "__main__":
    main()

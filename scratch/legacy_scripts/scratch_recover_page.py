import json
import re

log_path = "/Users/segun/.gemini/antigravity/brain/d3b13dad-92eb-45e6-a12e-1fcb2c541d07/.system_generated/logs/transcript.jsonl"
out_path = "/Users/segun/Documents/Verifield nexus/dashboard/src/app/dashboard/page.tsx"

lines_dict = {}

with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        try:
            step = json.loads(line)
        except Exception as e:
            continue
        
        # Check if this is a VIEW_FILE step of dashboard/src/app/dashboard/page.tsx
        tool_calls = step.get("tool_calls", [])
        is_page_view = False
        
        # In SYSTEM/MODEL response, we can also look at the content
        content = step.get("content", "")
        if "File Path: `file:///Users/segun/Documents/Verifield%20nexus/dashboard/src/app/dashboard/page.tsx`" in content:
            is_page_view = True
        
        if is_page_view:
            # Extract lines from content
            # The code is usually in the format: <line_number>: <original_line>
            pattern = re.compile(r"^(\d+): (.*)$")
            for cl in content.split("\n"):
                m = pattern.match(cl.strip())
                if m:
                    line_num = int(m.group(1))
                    line_content = m.group(2)
                    lines_dict[line_num] = line_content

print(f"Extracted {len(lines_dict)} lines from the logs.")

if len(lines_dict) > 0:
    max_line = max(lines_dict.keys())
    print(f"Max line number: {max_line}")
    
    # Write to page.tsx
    with open(out_path, "w", encoding="utf-8") as out:
        for i in range(1, max_line + 1):
            # Fallback if a line was missing
            out.write(lines_dict.get(i, "") + "\n")
    print("Successfully recovered page.tsx!")
else:
    print("No lines extracted.")

#!/usr/bin/env python3
"""Fix f-string syntax errors in nvidia_api.py"""
import re

with open('app/api/nvidia_api.py', 'r') as f:
    lines = f.readlines()

# Track which lines need fixing
fixed_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # Check for problematic f-strings with backslashes in json.dumps
    if "f\"data: {json.dumps(" in line and ("'\\n" in line or '"\\n' in line):
        # Extract the line and the next few lines if needed
        # Pattern: yield f"data: {json.dumps({'type': 'content', 'content': '\n\n' + var})}\n\n"
        
        # Try to find and replace '\n\n' + variable patterns
        if "'\n\n' +" in line:
            # Replace '\n\n' + var with a variable assignment
            match = re.search(r"'\n\n' \+ (\w+)", line)
            if match:
                var_name = match.group(1)
                # Get indentation
                indent = len(line) - len(line.lstrip())
                indent_str = " " * indent
                
                # Create variable assignment
                var_assign = f"{indent_str}content_with_sep = '\\n\\n' + {var_name}\n"
                fixed_lines.append(var_assign)
                
                # Replace in current line
                new_line = line.replace("'\\n\\n' + " + var_name, "content_with_sep")
                fixed_lines.append(new_line)
                i += 1
                continue
    
    fixed_lines.append(line)
    i += 1

with open('app/api/nvidia_api.py', 'w') as f:
    f.writelines(fixed_lines)

print("✅ Fixed f-string issues")

# Verify syntax
import ast
with open('app/api/nvidia_api.py', 'r') as f:
    try:
        ast.parse(f.read())
        print("✅ File is syntactically valid")
    except SyntaxError as e:
        print(f"❌ Still has errors at line {e.lineno}: {e.msg}")

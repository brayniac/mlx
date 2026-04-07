"""Fix MLX Metal JIT preamble for Xcode 26 compatibility.

Targeted fixes:
1. Remove complex64_t sections (complex.h, cexpf.h)
2. Remove complex64_t functions from other headers
3. Strip bfloat16 math re-definitions (conflict with Xcode 26 builtins)
4. Remove #if !defined(MLX_METAL_JIT) guarded blocks
"""
import re
import sys

text = sys.stdin.read()

# 1. Remove #if !defined(MLX_METAL_JIT) ... #endif blocks
text = re.sub(
    r'#if !defined\(MLX_METAL_JIT\).*?#endif[^\n]*\n',
    '', text, flags=re.DOTALL)

# 2. Remove entire complex.h section
text = re.sub(
    r'///+\n// Contents from "mlx/backend/metal/kernels/complex\.h"\n///+\n'
    r'.*?'
    r'(?=///+\n// Contents from )',
    '', text, flags=re.DOTALL)

# 3. Remove entire cexpf.h section
text = re.sub(
    r'///+\n// Contents from "mlx/backend/metal/kernels/cexpf\.h"\n///+\n'
    r'.*?'
    r'(?=///+\n// Contents from )',
    '', text, flags=re.DOTALL)

# 4. Remove lines containing complex64_t (individual functions/declarations)
lines = text.split('\n')
result = []
brace_depth = 0
skipping = False

i = 0
while i < len(lines):
    line = lines[i]
    
    if skipping:
        brace_depth += line.count('{') - line.count('}')
        if brace_depth <= 0:
            skipping = False
        i += 1
        continue
    
    if 'complex64_t' in line:
        # Check if this starts a function body
        if '{' in line:
            brace_depth = line.count('{') - line.count('}')
            if brace_depth > 0:
                skipping = True
            # Also remove preceding template<> lines
            while result and ('template' in result[-1] or 'typename' in result[-1]):
                result.pop()
            i += 1
            continue
        elif line.strip().endswith(';') or line.strip().endswith('{'):
            # Declaration or start of block
            while result and ('template' in result[-1] or 'typename' in result[-1]):
                result.pop()
            i += 1
            continue
        else:
            # Standalone reference — skip line
            i += 1
            continue
    
    result.append(line)
    i += 1

text = '\n'.join(result)

# 5. Strip bfloat16 math re-instantiations that conflict with Xcode 26 builtins
# Remove: instantiate_metal_math_funcs(...); calls (multi-line with args)
text = re.sub(
    r'instantiate_metal_math_funcs\(\s*\n\s*bfloat16_t,\s*\n\s*bfloat16_t,\s*\n\s*float,\s*\n\s*[^)]*\);\s*\n',
    '', text)

sys.stdout.write(text)

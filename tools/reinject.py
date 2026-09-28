"""Paste tools/gen_catalog.js into the page between the // @gen-begin and // @gen-end markers."""
import os
S = os.path.dirname(os.path.abspath(__file__))
f = os.path.join(S, '..', 'Scoop Desktop.dc.html')
s = open(f, encoding='utf-8').read()
gen = open(os.path.join(S, 'gen_catalog.js'), encoding='utf-8').read()
a = s.index('// @gen-begin')
a = s.index('\n', a) + 1
b = s.index('\n// @gen-end')
s = s[:a] + gen + s[b:]
open(f, 'w', encoding='utf-8', newline='').write(s)
print('reinjected', len(gen), 'bytes of catalog')

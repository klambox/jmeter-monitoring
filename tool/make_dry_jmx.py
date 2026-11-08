"""Copy a JMX for a dry run: every enabled Thread Group gets 1 thread, 1 loop and a 1 s ramp-up.

    python make_dry_jmx.py SOURCE.jmx TARGET.jmx

The source file is not touched.
"""
import re
import sys

src, dst = sys.argv[1], sys.argv[2]
text = open(src, encoding='utf-8').read()


def one_each(match):
    tg = match.group(0)
    tg = re.sub(r'(name="LoopController\.loops">)[^<]*(<)', r'\g<1>1\2', tg)
    tg = re.sub(r'(name="ThreadGroup\.num_threads">)[^<]*(<)', r'\g<1>1\2', tg)
    tg = re.sub(r'(name="ThreadGroup\.ramp_time">)[^<]*(<)', r'\g<1>1\2', tg)
    return tg


text, n = re.subn(r'<ThreadGroup [^>]*enabled="true".*?</ThreadGroup>', one_each, text, flags=re.S)
open(dst, 'w', encoding='utf-8', newline='').write(text)
print('dry run copy: %d enabled thread group(s) set to 1 user, 1 loop -> %s' % (n, dst))

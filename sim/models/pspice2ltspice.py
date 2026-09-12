#!/usr/bin/env python3
"""Make a TI unencrypted-PSpice model loadable by LTspice.

    ./pspice2ltspice.py vendor/TPS62827_TRANS.LIB tps62827.lib

LTspice already understands almost all of PSpice's dialect - `.MODEL x VSWITCH`,
`E ... TABLE {} = () ()` and `E ... VALUE { IF(...) }` all work unmodified, and
were verified against this LTspice build before this script was written.

Exactly one construct defeats it. PSpice references a subcircuit parameter
inside a behavioural expression by bracing it, and sometimes braces the whole
expression again on top:

    E_ABMGATE YINT 0 VALUE {{IF(V(A) > {VTHRESH} ,
    + {VDD},{VSS})}}

LTspice turns `VALUE {expr}` into a B-source `V={expr}`, so those inner braces
end up nested inside the outer pair, and it gives up:

    Questionable use of curly braces in "b e_abmgate yint 0 v={if(v(a)>{{vthresh}}..."
        Error: undefined symbol in: "if([v](a)>((vthresh)),((vdd)),((vss)))"

The fix is to strip braces *inside* the outermost pair of a VALUE or TABLE
expression, leaving the outer pair alone. Parameter names resolve fine bare.

Everything else is passed through byte for byte, comments and TI's licence
header included. Continuation lines are joined, because a braced expression
frequently spans them.
"""

import re
import sys


def statements(lines):
    """Join PSpice continuation lines into logical statements."""
    out = []
    for line in lines:
        if line[:1] == "+" and out:
            out[-1] = out[-1].rstrip() + " " + line[1:].strip()
        else:
            out.append(line.rstrip("\n"))
    return out


def strip_inner_braces(stmt):
    """Remove braces nested inside the outermost {...} of a VALUE/TABLE expr."""
    m = re.search(r"\b(VALUE|TABLE)\b\s*\{", stmt, re.I)
    if not m:
        return stmt, False

    start = stmt.index("{", m.end() - 1)
    depth, end = 0, None
    for i in range(start, len(stmt)):
        if stmt[i] == "{":
            depth += 1
        elif stmt[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end is None:                      # unbalanced; leave it for LTspice to report
        return stmt, False

    inner = stmt[start + 1:end]
    if "{" not in inner and "}" not in inner:
        return stmt, False
    return stmt[:start + 1] + inner.replace("{", "").replace("}", "") + stmt[end:], True


def convert(src, dst):
    with open(src, errors="surrogateescape") as f:
        stmts = statements(f.readlines())

    touched = 0
    out = []
    for s in stmts:
        if s.lstrip().startswith("*"):   # comment - never rewrite
            out.append(s)
            continue
        s, changed = strip_inner_braces(s)
        touched += changed
        out.append(s)

    with open(dst, "w", errors="surrogateescape") as f:
        f.write("* Converted for LTspice by sim/models/pspice2ltspice.py\n")
        f.write("* Source: %s - unmodified apart from brace nesting. Do not edit.\n" % src)
        f.write("\n".join(out) + "\n")

    print("%s -> %s  (%d expression(s) rewritten)" % (src, dst, touched))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    convert(sys.argv[1], sys.argv[2])

"""Generate testcases T16-T18 by running compiler.py and saving its output."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMPILER = os.path.join(HERE, "compiler.py")
INPUT = os.path.join(HERE, "input.txt")
TREE = os.path.join(HERE, "parse_tree.txt")
ERRS = os.path.join(HERE, "syntax_errors.txt")

CASES = {
    "T16": """\
/* T16: array init, multi-param function, nested expressions */
int max(int a, int b) {
    if (a < b) {
        return b;
    }
    return a;
}

void main(void) {
    int arr[5];
    int i;
    int result;
    arr[0] = 3;
    arr[1] = 7;
    arr[2] = 2;
    arr[3] = 9;
    arr[4] = 4;
    i = 0;
    result = arr[0];
    while (i < 5) {
        result = max(result, arr[i]);
        i = i + 1;
    }
    return;
}
""",

    "T17": """\
/* T17: syntax errors - missing semicolons and misplaced tokens */
void main(void) {
    int x
    int y;
    x = 5
    y = x + 3;
    if (x < y) {
        x = y;
    }
    return;
}
""",

    "T18": """\
/* T18: switch inside while, break, goto, variable init */
int counter;

void main(void) {
    int x = 0;
    int done = 0;
    counter = 10;
    loop:
    while (x < counter) {
        switch (x) {
            case 3:
                done = 1;
                break;
            case 7:
                counter = counter - 1;
                break;
            default:
                x = x + 1;
        }
        if (done == 1) {
            goto end;
        }
    }
    end:
    return;
}
""",
}


def run(src):
    with open(INPUT, "w") as f:
        f.write(src)
    subprocess.run([sys.executable, COMPILER], cwd=HERE,
                   capture_output=True, text=True)
    tree = open(TREE, encoding="utf-8").read()
    errs = open(ERRS, encoding="utf-8").read()
    return tree, errs


for name, src in CASES.items():
    tc_dir = os.path.join(HERE, "testcases", name)
    os.makedirs(tc_dir, exist_ok=True)

    with open(os.path.join(tc_dir, "input.txt"), "w") as f:
        f.write(src)

    tree, errs = run(src)

    with open(os.path.join(tc_dir, "parse_tree.txt"), "w") as f:
        f.write(tree)
    with open(os.path.join(tc_dir, "syntax_errors.txt"), "w") as f:
        f.write(errs)

    err_summary = errs.strip().splitlines()[0] if errs.strip() else ""
    print(f"Generated {name}: {err_summary}")

print("\nDone. Run the full suite with test_all.py to verify.")

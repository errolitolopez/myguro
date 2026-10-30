"""Finds every message a server error carries in the code: the English sentence, with {name} for each value an
f-string fills in (used by test_i18n_messages.py)."""
import ast, glob, sys

def render(node):
    """A string literal, an f-string, an implicit/explicit concatenation -> 'text with {name}', or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out, used = [], {}
        for part in node.values:
            if isinstance(part, ast.Constant):
                out.append(part.value)
            else:
                expr = part.value
                name = expr.id if isinstance(expr, ast.Name) else (expr.attr if isinstance(expr, ast.Attribute) else "value")
                used[name] = used.get(name, 0) + 1
                out.append("{" + (name if used[name] == 1 else f"{name}{used[name]}") + "}")  # the same name twice must differ
        return "".join(out)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left, right = render(node.left), render(node.right)
        return left + right if left is not None and right is not None else None
    return None

def messages():
    found, dynamic = {}, []
    for path in sorted(glob.glob("myguro/**/*.py", recursive=True)):
        tree = ast.parse(open(path).read())
        for node in ast.walk(tree):
            call = None
            if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
                func = node.exc.func
                name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")
                if name.endswith("Error") and node.exc.args:
                    call = node.exc.args[0]
            elif isinstance(node, ast.Dict):  # {"kind": ..., "message": "..."}: the schedule's problems
                for key, value in zip(node.keys, node.values):
                    if isinstance(key, ast.Constant) and key.value == "message":
                        for branch in ([value.body, value.orelse] if isinstance(value, ast.IfExp) else [value]):
                            text = render(branch)
                            if text is not None:
                                found.setdefault(text, []).append(f"{path}:{node.lineno}")
                continue
            elif isinstance(node, ast.Call) and getattr(node.func, "id", "") in ("fail", "problem") and len(node.args) >= 2:
                call = node.args[1]  # fail(item, message) and problem(where, message) in the Word import
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "error_response" or getattr(func, "attr", "") == "error_response":
                    pass
                for kw in node.keywords:
                    if kw.arg == "error" and isinstance(func, (ast.Name, ast.Attribute)) and getattr(func, "id", getattr(func, "attr", "")) == "jsonify":
                        call = kw.value
            if call is None:
                continue
            branches = [call.body, call.orelse] if isinstance(call, ast.IfExp) else [call]
            for branch in branches:
                text = render(branch)
                if text is None:
                    dynamic.append((path, node.lineno, ast.unparse(branch)[:80]))
                else:
                    found.setdefault(text, []).append(f"{path}:{node.lineno}")
    return found, dynamic

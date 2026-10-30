"""Finds every message a server error carries in the code: the English sentence, with {name} for each value an
f-string fills in (used by test_i18n_messages.py)."""
import ast, glob, sys

def render(node):
    """A string literal, an f-string, an implicit/explicit concatenation -> 'text with {name}', or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out = []
        for part in node.values:
            if isinstance(part, ast.Constant):
                out.append(part.value)
            else:
                expr = part.value
                name = expr.id if isinstance(expr, ast.Name) else (expr.attr if isinstance(expr, ast.Attribute) else "value")
                out.append("{" + name + "}")
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
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "error_response" or getattr(func, "attr", "") == "error_response":
                    pass
                for kw in node.keywords:
                    if kw.arg == "error" and isinstance(func, (ast.Name, ast.Attribute)) and getattr(func, "id", getattr(func, "attr", "")) == "jsonify":
                        call = kw.value
            if call is None:
                continue
            text = render(call)
            if text is None:
                dynamic.append((path, node.lineno, ast.unparse(call)[:80]))
            else:
                found.setdefault(text, []).append(f"{path}:{node.lineno}")
    return found, dynamic

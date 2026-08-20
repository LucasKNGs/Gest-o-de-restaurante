from pathlib import Path

root = Path("app")

replacements = {
    "const f=new FormData(e.currentTarget);":
        "const form=e.currentTarget;const f=new FormData(form);",

    "e.currentTarget.reset();":
        "form.reset();",

    "const f=new FormData(ev.currentTarget);":
        "const form=ev.currentTarget;const f=new FormData(form);",

    "ev.currentTarget.reset();":
        "form.reset();",
}

changed = []

for path in root.rglob("*.tsx"):
    text = path.read_text(encoding="utf-8")
    original = text

    for old, new in replacements.items():
        text = text.replace(old, new)

    if text != original:
        path.write_text(text, encoding="utf-8")
        changed.append(str(path))

print("Arquivos corrigidos:")
for path in changed:
    print(" -", path)

print(f"\nTotal: {len(changed)} arquivos.")

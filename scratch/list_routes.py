with open("d:/TFG/src/audit_salarial_app/admin/routes.py", "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if "AUDITOR" in line or "auditor" in line:
            print(f"Line {i+1}: {line.strip()}")

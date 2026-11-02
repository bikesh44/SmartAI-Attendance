from app import create_app

app = create_app()

print("\n===== REGISTERED API ENDPOINTS =====")
for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
    methods = sorted(rule.methods - {"HEAD", "OPTIONS"})
    print(f"{','.join(methods):18} {rule.rule}  [{rule.endpoint}]")

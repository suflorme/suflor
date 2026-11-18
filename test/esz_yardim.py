# Bölüm dosyalarını (aktarici/*.py) kendi küçük ad alanında çalıştıran testler için: relay.py'deki geçici-dosya yardımcıları (gecici_ad, dosya_yaz_esz).
# Gerçekte bölümler relay.py'nin ad alanında çalışır; bu testlerde ad alanı elle kurulduğu için yardımcılar ESZ sözlüğüyle eklenir: ns = {**ESZ, ...}
import ast, json, os, threading
_KOD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "relay.py")
_agac = ast.parse(open(_KOD, encoding="utf-8").read())
_g = {"os": os, "json": json, "threading": threading}
exec(compile(ast.Module([n for n in _agac.body if isinstance(n, ast.FunctionDef) and n.name in ("gecici_ad", "dosya_yaz_esz")], []), _KOD, "exec"), _g)
ESZ = {"gecici_ad": _g["gecici_ad"], "dosya_yaz_esz": _g["dosya_yaz_esz"]}

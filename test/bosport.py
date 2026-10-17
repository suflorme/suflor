# Test portu: istenen port boşsa o, doluysa (başka test ya da süreç tutuyorsa) işletim sisteminin verdiği boş port.
# Kullanım (önbellek dosyası yazmadan; klasörde _ ile başlayan klasör olmaz):
#   sys.dont_write_bytecode = True; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); from bosport import bos_port
#   PORT = bos_port(8793)
import socket
_verilen = set()
def bos_port(tercih=0):
    for p in (tercih, 0):
        if p and p in _verilen: continue
        s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try: s.bind(("127.0.0.1", p)); p = s.getsockname()[1]
        except OSError: continue
        finally: s.close()
        _verilen.add(p); return p
    raise OSError("boş port bulunamadı")

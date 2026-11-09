#!/usr/bin/env python3
"""Lee/escribe valores del storage.local de una extension de Firefox/LibreWolf
(IndexedDB: valores = structured clone comprimido con snappy "raw").
Soporta null/bool/int/double/string/objetos/arrays.
El navegador TIENE que estar cerrado para escribir.

  moz_ext_storage.py DB dump
  moz_ext_storage.py DB get KEY
  moz_ext_storage.py DB set-str KEY FILE      (contenido del archivo)
  moz_ext_storage.py DB set-bool KEY true|false
  moz_ext_storage.py DB set-json KEY FILE.json
"""
import json, sqlite3, struct, sys

# ---------- snappy raw ----------
def _varint(b, i):
    r = s = 0
    while True:
        c = b[i]; i += 1
        r |= (c & 0x7F) << s; s += 7
        if c < 0x80: return r, i

def snappy_decompress(b):
    n, i = _varint(b, 0)
    out = bytearray()
    while i < len(b):
        t = b[i]; i += 1
        kind = t & 3
        if kind == 0:  # literal
            ln = t >> 2
            if ln >= 60:
                nb = ln - 59; ln = int.from_bytes(b[i:i+nb], 'little'); i += nb
            ln += 1
            out += b[i:i+ln]; i += ln
            continue
        if kind == 1:
            ln = ((t >> 2) & 7) + 4; off = ((t >> 5) << 8) | b[i]; i += 1
        elif kind == 2:
            ln = (t >> 2) + 1; off = int.from_bytes(b[i:i+2], 'little'); i += 2
        else:
            ln = (t >> 2) + 1; off = int.from_bytes(b[i:i+4], 'little'); i += 4
        for _ in range(ln): out.append(out[-off])
    assert len(out) == n, (len(out), n)
    return bytes(out)

def snappy_compress(b):  # solo literales: stream valido, sin comprimir
    out = bytearray(); n = len(b)
    while True:
        c = n & 0x7F; n >>= 7
        out.append(c | (0x80 if n else 0))
        if not n: break
    for i in range(0, len(b), 65536):
        chunk = b[i:i+65536]; ln = len(chunk) - 1
        if ln < 60: out.append(ln << 2)
        elif ln < 256: out += bytes([60 << 2, ln])
        else: out += bytes([61 << 2]) + ln.to_bytes(2, 'little')
        out += chunk
    return bytes(out)

# ---------- structured clone (subset: null/bool/int/double/string/object/array) ----------
T_HEADER, T_NULL, T_UNDEF, T_BOOL, T_INT, T_STRING = 0xFFF10000, 0xFFFF0000, 0xFFFF0001, 0xFFFF0002, 0xFFFF0003, 0xFFFF0004
T_ARRAY, T_OBJECT, T_END = 0xFFFF0007, 0xFFFF0008, 0xFFFF0013

def sc_decode(raw):
    pos = [0]
    def pair():
        d, t = struct.unpack_from('<II', raw, pos[0]); pos[0] += 8; return d, t
    def string(d):
        ln, latin1 = d & 0x7FFFFFFF, d >> 31
        nb = ln if latin1 else 2 * ln
        b = raw[pos[0]:pos[0] + nb]; pos[0] += nb + (-nb % 8)
        return b.decode('latin1' if latin1 else 'utf-16-le')
    def value():
        start = pos[0]; d, t = pair()
        if t == T_HEADER: return value()
        if t == T_NULL: return None
        if t == T_UNDEF: return None
        if t == T_BOOL: return bool(d)
        if t == T_INT: return struct.unpack('<i', struct.pack('<I', d))[0]
        if t == T_STRING: return string(d)
        if t in (T_OBJECT, T_ARRAY):
            out = {}
            while True:
                kd, kt = pair()
                if kt == T_END: break
                k = string(kd) if kt == T_STRING else (struct.unpack('<i', struct.pack('<I', kd))[0] if kt == T_INT else f'?{kt:#x}')
                out[k] = value()
            return [out[i] for i in sorted(out)] if t == T_ARRAY else out
        if t < 0xFFF00000:  # double
            return struct.unpack_from('<d', raw, start)[0]
        raise ValueError(f'tag no soportado {t:#x}')
    return value()

def _hdr():
    return struct.pack('<II', 0, T_HEADER)

def _p(d, t): return struct.pack('<II', d & 0xFFFFFFFF, t)

def _str(s):
    try:
        enc = s.encode('latin1'); flag = 1 << 31; ln = len(enc)
    except UnicodeEncodeError:
        enc = s.encode('utf-16-le'); flag = 0; ln = len(enc) // 2
    return _p(ln | flag, T_STRING) + enc + b'\0' * (-len(enc) % 8)

def sc_encode(v):
    if v is None: return _p(0, T_NULL)
    if isinstance(v, bool): return _p(int(v), T_BOOL)
    if isinstance(v, int) and -2**31 <= v < 2**31: return _p(v, T_INT)
    if isinstance(v, (int, float)): return struct.pack('<d', float(v))
    if isinstance(v, str): return _str(v)
    if isinstance(v, list):
        return _p(len(v), T_ARRAY) + b''.join(_p(i, T_INT) + sc_encode(x) for i, x in enumerate(v)) + _p(0, T_END)
    if isinstance(v, dict):
        return _p(0, T_OBJECT) + b''.join(_str(str(k)) + sc_encode(x) for k, x in v.items()) + _p(0, T_END)
    raise TypeError(type(v))

# ---------- claves IDB (string) ----------
def idb_key(s):
    out = bytearray([0x30])
    for ch in s:
        c = ord(ch)
        if c <= 0x7E: out.append(c + 1)
        elif c <= 0x3FFF + 0x7F:
            c -= 0x7F; out += bytes([0x80 | (c >> 8), c & 0xFF])
        else:
            c <<= 6; out += bytes([0xC0 | (c >> 16), (c >> 8) & 0xFF, c & 0xFF])
    return bytes(out)

def main():
    db, cmd, *a = sys.argv[1:]
    con = sqlite3.connect(db)
    # los triggers de Firefox llaman a update_refcount() (archivos externos de
    # valores grandes); los valores que escribimos van inline, asi que nunca
    # deberia ejecutarse: si pasa, abortar en vez de romper los refcounts
    def _refcount(*_): raise RuntimeError('valor con archivo externo: no soportado')
    con.create_function('update_refcount', 2, _refcount)
    store = con.execute("select id from object_store where name='storage-local-data'").fetchone()[0]
    rows = con.execute('select key, data, file_ids from object_data where object_store_id=?', (store,)).fetchall()
    if cmd == 'dump':
        for k, d, f in rows:
            v = sc_decode(snappy_decompress(d)) if not f else '<external file>'
            name = bytes(c - 1 for c in k[1:]).decode('latin1', 'replace') if k[:1] == b'\x30' else k
            print(name, '=', repr(v)[:120])
        return
    key = idb_key(a[0])
    if cmd == 'get':
        for k, d, f in rows:
            if k == key: print(json.dumps(sc_decode(snappy_decompress(d)), ensure_ascii=False)); return
        sys.exit(1)
    if cmd == 'set-str': val = sc_encode(open(a[1], encoding='utf-8').read())
    elif cmd == 'set-bool': val = sc_encode(a[1] == 'true')
    elif cmd == 'set-json': val = sc_encode(json.load(open(a[1], encoding='utf-8')))
    else: sys.exit(__doc__)
    # copiar el header de un registro existente (por si el scope no es 0)
    hdr = _hdr()
    if rows:
        r = snappy_decompress(rows[0][1])
        if struct.unpack_from('<I', r, 4)[0] == T_HEADER: hdr = r[:8]
    blob = snappy_compress(hdr + val)
    con.execute('insert or replace into object_data (object_store_id, key, index_data_values, file_ids, data) '
                'values (?, ?, NULL, NULL, ?)', (store, key, blob))
    con.commit(); con.close()

if __name__ == '__main__':
    main()

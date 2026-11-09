#!/usr/bin/env python3
"""Patch tidal-hifi's app.asar so it runs ~/.config/tidal-hifi/userscripts/*.js in the TIDAL page.

Appends a small loader to ts-dist/main.js inside the asar (pure Python, no node needed).
Idempotent: does nothing if the loader is already there. Usage: patch-asar.py [path/to/app.asar]
"""
import hashlib, json, os, struct, sys

ASAR = sys.argv[1] if len(sys.argv) > 1 else "/opt/tidal-hifi/resources/app.asar"
TARGET = ["ts-dist", "main.js"]
MARKER = "/* tidal-hifi-userscripts-loader */"
LOADER = MARKER + r"""
;(() => {
  const { app } = require("electron");
  const fs = require("fs");
  const path = require("path");
  app.on("web-contents-created", (_e, wc) => {
    wc.on("dom-ready", () => {
      if (!/^https:\/\/([\w-]+\.)?tidal\.com\//.test(wc.getURL())) return;
      const dir = path.join(app.getPath("userData"), "userscripts");
      let files = [];
      try { files = fs.readdirSync(dir).filter((f) => f.endsWith(".js")).sort(); } catch { return; }
      for (const f of files) {
        try {
          wc.executeJavaScript(fs.readFileSync(path.join(dir, f), "utf8"))
            .catch((err) => console.error("[userscripts]", f, err));
        } catch (err) { console.error("[userscripts]", f, err); }
      }
    });
  });
})();
"""

def main():
    with open(ASAR, "rb") as fh:
        raw = fh.read()
    (pickle_size,) = struct.unpack_from("<I", raw, 4)
    (json_len,) = struct.unpack_from("<I", raw, 12)
    header = json.loads(raw[16:16 + json_len].decode())
    data_start = 8 + pickle_size
    data = raw[data_start:]

    node = header
    for part in TARGET:
        node = node["files"][part]
    off, size = int(node["offset"]), node["size"]
    src = data[off:off + size]
    if MARKER.encode() in src:
        print("tidal-hifi userscripts loader already present")
        return
    new = src.rstrip(b"\n") + b"\n" + LOADER.encode()

    node["offset"] = str(len(data))
    node["size"] = len(new)
    block = 4 * 1024 * 1024
    node["integrity"] = {
        "algorithm": "SHA256",
        "hash": hashlib.sha256(new).hexdigest(),
        "blockSize": block,
        "blocks": [hashlib.sha256(new[i:i + block]).hexdigest() for i in range(0, max(len(new), 1), block)],
    }

    hjson = json.dumps(header, separators=(",", ":")).encode()
    pad = (4 - len(hjson) % 4) % 4
    hpickle = struct.pack("<II", 4 + len(hjson) + pad, len(hjson)) + hjson + b"\0" * pad
    out = struct.pack("<II", 4, len(hpickle)) + hpickle + data + new

    tmp = ASAR + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(out)
    os.chmod(tmp, os.stat(ASAR).st_mode & 0o7777)
    os.replace(tmp, ASAR)
    print("tidal-hifi patched to load userscripts")

if __name__ == "__main__":
    main()

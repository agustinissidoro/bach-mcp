/*
bachmcp.runner.files.js
-----------------------
Text files for the runners, through Max's File object (passed in, so that the
same code runs on a stand-in in the tests): an algorithm file to read, a
transformer's source score to read and write.

    const files = makeFiles(File);
    files.read(path)            the text, or null if it cannot be read
    files.write(path, text)     replaces the file; false if it cannot be opened
    basename(path)              the file's name, from a Max or a system path
*/
"use strict";

/** Text from UTF-8 bytes: Max's File reads bytes. */
function utf8(bytes) {
  let out = "";
  for (let i = 0; i < bytes.length; i++) {
    const b = bytes[i] & 255;
    if (b < 0x80) {
      out += String.fromCharCode(b);
    } else if (b >= 0xc0 && b < 0xe0 && i + 1 < bytes.length) {
      out += String.fromCharCode(((b & 0x1f) << 6) | (bytes[++i] & 0x3f));
    } else if (b >= 0xe0 && b < 0xf0 && i + 2 < bytes.length) {
      out += String.fromCharCode(((b & 0x0f) << 12) | ((bytes[++i] & 0x3f) << 6) | (bytes[++i] & 0x3f));
    } else if (b >= 0xf0 && i + 3 < bytes.length) {
      const cp = ((b & 0x07) << 18) | ((bytes[++i] & 0x3f) << 12) | ((bytes[++i] & 0x3f) << 6) | (bytes[++i] & 0x3f);
      out += String.fromCodePoint(cp);
    }
  }
  return out;
}

function makeFiles(File) {
  function read(path) {
    const f = new File(path, "read");
    if (!f.isopen) return null;
    const bytes = [];
    while (f.position < f.eof) {
      const chunk = f.readbytes(Math.min(4096, f.eof - f.position));
      if (!chunk || !chunk.length) break;
      for (let i = 0; i < chunk.length; i++) bytes.push(chunk[i]);
    }
    f.close();
    return utf8(bytes);
  }

  function write(path, content) {
    const f = new File(path, "write", "TEXT");
    if (!f.isopen) return false;
    f.position = 0;
    f.eof = 0;
    for (let i = 0; i < content.length; i += 4096) f.writestring(content.slice(i, i + 4096));
    f.eof = f.position;
    f.close();
    return true;
  }

  return { read, write };
}

function basename(path) {
  return String(path).split(/[\/:]/).pop();
}

module.exports = { makeFiles, basename };

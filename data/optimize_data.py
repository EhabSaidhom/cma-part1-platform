#!/usr/bin/env python3
"""
Make the question data load much faster.

Problem: every data/<source>/*.json file contains the question and explanation IMAGES
as huge base64 text (3-9 MB per sub-unit), so opening a topic downloads everything first.

This script moves every image into its own small file and leaves only the question
details in the JSON. The JSON shrinks ~100x (a few KB) and each image is downloaded only
when that question is shown.

USAGE (run in the project folder that contains the 'data' folder):
    python optimize_data.py                 # writes the result to  ./data_optimized
    python optimize_data.py --in data --out data_optimized

Then replace the old 'data' folder with 'data_optimized' (rename it to 'data'),
add the vercel.json that comes with this script, and deploy.
Your original 'data' folder is never modified.
Safe to run again. Only the standard library is needed.
"""
import argparse, base64, hashlib, json, os, re, shutil, sys

DATA_URI = re.compile(r'^data:image/([a-zA-Z0-9.+-]+);base64,(.*)$', re.S)
EXT = {'jpeg': 'jpg', 'jpg': 'jpg', 'png': 'png', 'webp': 'webp', 'gif': 'gif'}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='src', default='data')
    ap.add_argument('--out', dest='dst', default='data_optimized')
    a = ap.parse_args()
    if not os.path.isdir(a.src):
        sys.exit(f"Folder '{a.src}' not found. Run this script from the project folder.")
    img_dir = os.path.join(a.dst, 'img'); os.makedirs(img_dir, exist_ok=True)
    seen, n_img, n_files, before, after = set(), 0, 0, 0, 0
    def save(uri):
        nonlocal n_img
        m = DATA_URI.match(uri)
        if not m: return uri                                   # already a normal path/URL
        raw = base64.b64decode(m.group(2))
        name = hashlib.sha1(raw).hexdigest()[:16] + '.' + EXT.get(m.group(1).lower(), 'png')
        if name not in seen:
            seen.add(name); n_img += 1
            with open(os.path.join(img_dir, name), 'wb') as f: f.write(raw)
        return 'data/img/' + name
    for root, _, files in os.walk(a.src):
        rel = os.path.relpath(root, a.src)
        out = os.path.join(a.dst, rel) if rel != '.' else a.dst
        os.makedirs(out, exist_ok=True)
        for fn in files:
            p_in, p_out = os.path.join(root, fn), os.path.join(out, fn)
            if not fn.endswith('.json') or fn == 'manifest.json':
                shutil.copy2(p_in, p_out); continue
            with open(p_in, encoding='utf-8') as f: data = json.load(f)
            if isinstance(data, list):
                for q in data:
                    for k in ('image', 'explainImage'):
                        if isinstance(q.get(k), str): q[k] = save(q[k])
            with open(p_out, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
            n_files += 1; before += os.path.getsize(p_in); after += os.path.getsize(p_out)
            print(f"{os.path.join(rel, fn):55s} {os.path.getsize(p_in)/1e6:7.2f} MB -> {os.path.getsize(p_out)/1e3:8.1f} KB")
    print(f"\nDone. {n_files} data files: {before/1e6:.0f} MB -> {after/1e6:.1f} MB of JSON; {n_img} image files written to {img_dir}")
    print("Next: rename the old 'data' folder, rename '%s' to 'data', add vercel.json, deploy." % a.dst)

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
import hashlib, json, os, re, sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMP_ROOT = os.path.join(ROOT, "companies")
OUT_PATH = os.path.join(ROOT, "manifest.json")

TYPE_MAP = {
    "reports": "report",
    "transcripts": "transcript"
}

def sha1_of_file(path, chunk_size=65536):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            data = f.read(chunk_size)
            if not data: break
            h.update(data)
    return "sha1:" + h.hexdigest()

def slugify(name):
    s = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()
    return re.sub(r"-{2,}", "-", s)

def infer_doc_id(company, year, doc_type, filename):
    stem = os.path.splitext(os.path.basename(filename))[0]
    # try short, meaningful stem
    stem_s = slugify(stem)
    return f"{slugify(company)}-{year}-{doc_type[:6]}-{stem_s[:24]}"

def guess_title(filename):
    stem = os.path.splitext(os.path.basename(filename))[0]
    return re.sub(r"[_\-]+", " ", stem).strip()

def guess_pages(path):
    # lightweight: return None; your AI will page-count at read-time
    try:
        import PyPDF2
        with open(path, "rb") as f:
            pdf = PyPDF2.PdfReader(f)
            return len(pdf.pages)
    except Exception:
        return None

def build_manifest():
    companies = []
    for comp in sorted(os.listdir(COMP_ROOT)):
        comp_path = os.path.join(COMP_ROOT, comp)
        if not os.path.isdir(comp_path): continue
        years = []
        for year in sorted(os.listdir(comp_path)):
            if not year.isdigit(): continue
            year_path = os.path.join(comp_path, year)
            docs = []
            for sub in ("reports", "transcripts"):
                sub_path = os.path.join(year_path, sub)
                if not os.path.isdir(sub_path): continue
                for fn in sorted(os.listdir(sub_path)):
                    fpath = os.path.join(sub_path, fn)
                    if not os.path.isfile(fpath): continue
                    if not re.search(r"\.(pdf|txt|html?)$", fn, re.I): continue
                    doc_type = TYPE_MAP.get(sub, "other")
                    doc_id = infer_doc_id(comp, year, doc_type, fn)
                    docs.append({
                        "doc_id": doc_id,
                        "type": doc_type,
                        "title": guess_title(fn),
                        "path": os.path.relpath(fpath, ROOT).replace("\\", "/"),
                        "hash": sha1_of_file(fpath),
                        "pages": guess_pages(fpath)
                    })
            if docs:
                years.append({"year": int(year), "docs": docs})
        if years:
            companies.append({"company": comp, "years": years})

    manifest = {
        "version": "1.0",
        "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "root": "https://your-site/ir-hub/",
        "companies": companies
    }
    return manifest

def main():
    m = build_manifest()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_PATH} with {sum(len(y['docs']) for c in m['companies'] for y in c['years'])} docs.")

if __name__ == "__main__":
    sys.exit(main())

import sys
import os

def install_and_import(package):
    import importlib
    try:
        importlib.import_module(package)
    except ImportError:
        import subprocess
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def convert_pdf_to_md(pdf_path, md_path):
    install_and_import("markitdown")
    from markitdown import MarkItDown
    
    print(f"Converting {pdf_path} to Markdown using Microsoft MarkItDown...")
    md = MarkItDown()
    result = md.convert(pdf_path)
    
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(result.text_content)
    print(f"Successfully converted {pdf_path} to {md_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 pdf_to_md.py <pdf_path> <md_path>")
        sys.exit(1)
    convert_pdf_to_md(sys.argv[1], sys.argv[2])

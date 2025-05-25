import base64
import os
import time
from pathlib import Path
from typing import List

from mistralai import Mistral
from tqdm import tqdm


def _encode_base64(path: Path) -> str:
    """Read path as bytes and return a base-64 data-URI."""
    mime = "application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream"
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def parse_document(
    path: str | Path,
    *,
    api_key: str | None = None,
    model: str = "mistral-ocr-latest",
    include_images: bool = False,
    poll: float = 0.0,          # kept for API parity; ignored here
) -> List[str]:
    """
    Extract every page of path (PDF, image, PPTX…) using Mistral OCR.

    Returns
    -------
    list[str]  – markdown per page, preserving layout/structure.
    """
    path = Path(path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)

    api_key = api_key or os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("Set MISTRAL_API_KEY env-var or pass api_key=…")

    client = Mistral(api_key=api_key)

    print(f"[+] encoding {path} → base-64")
    data_uri = _encode_base64(path)

    print(f"[+] sending to Mistral OCR ({model})")
    ocr = client.ocr.process(
        model=model,
        document={"type": "document_url", "document_url": data_uri},
        include_image_base64=include_images,
    )

    # The SDK returns a Pydantic model; .pages is a list of Page objects.
    pages = [page.markdown for page in ocr.pages]
    print(f"[✓] received {len(pages)} pages from Mistral")
    return pages


if __name__ == "__main__":

  t0 = time.perf_counter()
  pages = parse_document("mathq.pdf",api_key="IhmKJGkJv61EPFwWIuY9wCgnbaFV6Fm1")
  dt = time.perf_counter() - t0

  joined = "\n\n".join(pages)
  print("\n=== PARSED OUTPUT (first 500 chars) ===\n")
  print(joined[:500] + ("…" if len(joined) > 5000 else ""))
  print(f"\n[done] extracted {len(joined):,} characters in {dt:.1f} s")
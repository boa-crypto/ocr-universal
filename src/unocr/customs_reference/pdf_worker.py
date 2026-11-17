"""Extraction native d'une page, processus jetable sans rendu, OCR ou JavaScript."""
import json
import sys

MAX_PAGES = 10_000
MAX_CARACTERES = 200_000


def main():
    try:
        # Garde Unix supplémentaire ; pas une isolation OS ou réseau complète.
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
    except (ImportError, ValueError, OSError):
        pass
    try:
        import pypdfium2 as pdfium
        numero = int(sys.argv[1])
        contenu = sys.stdin.buffer.read(64 * 1024 * 1024 + 1)
        if not 0 < len(contenu) <= 64 * 1024 * 1024 or not 1 <= numero <= MAX_PAGES:
            return 2
        with pdfium.PdfDocument(contenu) as document:
            nombre = len(document)
            if not 1 <= nombre <= MAX_PAGES or numero > nombre:
                return 2
            page = document[numero - 1]
            try:
                texte = page.get_textpage()
                try:
                    if texte.count_chars() > MAX_CARACTERES:
                        return 2
                    extrait = texte.get_text_bounded(errors="strict")
                    if len(extrait) > MAX_CARACTERES:
                        return 2
                finally:
                    texte.close()
            finally:
                page.close()
        print(json.dumps({"nombre_pages": nombre, "texte": extrait}, ensure_ascii=True))
        return 0
    except Exception:
        # Ne jamais propager un diagnostic du parseur contenant des données.
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

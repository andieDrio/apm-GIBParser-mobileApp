        payload = Path(path).read_bytes()
        assert payload.startswith(b"%PDF")

        from pypdf import PdfReader

        reader = PdfReader(path)
        extracted_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        assert "Operational-Password-123!" in extracted_text
        assert "Group-IB" in extracted_text
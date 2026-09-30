import os
import hashlib
import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings


_file_cache: dict[str, list[dict]] = {}


class RAGService:
    def __init__(self, db: AsyncSession, user_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.upload_dir = settings.upload_dir
        os.makedirs(self.upload_dir, exist_ok=True)
        self._qdrant = None
        self._embed_provider = None
        self._collection_ensured = False

    @staticmethod
    def cache_file(user_id: str, filename: str, file_path: str, text: str, file_id: str):
        if user_id not in _file_cache:
            _file_cache[user_id] = []
        # Avoid duplicate cache entries for same file_id
        _file_cache[user_id] = [f for f in _file_cache[user_id] if f.get("file_id") != file_id]
        _file_cache[user_id].append({
            "filename": filename,
            "file_path": file_path,
            "text": text,
            "file_id": file_id,
        })

    @staticmethod
    def get_cached_file_by_id(user_id: str, file_id: str) -> Optional[dict]:
        files = _file_cache.get(user_id, [])
        for f in files:
            if f.get("file_id") == file_id:
                return f
        return None

    @staticmethod
    def remove_cached_file(user_id: str, file_id: str) -> bool:
        if user_id not in _file_cache:
            return False
        before = len(_file_cache[user_id])
        _file_cache[user_id] = [f for f in _file_cache[user_id] if f.get("file_id") != file_id]
        return len(_file_cache[user_id]) < before

    @staticmethod
    def get_cached_file_content(user_id: str, filename_hint: str) -> Optional[str]:
        files = _file_cache.get(user_id, [])
        for f in reversed(files):
            if filename_hint.lower() in f["filename"].lower() or filename_hint == f.get("file_id"):
                return f["text"]
        return None

    @staticmethod
    def get_cached_file_path(user_id: str, filename_hint: str) -> Optional[str]:
        files = _file_cache.get(user_id, [])
        for f in reversed(files):
            if filename_hint.lower() in f["filename"].lower() or filename_hint == f.get("file_id"):
                return f["file_path"]
        return None

    @staticmethod
    def get_all_cached_texts(user_id: str) -> Optional[str]:
        files = _file_cache.get(user_id, [])
        if not files:
            return None
        parts = []
        for f in files:
            if f.get("text"):
                parts.append(f"[From {f['filename']} (file_id={f.get('file_id', '')})]:\n{f['text']}")
        return "\n\n".join(parts) if parts else None

    @staticmethod
    def get_cached_files(user_id: str) -> list[dict]:
        return list(_file_cache.get(user_id, []))

    def _get_qdrant(self):
        if self._qdrant is None:
            try:
                from qdrant_client import AsyncQdrantClient
                self._qdrant = AsyncQdrantClient(url=settings.qdrant_url, timeout=5)
            except Exception:
                self._qdrant = False
        return self._qdrant if self._qdrant is not False else None

    def _get_embed_provider(self):
        if self._embed_provider is None:
            try:
                from app.services.nvidia.embeddings import NvidiaEmbeddingsProvider
                self._embed_provider = NvidiaEmbeddingsProvider()
            except Exception:
                self._embed_provider = False
        return self._embed_provider if self._embed_provider is not False else None

    async def _ensure_collection(self):
        if self._collection_ensured:
            return True
        qdrant = self._get_qdrant()
        if not qdrant:
            return False
        try:
            from qdrant_client.models import VectorParams, Distance
            collections = await asyncio.wait_for(
                qdrant.get_collections(), timeout=5.0
            )
            exists = any(c.name == settings.qdrant_collection for c in collections.collections)
            if not exists:
                await asyncio.wait_for(
                    qdrant.create_collection(
                        collection_name=settings.qdrant_collection,
                        vectors_config=VectorParams(size=4096, distance=Distance.COSINE),
                    ),
                    timeout=5.0,
                )
            self._collection_ensured = True
            return True
        except (asyncio.TimeoutError, Exception):
            return False

    async def process_file(self, file_path: str, filename: str, file_id: Optional[str] = None) -> dict:
        ext = os.path.splitext(filename)[1].lower()
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("File is empty (0 bytes)")

        text = ""
        metadata = {"filename": filename, "path": file_path, "size": file_size}

        if ext in (".txt", ".md", ".rtf", ".log", ".ini", ".cfg", ".env.example"):
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        elif ext == ".pdf":
            text = self._extract_pdf(file_path)
        elif ext in (".docx", ".doc"):
            text = self._extract_docx(file_path)
        elif ext in (".csv", ".tsv"):
            text = self._extract_csv(file_path, ext)
        elif ext in (".xlsx", ".xls"):
            text = self._extract_excel(file_path)
        elif ext in (".pptx", ".ppt"):
            text = self._extract_pptx(file_path)
        elif ext == ".zip":
            text = self._extract_zip(file_path)
        elif ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"):
            text = self._extract_image_meta(file_path, filename, ext)
        elif ext in (
            ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".cs", ".go",
            ".rs", ".sql", ".html", ".css", ".scss", ".json", ".xml", ".yaml", ".yml",
            ".sh", ".ps1", ".rb", ".php", ".kt", ".swift", ".toml"
        ):
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                raw_text = f.read()
            if ext == ".json":
                import json as _json
                try:
                    parsed = _json.loads(raw_text)
                    text = _json.dumps(parsed, indent=2)
                except Exception as exc:
                    raise ValueError(f"Malformed JSON file: {exc}") from exc
            else:
                text = raw_text
            metadata["language"] = ext.lstrip(".")
        else:
            raise ValueError(f"Unsupported file format: {ext or 'unknown'}")

        if not text or not text.strip():
            raise ValueError(f"No readable content could be extracted from '{filename}'")

        content_hash = hashlib.sha256(text.encode()).hexdigest()
        chunks = self._chunk_text(text)

        if file_id and text.strip():
            await self._index_chunks(chunks, file_id, filename, metadata)

        return {
            "text": text,
            "chunks": chunks,
            "metadata": metadata,
            "content_hash": content_hash,
            "chunk_count": len(chunks),
        }

    async def _index_chunks(self, chunks: list[str], file_id: str, filename: str, metadata: dict):
        embed_provider = self._get_embed_provider()
        qdrant = self._get_qdrant()
        if not embed_provider or not qdrant:
            return
        if not await self._ensure_collection():
            return

        from qdrant_client.models import PointStruct

        batch_size = 10
        points = []
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            try:
                embeddings = await embed_provider.create(texts=batch, input_type="passage")
            except Exception:
                continue
            for j, (chunk_text, embedding) in enumerate(zip(batch, embeddings)):
                points.append(PointStruct(
                    id=f"{file_id}_{i + j}",
                    vector=embedding,
                    payload={
                        "file_id": file_id,
                        "filename": filename,
                        "chunk_index": i + j,
                        "text": chunk_text,
                        "user_id": self.user_id or "",
                    },
                ))
        if points:
            try:
                await asyncio.wait_for(
                    qdrant.upsert(
                        collection_name=settings.qdrant_collection,
                        points=points,
                    ),
                    timeout=5.0,
                )
            except (asyncio.TimeoutError, Exception):
                pass

    async def search_similar(self, query: str, top_k: int = 5) -> Optional[str]:
        if not query or not query.strip():
            return None

        qdrant = self._get_qdrant()
        if not qdrant:
            return None

        # Fast skip: check if collection exists, and verify if the user has any indexed files.
        # This completely avoids calling the expensive external NVIDIA embedding endpoint
        # for users who haven't uploaded any documents.
        try:
            collections = await asyncio.wait_for(qdrant.get_collections(), timeout=2.0)
            exists = any(c.name == settings.qdrant_collection for c in collections.collections)
            if not exists:
                return None
            
            # Check if this user has any documents in Qdrant
            from qdrant_client.models import Filter, FieldCondition, MatchValue
            user_filter = None
            if self.user_id:
                user_filter = Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=self.user_id))]
                )
            
            count_res = await asyncio.wait_for(
                qdrant.count(
                    collection_name=settings.qdrant_collection,
                    count_filter=user_filter,
                    exact=False
                ),
                timeout=2.0
            )
            if not count_res or count_res.count == 0:
                return None
        except Exception:
            return None

        embed_provider = self._get_embed_provider()
        if not embed_provider:
            return None
        try:
            query_embedding = await embed_provider.create(texts=[query], input_type="query")
        except Exception:
            return None
        if not query_embedding:
            return None

        from qdrant_client.models import Filter, FieldCondition, MatchValue

        filter_ = None
        if self.user_id:
            filter_ = Filter(
                must=[FieldCondition(key="user_id", match=MatchValue(value=self.user_id))]
            )

        try:
            results = await asyncio.wait_for(
                qdrant.search(
                    collection_name=settings.qdrant_collection,
                    query_vector=query_embedding[0],
                    limit=top_k,
                    query_filter=filter_,
                    score_threshold=0.5,
                ),
                timeout=5.0,
            )
        except (asyncio.TimeoutError, Exception):
            return None

        if not results:
            return None

        context_parts = []
        for r in results:
            text = r.payload.get("text", "")
            filename = r.payload.get("filename", "")
            if text:
                context_parts.append(f"[From {filename}]: {text}")

        if not context_parts:
            return None

        return "\n\n".join(context_parts)

    def _chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
        if len(text) <= chunk_size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            if end < len(text):
                last_period = text.rfind(".", start, end)
                last_newline = text.rfind("\n", start, end)
                split_at = max(last_period, last_newline)
                if split_at > start:
                    end = split_at + 1
            chunks.append(text[start:end])
            start = end - overlap if end < len(text) else len(text)
        return chunks

    def _extract_pdf(self, path: str) -> str:
        with open(path, "rb") as f:
            header = f.read(1024)
        if b"%PDF-" not in header:
            raise ValueError("Invalid or corrupt PDF file header")
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(path)
            if len(reader.pages) == 0:
                raise ValueError("PDF file contains 0 pages")
            extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
            if not extracted.strip():
                return f"PDF Document ({len(reader.pages)} pages, scanned/image-based layout)"
            return extracted
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Corrupt or unreadable PDF file: {exc}") from exc

    def _extract_docx(self, path: str) -> str:
        with open(path, "rb") as f:
            magic = f.read(4)
        if magic not in (b"PK\x03\x04", b"\xd0\xcf\x11\xe0"):
            raise ValueError("Invalid or corrupt Word document header")
        try:
            from docx import Document
            doc = Document(path)
            parts = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_cells = [c.text.strip() for c in row.cells if c.text and c.text.strip()]
                    if row_cells:
                        parts.append(" | ".join(row_cells))
            return "\n\n".join(parts) if parts else "Word document (empty text body)"
        except Exception as exc:
            raise ValueError(f"Corrupt or unreadable DOCX file: {exc}") from exc

    def _extract_csv(self, path: str, ext: str = ".csv") -> str:
        try:
            import pandas as pd
            sep = "\t" if ext == ".tsv" else ","
            df = pd.read_csv(path, sep=sep)
            return df.to_string()
        except Exception:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
            if not text.strip():
                raise ValueError("CSV file is empty")
            return text

    def _extract_excel(self, path: str) -> str:
        with open(path, "rb") as f:
            magic = f.read(4)
        if magic not in (b"PK\x03\x04", b"\xd0\xcf\x11\xe0"):
            raise ValueError("Invalid or corrupt Excel file header")
        try:
            import pandas as pd
            dfs = pd.read_excel(path, sheet_name=None)
            parts = []
            for sheet_name, df in dfs.items():
                parts.append(f"--- Sheet: {sheet_name} ---\n{df.to_string()}")
            return "\n\n".join(parts) if parts else "Excel workbook (empty sheets)"
        except Exception as exc:
            raise ValueError(f"Corrupt or unreadable Excel file: {exc}") from exc

    def _extract_pptx(self, path: str) -> str:
        with open(path, "rb") as f:
            magic = f.read(4)
        if magic not in (b"PK\x03\x04", b"\xd0\xcf\x11\xe0"):
            raise ValueError("Invalid or corrupt PowerPoint file header")
        try:
            from pptx import Presentation
            prs = Presentation(path)
            texts = []
            for idx, slide in enumerate(prs.slides, 1):
                slide_texts = []
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text and shape.text.strip():
                        slide_texts.append(shape.text.strip())
                if slide_texts:
                    texts.append(f"--- Slide {idx} ---\n" + "\n".join(slide_texts))
            return "\n\n".join(texts) if texts else f"PowerPoint presentation ({len(prs.slides)} slides)"
        except Exception as exc:
            raise ValueError(f"Corrupt or unreadable PPTX file: {exc}") from exc

    def _extract_zip(self, path: str) -> str:
        import zipfile
        if not zipfile.is_zipfile(path):
            raise ValueError("Invalid or corrupt ZIP archive")
        try:
            parts = []
            with zipfile.ZipFile(path, "r") as zf:
                names = zf.namelist()
                parts.append(f"ZIP Archive Contents ({len(names)} entries):\n" + "\n".join(f"- {n}" for n in names[:200]))
                extracted_bytes = 0
                readable_exts = {
                    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".json",
                    ".csv", ".tsv", ".html", ".css", ".yaml", ".yml", ".xml", ".sql", ".sh"
                }
                for info in zf.infolist():
                    if info.is_dir() or info.file_size > 512 * 1024:
                        continue
                    sub_ext = os.path.splitext(info.filename)[1].lower()
                    if sub_ext in readable_exts and extracted_bytes < 256 * 1024:
                        raw = zf.read(info.filename)
                        extracted_bytes += len(raw)
                        decoded = raw.decode("utf-8", errors="replace")
                        parts.append(f"--- File: {info.filename} ---\n{decoded[:12000]}")
            return "\n\n".join(parts)
        except Exception as exc:
            raise ValueError(f"Corrupt or unreadable ZIP archive: {exc}") from exc

    def _extract_image_meta(self, path: str, filename: str, ext: str) -> str:
        with open(path, "rb") as f:
            head = f.read(32)
        if ext == ".png" and not head.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Invalid or corrupt PNG image header")
        if ext in (".jpg", ".jpeg") and not head.startswith(b"\xff\xd8\xff"):
            raise ValueError("Invalid or corrupt JPEG image header")
        if ext == ".gif" and not (head.startswith(b"GIF87a") or head.startswith(b"GIF89a")):
            raise ValueError("Invalid or corrupt GIF image header")
        if ext == ".webp" and not (head.startswith(b"RIFF") and b"WEBP" in head[:16]):
            raise ValueError("Invalid or corrupt WEBP image header")
        if ext == ".bmp" and not head.startswith(b"BM"):
            raise ValueError("Invalid or corrupt BMP image header")
        if ext == ".svg":
            with open(path, "r", encoding="utf-8", errors="replace") as sf:
                svg_text = sf.read()
            if "<svg" not in svg_text.lower():
                raise ValueError("Invalid or corrupt SVG file")
            return f"SVG Vector Image ({filename}):\n{svg_text[:12000]}"

        try:
            from PIL import Image
            with Image.open(path) as img:
                width, height = img.size
                mode = img.mode
                fmt = img.format or ext.lstrip(".").upper()
                return f"Image Attachment: {filename} ({fmt}, {width}x{height}px, mode={mode}, size={os.path.getsize(path)} bytes)"
        except Exception:
            return f"Image Attachment: {filename} (format={ext.lstrip('.').upper()}, size={os.path.getsize(path)} bytes)"

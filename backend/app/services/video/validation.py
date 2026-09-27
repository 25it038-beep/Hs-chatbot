"""Video format validation and MP4 container verification."""

import struct
from typing import Tuple, Optional


class VideoValidator:
    """Validates raw binary data or file paths to guarantee legitimate video assets."""

    MP4_FTYP_SIGNATURE = b"ftyp"

    @classmethod
    def validate_mp4_bytes(cls, data: bytes) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Validates raw bytes as a legitimate MP4 container.
        Returns: (is_valid, error_message, metadata)
        """
        if not data or len(data) < 16:
            return False, "File is too small to be a valid video container (< 16 bytes)", None

        # Check for 'ftyp' atom in the first 32 bytes
        ftyp_pos = data[:32].find(cls.MP4_FTYP_SIGNATURE)
        if ftyp_pos == -1:
            return False, "Invalid container: missing ISO MP4 'ftyp' atom header", None

        # Offset to major brand is 4 bytes after 'ftyp'
        major_brand_bytes = data[ftyp_pos + 4 : ftyp_pos + 8]
        try:
            major_brand = major_brand_bytes.decode("ascii", errors="ignore").strip()
        except Exception:
            major_brand = "unknown"

        meta = {
            "format": "mp4",
            "major_brand": major_brand,
            "byte_size": len(data),
        }
        return True, None, meta

    @classmethod
    def validate_video_file(cls, file_path: str) -> Tuple[bool, Optional[str], Optional[dict]]:
        """Validates a file on disk."""
        import os
        if not os.path.exists(file_path):
            return False, f"File does not exist: {file_path}", None

        size = os.path.getsize(file_path)
        if size < 1024:
            return False, f"File is too small to be a valid video ({size} bytes)", None

        try:
            with open(file_path, "rb") as f:
                header = f.read(64)
                valid, err, meta = cls.validate_mp4_bytes(header)
                if not valid:
                    return False, err, None
                meta["file_size"] = size
                return True, None, meta
        except Exception as e:
            return False, f"Failed to read video file: {str(e)}", None


video_validator = VideoValidator()

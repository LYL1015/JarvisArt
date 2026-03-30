import importlib.util
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Tuple

MODULE_PATH = Path(__file__).resolve().parents[1] / "lrc_api_server.py"
spec = importlib.util.spec_from_file_location("lrc_api_server", MODULE_PATH)
lrc_api_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lrc_api_server)


def build_multipart_body(boundary: str, fields: Dict[str, str], files: Dict[str, Tuple[str, bytes, str]]) -> bytes:
    chunks: List[bytes] = []
    for key, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode(),
                f"{value}\r\n".encode(),
            ]
        )

    for key, (filename, content, content_type) in files.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'.encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                content,
                b"\r\n",
            ]
        )

    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks)


class RequestParsingTests(unittest.TestCase):
    def test_parse_json_payload_supports_lua_path(self):
        payload = b'{"photo_path":"/tmp/photo.jpg","lua_path":"/tmp/preset.lua"}'

        request_data = lrc_api_server.PhotoProcessHandler.parse_json_payload(payload)
        photo_path, preset_path = lrc_api_server.PhotoProcessHandler.extract_photo_and_preset_paths(request_data)

        self.assertEqual(photo_path, "/tmp/photo.jpg")
        self.assertEqual(preset_path, "/tmp/preset.lua")

    def test_parse_multipart_payload_handles_binary_upload(self):
        boundary = "----JarvisArtBoundary"
        body = build_multipart_body(
            boundary=boundary,
            fields={"mode": "upload", "task_id": "task_123"},
            files={
                "photo_file": ("photo.jpg", b"\xff\xd8\xff\xe0\x00\x10JPEG", "image/jpeg"),
                "lua_file": ("preset.lua", b"return {Exposure2012 = 0.25}", "text/plain"),
            },
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            request_data = lrc_api_server.PhotoProcessHandler.parse_multipart_payload(
                raw_payload=body,
                content_type=f"multipart/form-data; boundary={boundary}",
                upload_root=Path(tmp_dir),
            )

            photo_path = Path(request_data["photo_path"])
            preset_path = Path(request_data["xmp_path"])

            self.assertTrue(photo_path.exists())
            self.assertTrue(preset_path.exists())
            self.assertEqual(photo_path.read_bytes(), b"\xff\xd8\xff\xe0\x00\x10JPEG")
            self.assertEqual(preset_path.read_text(encoding="utf-8"), "return {Exposure2012 = 0.25}")


if __name__ == "__main__":
    unittest.main()

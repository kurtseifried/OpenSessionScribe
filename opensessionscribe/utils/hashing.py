"""File hashing and manifest generation utilities."""

import hashlib
from pathlib import Path
from typing import Dict, List


def sha256_file(file_path: Path) -> str:
    """Calculate SHA-256 hash of file."""
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_manifest(output_dir: Path) -> Dict[str, str]:
    """Generate manifest with hashes of all output files."""
    manifest = {}
    
    # Hash all files in output directory
    for file_path in output_dir.rglob("*"):
        if file_path.is_file() and file_path.name != "manifest.json":
            relative_path = file_path.relative_to(output_dir)
            manifest[str(relative_path)] = sha256_file(file_path)
    
    return manifest


def verify_manifest(output_dir: Path, manifest: Dict[str, str]) -> bool:
    """Verify all files match their manifest hashes."""
    for rel_path, expected_hash in manifest.items():
        file_path = output_dir / rel_path
        if not file_path.exists():
            return False
        
        actual_hash = sha256_file(file_path)
        if actual_hash != expected_hash:
            return False
    
    return True


def perceptual_hash(image_path: Path) -> str:
    """Calculate perceptual hash for image deduplication."""
    # TODO: Use imagehash library
    # Return pHash or dHash for slide deduplication
    pass
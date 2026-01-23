"""Caching layer for validation results to speed up re-validation of identical files."""

import hashlib
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
from .types import ValidationResult


class ValidationCache:
    """
    Caching system for validation results.
    
    Avoids re-validating identical files by using SHA256 file hashing.
    Dramatically speeds up pipelines that process the same data multiple times.
    
    Example:
        >>> cache = ValidationCache(cache_dir='.validation_cache')
        >>> if not cache.has_result('data.csv'):
        ...     result = validator.validate_csv('data.csv')
        ...     cache.save_result('data.csv', result)
        ... else:
        ...     result = cache.load_result('data.csv')
    """
    
    def __init__(
        self,
        cache_dir: str = '.pyrustpipe_cache',
        ttl_hours: int = 24,
        max_cache_size_mb: int = 500,
    ):
        """
        Initialize ValidationCache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_hours: Cache time-to-live in hours
            max_cache_size_mb: Maximum cache size in megabytes
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.ttl = timedelta(hours=ttl_hours)
        self.max_cache_size = max_cache_size_mb * 1024 * 1024
        self.manifest_path = self.cache_dir / 'manifest.json'
        
        self._load_manifest()
    
    def _load_manifest(self) -> None:
        """Load cache manifest from disk."""
        if self.manifest_path.exists():
            with open(self.manifest_path, 'r') as f:
                self.manifest = json.load(f)
        else:
            self.manifest = {}
    
    def _save_manifest(self) -> None:
        """Save cache manifest to disk."""
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)
    
    def _get_file_hash(self, filepath: str) -> str:
        """
        Calculate SHA256 hash of file for cache key.
        
        Args:
            filepath: Path to file
            
        Returns:
            SHA256 hash hexdigest
        """
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid."""
        if cache_key not in self.manifest:
            return False
        
        entry = self.manifest[cache_key]
        created_at = datetime.fromisoformat(entry['created_at'])
        
        return datetime.now() - created_at < self.ttl
    
    def has_result(self, filepath: str) -> bool:
        """
        Check if validation result is cached.
        
        Args:
            filepath: Path to file
            
        Returns:
            True if valid cache entry exists
        """
        file_hash = self._get_file_hash(filepath)
        return self._is_cache_valid(file_hash)
    
    def save_result(
        self, filepath: str, result: ValidationResult, metadata: Optional[Dict] = None
    ) -> None:
        """
        Save validation result to cache.
        
        Args:
            filepath: Path to file being validated
            result: ValidationResult object
            metadata: Optional metadata to store with result
        """
        file_hash = self._get_file_hash(filepath)
        cache_file = self.cache_dir / f"{file_hash}.json"
        
        # Serialize result
        cache_data = {
            'file_hash': file_hash,
            'filepath': filepath,
            'created_at': datetime.now().isoformat(),
            'valid_count': result.valid_count,
            'invalid_count': result.invalid_count,
            'total_rows': result.total_rows,
            'success_rate': result.success_rate(),
            'metadata': metadata or {},
            'errors_count': len(result.errors),
        }
        
        # Save to cache file
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        # Update manifest
        self.manifest[file_hash] = {
            'filepath': filepath,
            'created_at': datetime.now().isoformat(),
            'cache_file': str(cache_file),
        }
        
        self._save_manifest()
        self._cleanup_cache()
    
    def load_result(self, filepath: str) -> Optional[ValidationResult]:
        """
        Load cached validation result.
        
        Args:
            filepath: Path to file
            
        Returns:
            Cached ValidationResult or None if not found/expired
        """
        file_hash = self._get_file_hash(filepath)
        
        if not self._is_cache_valid(file_hash):
            return None
        
        cache_file = self.cache_dir / f"{file_hash}.json"
        
        if not cache_file.exists():
            return None
        
        with open(cache_file, 'r') as f:
            data = json.load(f)
        
        # Return simplified result (errors not reconstructed from cache)
        return ValidationResult(
            valid_count=data['valid_count'],
            invalid_count=data['invalid_count'],
            total_rows=data['total_rows'],
            errors=[]  # Errors not cached for space efficiency
        )
    
    def invalidate(self, filepath: str) -> None:
        """
        Invalidate cache entry for a file.
        
        Args:
            filepath: Path to file
        """
        file_hash = self._get_file_hash(filepath)
        
        if file_hash in self.manifest:
            cache_file = self.cache_dir / f"{file_hash}.json"
            if cache_file.exists():
                cache_file.unlink()
            
            del self.manifest[file_hash]
            self._save_manifest()
    
    def clear_all(self) -> None:
        """Clear entire cache."""
        for file in self.cache_dir.glob('*.json'):
            if file.name != 'manifest.json':
                file.unlink()
        
        self.manifest = {}
        self._save_manifest()
    
    def _cleanup_cache(self) -> None:
        """Remove expired entries and enforce size limits."""
        now = datetime.now()
        expired = []
        
        # Find expired entries
        for file_hash, entry in list(self.manifest.items()):
            created_at = datetime.fromisoformat(entry['created_at'])
            if now - created_at >= self.ttl:
                expired.append(file_hash)
        
        # Remove expired
        for file_hash in expired:
            cache_file = self.cache_dir / f"{file_hash}.json"
            if cache_file.exists():
                cache_file.unlink()
            del self.manifest[file_hash]
        
        # Enforce size limit
        cache_size = sum(
            (self.cache_dir / f"{h}.json").stat().st_size
            for h in self.manifest
            if (self.cache_dir / f"{h}.json").exists()
        )
        
        if cache_size > self.max_cache_size:
            # Remove oldest entries until under limit
            entries_by_date = sorted(
                self.manifest.items(),
                key=lambda x: x[1]['created_at']
            )
            
            for file_hash, entry in entries_by_date:
                if cache_size <= self.max_cache_size:
                    break
                
                cache_file = self.cache_dir / f"{file_hash}.json"
                if cache_file.exists():
                    cache_size -= cache_file.stat().st_size
                    cache_file.unlink()
                
                del self.manifest[file_hash]
        
        self._save_manifest()
    
    def get_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        cache_size = sum(
            (self.cache_dir / f"{h}.json").stat().st_size
            for h in self.manifest
            if (self.cache_dir / f"{h}.json").exists()
        )
        
        return {
            'entries': len(self.manifest),
            'cache_size_mb': cache_size / (1024 ** 2),
            'cache_dir': str(self.cache_dir),
            'ttl_hours': int(self.ttl.total_seconds() / 3600),
            'max_size_mb': self.max_cache_size / (1024 ** 2),
        }


class CachedValidator:
    """
    Wrapper around Validator that uses ValidationCache.
    
    Automatically caches results and reuses them for identical files.
    
    Example:
        >>> cv = CachedValidator(schema=schema)
        >>> result = cv.validate_csv('data.csv')  # Validates
        >>> result = cv.validate_csv('data.csv')  # Uses cache!
    """
    
    def __init__(self, validator, cache_dir: str = '.pyrustpipe_cache'):
        """
        Initialize CachedValidator.
        
        Args:
            validator: Validator instance to wrap
            cache_dir: Directory for cache storage
        """
        self.validator = validator
        self.cache = ValidationCache(cache_dir=cache_dir)
    
    def validate_csv(self, filepath: str, use_cache: bool = True) -> ValidationResult:
        """
        Validate CSV file with caching.
        
        Args:
            filepath: Path to CSV file
            use_cache: Whether to use cache
            
        Returns:
            ValidationResult
        """
        # Check cache first
        if use_cache and self.cache.has_result(filepath):
            return self.cache.load_result(filepath)
        
        # Validate
        result = self.validator.validate_csv(filepath)
        
        # Cache result
        if use_cache:
            self.cache.save_result(filepath, result)
        
        return result
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return self.cache.get_stats()


__all__ = ['ValidationCache', 'CachedValidator']

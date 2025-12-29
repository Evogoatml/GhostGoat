"""
ADAP Integration System - Core Integration Engine
Handles repository cloning, analysis, and integration
"""

import os
import shutil
import zipfile
import tempfile
import subprocess
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import git
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib

class IntegrationEngine:
    """Main engine for repository integration"""
    
    def __init__(self, config: dict):
        self.config = config
        self.storage = config['storage']
        self.git_config = config['git']
        
        # Ensure storage directories exist
        for path in self.storage.values():
            Path(path).mkdir(parents=True, exist_ok=True)
    
    def reload_config(self, new_config: dict):
        """Reload configuration"""
        self.config = new_config
        self.storage = new_config['storage']
        self.git_config = new_config['git']
    
    def clone_repository(self, repo_url: str) -> Path:
        """Clone a repository from URL"""
        # Validate URL
        if not self._validate_repo_url(repo_url):
            raise ValueError(f"Invalid or unsupported repository URL: {repo_url}")
        
        # Generate unique directory name
        repo_hash = hashlib.md5(repo_url.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        repo_name = f"repo_{repo_hash}_{timestamp}"
        
        repo_path = Path(self.storage['repos_path']) / repo_name
        
        try:
            # Clone with timeout
            git.Repo.clone_from(
                repo_url,
                repo_path,
                depth=None if not self.git_config['shallow_clone'] else 1,
                progress=GitProgress()
            )
            
            # Check repository size
            repo_size = self._get_directory_size(repo_path)
            max_size = self._parse_size(self.git_config['max_repo_size'])
            
            if repo_size > max_size:
                shutil.rmtree(repo_path)
                raise ValueError(f"Repository too large: {repo_size} bytes (max: {max_size})")
            
            return repo_path
            
        except git.exc.GitCommandError as e:
            if repo_path.exists():
                shutil.rmtree(repo_path)
            raise RuntimeError(f"Failed to clone repository: {str(e)}")
    
    def extract_upload(self, zip_path: str) -> Path:
        """Extract uploaded zip file"""
        extract_path = Path(self.storage['temp_path']) / f"upload_{datetime.now().timestamp()}"
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Check for zip bombs
            total_size = sum(zinfo.file_size for zinfo in zip_ref.filelist)
            compressed_size = sum(zinfo.compress_size for zinfo in zip_ref.filelist)
            
            if total_size / compressed_size > 100:  # Compression ratio check
                raise ValueError("Suspicious compression ratio detected")
            
            if total_size > self._parse_size(self.config['server']['max_request_size']):
                raise ValueError("Extracted size exceeds maximum allowed")
            
            zip_ref.extractall(extract_path)
        
        # Clean up zip file
        os.remove(zip_path)
        
        return extract_path
    
    def integrate_algorithm(self, source_path: str, category: str, name: str) -> str:
        """Integrate algorithm into comprehension structure"""
        # Create category directory
        category_path = Path(self.storage['comprehension_path']) / category
        category_path.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename if exists
        target_filename = f"{name}.py"
        target_path = category_path / target_filename
        
        counter = 1
        while target_path.exists():
            target_filename = f"{name}_{counter}.py"
            target_path = category_path / target_filename
            counter += 1
        
        # Copy algorithm file
        shutil.copy2(source_path, target_path)
        
        # Create metadata
        metadata = {
            'name': name,
            'category': category,
            'original_path': source_path,
            'integrated_at': datetime.now().isoformat(),
            'file_hash': self._calculate_file_hash(target_path)
        }
        
        metadata_path = target_path.with_suffix('.meta.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return str(target_path)
    
    def create_export(self, job_id: int) -> str:
        """Create zip export of integration"""
        from src.database import Session, IntegrationJob, AlgorithmRecord
        
        db = Session()
        job = db.query(IntegrationJob).filter_by(id=job_id).first()
        algorithms = db.query(AlgorithmRecord).filter_by(
            job_id=job_id,
            integrated=True
        ).all()
        
        # Create temporary directory for export
        export_dir = Path(tempfile.mkdtemp())
        
        # Create structure
        (export_dir / 'algorithms').mkdir()
        (export_dir / 'plugins').mkdir()
        (export_dir / 'metadata').mkdir()
        
        # Copy integrated algorithms
        for algo in algorithms:
            if algo.target_path and os.path.exists(algo.target_path):
                category_dir = export_dir / 'algorithms' / algo.category
                category_dir.mkdir(exist_ok=True)
                shutil.copy2(algo.target_path, category_dir / f"{algo.name}.py")
                
                # Copy plugin if exists
                if algo.plugin_path and os.path.exists(algo.plugin_path):
                    plugin_dir = export_dir / 'plugins' / algo.category
                    plugin_dir.mkdir(exist_ok=True)
                    shutil.copy2(algo.plugin_path, plugin_dir / f"{algo.name}_plugin.py")
        
        # Create summary
        summary = {
            'job_id': job_id,
            'repository': job.repo_url,
            'exported_at': datetime.now().isoformat(),
            'total_algorithms': len(algorithms),
            'algorithms': [
                {
                    'name': algo.name,
                    'category': algo.category,
                    'complexity': algo.complexity
                }
                for algo in algorithms
            ]
        }
        
        with open(export_dir / 'metadata' / 'summary.json', 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Create installation script
        install_script = '''#!/bin/bash
# ADAP Integration Installation Script

echo "Installing ADAP integration..."

# Create directories
mkdir -p /mnt/comprehension
mkdir -p /mnt/comprehension/plugins

# Copy algorithms
cp -r algorithms/* /mnt/comprehension/

# Copy plugins
cp -r plugins/* /mnt/comprehension/plugins/

echo "Installation complete!"
echo "Algorithms installed to: /mnt/comprehension"
echo "Plugins installed to: /mnt/comprehension/plugins"
'''
        
        with open(export_dir / 'install.sh', 'w') as f:
            f.write(install_script)
        
        # Make install script executable
        os.chmod(export_dir / 'install.sh', 0o755)
        
        # Create README
        readme = f'''# ADAP Integration Export

This export contains {len(algorithms)} algorithms integrated from:
{job.repo_url}

## Contents

- `algorithms/` - Integrated algorithm files organized by category
- `plugins/` - Generated ADAP plugin wrappers
- `metadata/` - Integration metadata and summary
- `install.sh` - Installation script

## Installation

1. Extract this archive
2. Run: `./install.sh`

## Categories

'''
        
        categories = {}
        for algo in algorithms:
            categories[algo.category] = categories.get(algo.category, 0) + 1
        
        for cat, count in categories.items():
            readme += f"- {cat}: {count} algorithms\n"
        
        with open(export_dir / 'README.md', 'w') as f:
            f.write(readme)
        
        # Create zip file
        zip_path = Path(self.storage['temp_path']) / f'adap_export_{job_id}.zip'
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(export_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(export_dir)
                    zipf.write(file_path, arcname)
        
        # Cleanup
        shutil.rmtree(export_dir)
        db.close()
        
        return str(zip_path)
    
    def _validate_repo_url(self, url: str) -> bool:
        """Validate repository URL"""
        # Check if it's a local path (for uploaded files)
        if url.startswith('file://'):
            return True
        
        # Check supported hosts
        for host in self.git_config['supported_hosts']:
            if host in url:
                return True
        
        return False
    
    def _get_directory_size(self, path: Path) -> int:
        """Calculate directory size in bytes"""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = Path(dirpath) / filename
                if filepath.is_file():
                    total += filepath.stat().st_size
        return total
    
    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '500MB' to bytes"""
        units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 * 1024,
            'GB': 1024 * 1024 * 1024
        }
        
        for unit, multiplier in units.items():
            if size_str.endswith(unit):
                number = float(size_str[:-len(unit)])
                return int(number * multiplier)
        
        return int(size_str)  # Assume bytes if no unit
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


class GitProgress(git.RemoteProgress):
    """Progress handler for git operations"""
    
    def update(self, op_code, cur_count, max_count=None, message=''):
        """Update progress"""
        if message:
            percentage = (cur_count / max_count * 100) if max_count else 0
            print(f"Git progress: {message} ({percentage:.1f}%)")

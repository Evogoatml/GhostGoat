#!/usr/bin/env python3
"""GhostGoat Audit System - tracks changes and auto-fixes imports"""
import os, sys, json, hashlib, argparse
from pathlib import Path
from datetime import datetime

class AuditLogger:
    def __init__(self, audit_file=".audit.json"):
        self.audit_file = audit_file
        self.entries = self.load()
    
    def load(self):
        if os.path.exists(self.audit_file):
            with open(self.audit_file) as f:
                return json.load(f)
        return {"changes": [], "fixes": []}
    
    def save(self):
        with open(self.audit_file, 'w') as f:
            json.dump(self.entries, f, indent=2)
    
    def log_change(self, file_path, action, old_hash=None, new_hash=None):
        self.entries["changes"].append({
            "timestamp": datetime.now().isoformat(),
            "file": file_path, "action": action,
            "old_hash": old_hash, "new_hash": new_hash
        })
        self.save()
    
    def hash_file(self, path):
        if os.path.exists(path):
            with open(path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()[:8]
        return None

class ImportFixer:
    def __init__(self, root):
        self.root = root
        self.audit = AuditLogger()
        self.fixes = {}
    
    def scan_file(self, file_path):
        with open(file_path, 'r') as f:
            content = f.read()
        changes = []
        for old, new in self.fixes.items():
            if old in content and new not in content:
                changes.append((old, new))
        return changes
    
    def fix_file(self, file_path, dry_run=False):
        old_hash = self.audit.hash_file(file_path)
        changes = self.scan_file(file_path)
        if not changes:
            return []
        if dry_run:
            return changes
        with open(file_path, 'r') as f:
            content = f.read()
        for old, new in changes:
            content = content.replace(old, new)
            self.audit.log_change(file_path, "import_fix", old_hash, self.audit.hash_file(file_path))
        with open(file_path, 'w') as f:
            f.write(content)
        return changes
    
    def scan_all(self):
        issues = []
        for root, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in ('venv', '.venv', '__pycache__', '.git', 'node_modules', '_MOVED')]
            for f in files:
                if f.endswith('.py'):
                    path = os.path.join(root, f)
                    try:
                        changes = self.scan_file(path)
                        if changes:
                            issues.append((path, changes))
                    except:
                        pass
        return issues
    
    def fix_all(self, dry_run=False):
        issues = self.scan_all()
        fixed = []
        for path, changes in issues:
            if not dry_run:
                self.fix_file(path)
            fixed.append((path, changes))
        return fixed

class FileWatcher:
    def __init__(self, root, watch_file=".watched_files.json"):
        self.root = root
        self.watch_file = watch_file
        self.files = self.load()
        self.audit = AuditLogger()
    
    def load(self):
        if os.path.exists(self.watch_file):
            with open(self.watch_file) as f:
                return json.load(f)
        return {}
    
    def save(self):
        with open(self.watch_file, 'w') as f:
            json.dump(self.files, f, indent=2)
    
    def add(self, path):
        if os.path.exists(path):
            self.files[path] = {"hash": self.audit.hash_file(path), "added": datetime.now().isoformat()}
            self.save()
    
    def check_changes(self):
        changed = []
        for path, info in list(self.files.items()):
            if os.path.exists(path):
                current_hash = self.audit.hash_file(path)
                if current_hash != info["hash"]:
                    changed.append((path, info["hash"], current_hash))
                    self.files[path]["hash"] = current_hash
        self.save()
        return changed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GhostGoat Audit System")
    parser.add_argument("command", choices=["scan", "fix", "watch", "report"])
    parser.add_argument("--file", "-f", help="Specific file")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Dry run only")
    parser.add_argument("--path", "-p", default=".", help="Path to scan")
    args = parser.parse_args()
    fixer = ImportFixer(args.path)
    if args.command == "scan":
        issues = fixer.scan_all()
        if issues:
            print(f"Found {len(issues)} files with import issues:")
            for path, changes in issues:
                print(f"  {path}")
                for old, new in changes:
                    print(f"    - {old}")
        else:
            print("No import issues found")
    elif args.command == "fix":
        if args.file:
            result = fixer.fix_file(args.file, dry_run=args.dry_run)
            print(f"Fixed: {result}")
        else:
            result = fixer.fix_all(dry_run=args.dry_run)
            print(f"Fixed {len(result)} files")
    elif args.command == "watch":
        watcher = FileWatcher(args.path)
        if args.file:
            watcher.add(args.file)
            print(f"Now watching: {args.file}")
        else:
            changed = watcher.check_changes()
            if changed:
                print("Changed files:")
                for path, old, new in changed:
                    print(f"  {path}: {old} -> {new}")
            else:
                print("No changes detected")
    elif args.command == "report":
        audit = AuditLogger()
        print(f"Audit: {len(audit.entries['changes'])} changes, {len(audit.entries['fixes'])} fixes")
        print("\nRecent changes:")
        for entry in audit.entries["changes"][-10:]:
            print(f"  {entry['timestamp']} - {entry['file']}: {entry['action']}")
import ast
import inspect
import hashlib
from typing import Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime


class SelfModifier:
    """Manages self-modification of system code"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.modification_log = []
        self.rollback_stack = []
        self.max_rollback_depth = 10
        
    async def apply(self, modification: Dict) -> bool:
        """Apply a code modification"""
        try:
            mod_type = modification['type']
            
            if mod_type == 'add_method':
                return await self.add_method(modification)
            elif mod_type == 'modify_method':
                return await self.modify_method(modification)
            elif mod_type == 'add_threshold':
                return await self.add_threshold(modification)
            else:
                return False
                
        except Exception as e:
            print(f"Modification failed: {e}")
            return False
    
    async def add_method(self, modification: Dict) -> bool:
        """Add a new method to a class"""
        target_class = modification['target_class']
        method_name = modification['method_name']
        code = modification['code']
        
        # Parse and validate code
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            print(f"Invalid Python syntax: {e}")
            return False
        
        # Store rollback info
        self.rollback_stack.append({
            'type': 'remove_method',
            'class': target_class,
            'method': method_name,
            'timestamp': datetime.now().isoformat()
        })
        
        # Trim rollback stack
        if len(self.rollback_stack) > self.max_rollback_depth:
            self.rollback_stack.pop(0)
        
        # Log modification
        self.modification_log.append({
            'type': 'add_method',
            'target': f"{target_class}.{method_name}",
            'timestamp': datetime.now().isoformat(),
            'code_hash': hashlib.sha256(code.encode()).hexdigest()
        })
        
        return True
    
    async def modify_method(self, modification: Dict) -> bool:
        """Modify an existing method"""
        # Implementation for modifying existing methods
        return True
    
    async def add_threshold(self, modification: Dict) -> bool:
        """Add or modify a threshold"""
        threshold_name = modification['name']
        value = modification['value']
        
        # Store in config
        if 'thresholds' not in self.config:
            self.config['thresholds'] = {}
        
        old_value = self.config['thresholds'].get(threshold_name)
        self.config['thresholds'][threshold_name] = value
        
        # Store rollback
        self.rollback_stack.append({
            'type': 'restore_threshold',
            'name': threshold_name,
            'value': old_value,
            'timestamp': datetime.now().isoformat()
        })
        
        return True
    
    async def rollback(self) -> bool:
        """Rollback the last modification"""
        if not self.rollback_stack:
            return False
        
        rollback_info = self.rollback_stack.pop()
        
        if rollback_info['type'] == 'remove_method':
            # Remove added method
            pass
        elif rollback_info['type'] == 'restore_threshold':
            # Restore old threshold value
            self.config['thresholds'][rollback_info['name']] = rollback_info['value']
        
        return True

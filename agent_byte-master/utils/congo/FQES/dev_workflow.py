#!/usr/bin/env python3
"""
FQES Development Workflow Script
Helps manage the implementation phases
"""

import subprocess
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

class FQESDeveloper:
    """FQES Development Assistant"""
    
    def __init__(self):
        self.phases = {
            1: "Mathematical Foundation",
            2: "Basic Compression", 
            3: "Agent Integration",
            4: "Quantum Resistance"
        }
        
    def show_phase_plan(self, phase_num):
        """Show the implementation plan for a specific phase"""
        phase_file = Path("docs/IMPLEMENTATION_PLAN.md")
        if phase_file.exists():
            with open(phase_file, 'r') as f:
                content = f.read()
                # Extract phase information
                phases = content.split('## Phase ')[1:]
                if phase_num <= len(phases):
                    print(f"📋 Phase {phase_num} Plan:")
                    print("=" * 40)
                    phase_content = phases[phase_num-1].split('## Phase ')[0]
                    print(phase_content[:1000] + "..." if len(phase_content) > 1000 else phase_content)
                else:
                    print(f"Phase {phase_num} not found in plan")
        else:
            print("Implementation plan file not found")
    
    def run_tests(self):
        """Run the test suite"""
        print("🧪 Running FQES test suite...")
        result = subprocess.run([sys.executable, "test_fqes.py"], 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    
    def create_phase_branch(self, phase_num):
        """Create a git branch for a development phase"""
        branch_name = f"phase-{phase_num}"
        result = subprocess.run(["git", "checkout", "-b", branch_name], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Created branch '{branch_name}' for Phase {phase_num}")
            return True
        else:
            print(f"❌ Failed to create branch: {result.stderr}")
            return False
    
    def show_current_status(self):
        """Show current development status"""
        print("📊 Current FQES Development Status")
        print("=" * 40)
        
        # Check if git is initialized
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Git repository initialized")
        else:
            print("❌ Git not initialized")
        
        # Check file structure
        required_dirs = ["src/core", "src/agents", "src/quantum", "src/integration", "tests", "docs"]
        for dir_path in required_dirs:
            if Path(dir_path).exists():
                print(f"✅ {dir_path}/ exists")
            else:
                print(f"❌ {dir_path}/ missing")
        
        # Show phase information
        print(f"\n🎯 Total phases defined: {len(self.phases)}")
        for phase_num, phase_name in self.phases.items():
            print(f"   Phase {phase_num}: {phase_name}")

def main():
    developer = FQESDeveloper()
    
    print("🚀 FQES Development Workflow Assistant")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. Show Current Status")
        print("2. Show Phase Plan")
        print("3. Run Tests")
        print("4. Create Development Branch")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            developer.show_current_status()
                
        elif choice == "2":
            phase = input("Enter phase number (1-4): ").strip()
            if phase.isdigit() and 1 <= int(phase) <= 4:
                developer.show_phase_plan(int(phase))
            else:
                print("❌ Invalid phase number")
                
        elif choice == "3":
            developer.run_tests()
            
        elif choice == "4":
            phase = input("Enter phase number for branch (1-4): ").strip()
            if phase.isdigit() and 1 <= int(phase) <= 4:
                developer.create_phase_branch(int(phase))
            else:
                print("❌ Invalid phase number")
                
        elif choice == "5":
            print("👋 Happy coding!")
            break
            
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    main()

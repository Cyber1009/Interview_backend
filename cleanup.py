#!/usr/bin/env python
"""
Interview Backend Structure Cleanup Script

This script helps with transitioning from the old flat structure to the new hierarchical structure
by identifying files that still use the old import patterns.

Usage:
    python cleanup.py [--update] [--verbose]

Options:
    --update   Attempt to automatically update import statements
    --verbose  Show detailed logging information
"""

import os
import re
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Import mappings from old to new paths
IMPORT_MAPPINGS = {
    r'from app\.models import (.+?)': r'from app.core.database.models import \1',
    r'from app\.database import (.+?)': r'from app.core.database.db import \1',
    r'from app\.security import (.+?)': r'from app.core.security.auth import \1',  # May need manual review
    r'from app\.config import (.+?)': r'from app.core.config import \1',
    r'from app\.db_migration import (.+?)': r'from app.core.database.migrations import \1',
    # Schema imports may need more detailed handling
    r'from app\.schemas import (.+?)': r'from app.schemas import \1',  # Marked for manual review
}

# File patterns to exclude
EXCLUDE_PATTERNS = [
    r'__pycache__',
    r'\.git',
    r'\.idea',
    r'\.venv',
    r'venv',
    r'backup_',
    r'\.py[cod]$',
    r'app/models\.py',         # Exclude compatibility layers
    r'app/database\.py',       # Exclude compatibility layers
    r'app/security\.py',       # Exclude compatibility layers
    r'app/schemas\.py',        # Exclude compatibility layers
    r'app/db_migration\.py',   # Exclude compatibility layers
]

def should_exclude(path: str) -> bool:
    """Check if a path should be excluded from analysis."""
    for pattern in EXCLUDE_PATTERNS:
        if re.search(pattern, path):
            return True
    return False

def find_python_files(root_dir: str) -> List[str]:
    """Find all Python files in the given directory."""
    python_files = []
    for dirpath, _, filenames in os.walk(root_dir):
        if should_exclude(dirpath):
            continue
        
        for filename in filenames:
            if not filename.endswith('.py') or should_exclude(filename):
                continue
            
            full_path = os.path.join(dirpath, filename)
            python_files.append(full_path)
    
    return python_files

def check_imports(file_path: str) -> List[Tuple[int, str, str]]:
    """Check for deprecated import patterns in a file."""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines):
            for old_pattern, new_pattern in IMPORT_MAPPINGS.items():
                if re.search(old_pattern, line):
                    suggested_line = re.sub(old_pattern, new_pattern, line)
                    # If suggested line has 'app.schemas import' but not specific schema, flag for manual review
                    if 'app.schemas import' in suggested_line and not re.search(r'app\.schemas\.\w+', suggested_line):
                        suggested_line = "# MANUAL REVIEW NEEDED: " + suggested_line.strip() + " # Should use specific schema module"
                    
                    issues.append((i + 1, line.strip(), suggested_line.strip()))
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
    
    return issues

def update_imports(file_path: str) -> Tuple[bool, int]:
    """Update deprecated import patterns in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        updated_content = content
        changes_made = 0
        
        for old_pattern, new_pattern in IMPORT_MAPPINGS.items():
            if 'app.schemas import' in new_pattern:
                # Skip auto-updating schema imports as they need manual review
                continue
            
            updated_version, count = re.subn(old_pattern, new_pattern, updated_content)
            if count > 0:
                updated_content = updated_version
                changes_made += count
        
        if changes_made > 0:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            return True, changes_made
        
        return False, 0
    except Exception as e:
        logger.error(f"Error updating {file_path}: {str(e)}")
        return False, 0

def analyze_project(root_dir: str, verbose: bool = False, update: bool = False) -> Dict:
    """Analyze the project structure and find deprecated imports."""
    python_files = find_python_files(root_dir)
    logger.info(f"Found {len(python_files)} Python files to analyze")
    
    results = {
        'total_files': len(python_files),
        'files_with_issues': 0,
        'total_issues': 0,
        'files_updated': 0,
        'total_updates': 0,
        'issues_by_pattern': {},
        'files_with_issues_list': []
    }
    
    for file_path in python_files:
        rel_path = os.path.relpath(file_path, root_dir)
        
        if update:
            updated, count = update_imports(file_path)
            if updated:
                results['files_updated'] += 1
                results['total_updates'] += count
                logger.info(f"Updated {count} imports in {rel_path}")
        
        issues = check_imports(file_path)
        
        if issues:
            results['files_with_issues'] += 1
            results['total_issues'] += len(issues)
            results['files_with_issues_list'].append(rel_path)
            
            if verbose:
                logger.info(f"\nIssues in {rel_path}:")
                for line_num, old_line, new_line in issues:
                    logger.info(f"  Line {line_num}:")
                    logger.info(f"    OLD: {old_line}")
                    logger.info(f"    NEW: {new_line}")
            
            # Count issues by pattern
            for _, old_line, _ in issues:
                for pattern in IMPORT_MAPPINGS.keys():
                    if re.search(pattern, old_line):
                        pattern_name = pattern.replace(r'\.', '.').replace('(.*)', 'X')
                        if pattern_name not in results['issues_by_pattern']:
                            results['issues_by_pattern'][pattern_name] = 0
                        results['issues_by_pattern'][pattern_name] += 1
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Analyze and cleanup project structure")
    parser.add_argument("--update", action="store_true", help="Automatically update import statements where possible")
    parser.add_argument("--verbose", action="store_true", help="Show detailed logging")
    args = parser.parse_args()
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    logger.info("Starting project structure analysis...")
    results = analyze_project(root_dir, args.verbose, args.update)
    
    logger.info("\nAnalysis Summary:")
    logger.info(f"Total Python files scanned: {results['total_files']}")
    logger.info(f"Files with deprecated imports: {results['files_with_issues']}")
    logger.info(f"Total deprecated import statements: {results['total_issues']}")
    
    if args.update:
        logger.info(f"Files updated: {results['files_updated']}")
        logger.info(f"Import statements updated: {results['total_updates']}")
    
    if results['issues_by_pattern']:
        logger.info("\nIssues by import pattern:")
        for pattern, count in results['issues_by_pattern'].items():
            logger.info(f"  {pattern}: {count}")
    
    if results['files_with_issues_list']:
        logger.info("\nFiles with issues:")
        for file_path in results['files_with_issues_list']:
            logger.info(f"  - {file_path}")
        
        # Create improvements.md file with migration suggestions
        with open(os.path.join(root_dir, "IMPROVEMENTS.md"), "w", encoding="utf-8") as f:
            f.write("# Project Structure Improvement Suggestions\n\n")
            f.write("The following files contain deprecated import statements that should be updated:\n\n")
            
            for file_path in results['files_with_issues_list']:
                f.write(f"- `{file_path}`\n")
            
            f.write("\n## Import Pattern Migration Guide\n\n")
            f.write("Update your import statements according to these patterns:\n\n")
            for old, new in IMPORT_MAPPINGS.items():
                old_readable = old.replace(r'\.', '.').replace(r'from app', 'from app').replace(r'import (.+?)', 'import X')
                new_readable = new.replace(r'\.', '.').replace(r'from app', 'from app').replace(r'import \1', 'import X')
                
                # Handle schema imports differently
                if 'app.schemas' in new_readable and not re.search(r'app\.schemas\.\w+', new_readable):
                    f.write(f"- `{old_readable}` → Determine appropriate schema module:\n")
                    f.write("  - `from app.schemas.auth_schemas import X` (for authentication schemas)\n")
                    f.write("  - `from app.schemas.interview_schemas import X` (for interview schemas)\n")
                    f.write("  - `from app.schemas.payment_schemas import X` (for payment schemas)\n")
                    f.write("  - `from app.schemas.recording_schemas import X` (for recording schemas)\n")
                    f.write("  - `from app.schemas.theme_schemas import X` (for theme schemas)\n")
                else:
                    f.write(f"- `{old_readable}` → `{new_readable}`\n")
            
            f.write("\n## Next Steps\n\n")
            f.write("1. Update imports in the affected files\n")
            f.write("2. Run tests to ensure everything works correctly\n")
            f.write("3. Run this cleanup script again to verify all issues are resolved\n")
            f.write("4. Once all files are updated, consider removing the compatibility layers\n")
        
        logger.info(f"\nSuggestions written to {os.path.join(root_dir, 'IMPROVEMENTS.md')}")
    
    logger.info("\nDone!")

if __name__ == "__main__":
    main()
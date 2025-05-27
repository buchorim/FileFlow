#!/usr/bin/env python3
"""
FileFlow Mobile - Enhanced Android/Termux File Manager
Smart file organization tool with threading, rich UI, and advanced features

Author: Arinara Developer Team
Version: 2.0 Enhanced
Platform: Android (Termux), Linux, Cross-platform

Requirements:
pip install rich

Features:
- Multi-threading for better performance
- Rich library for beautiful UI
- Real-time file scanning display
- Time estimation for operations
- Dynamic path changing
- Enhanced progress tracking
"""

import os
import sys
import hashlib
import shutil
import time
import threading
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import re
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed

# Rich library imports
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn, MofNCompleteColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich.prompt import Prompt, Confirm
    from rich.tree import Tree
    from rich.columns import Columns
    from rich.align import Align
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("⚠️  Rich library not found. Install with: pip install rich")
    print("📱 Falling back to basic UI...")

class FileFlowMobileEnhanced:
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.android_paths = {
            'downloads': '/sdcard/Download',
            'pictures': '/sdcard/Pictures', 
            'dcim': '/sdcard/DCIM',
            'documents': '/sdcard/Documents',
            'music': '/sdcard/Music',
            'videos': '/sdcard/Movies',
            'whatsapp': '/sdcard/WhatsApp/Media',
            'telegram': '/sdcard/Telegram',
            'home': str(Path.home()),
            'current': '.'
        }
        
        # Enhanced file categories
        self.file_categories = {
            'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.svg', '.tiff', '.ico'],
            'Videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv'],
            'Audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus'],
            'Documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx'],
            'Archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.lzma'],
            'Code': ['.py', '.js', '.html', '.css', '.java', '.cpp', '.c', '.php', '.rb', '.go', '.rs'],
            'APK': ['.apk', '.xapk', '.aab'],
            'Fonts': ['.ttf', '.otf', '.woff', '.woff2'],
            'Ebooks': ['.epub', '.mobi', '.azw', '.azw3']
        }
        
        self.temp_extensions = ['.tmp', '.temp', '.bak', '.log', '~', '.swp', '.cache', '.crdownload', '.part']
        self.scan_queue = queue.Queue()
        self.current_path = Path('.')
        self.stats = {
            'files_processed': 0,
            'start_time': None,
            'estimated_time': None
        }
        
    def clear_screen(self):
        """Clear terminal screen"""
        if RICH_AVAILABLE:
            self.console.clear()
        else:
            os.system('clear' if os.name == 'posix' else 'cls')
    
    def print_header(self):
        """Display enhanced app header"""
        self.clear_screen()
        if RICH_AVAILABLE:
            header = Panel.fit(
                "[bold blue]📱 FileFlow Mobile Enhanced v2.0 📱[/bold blue]\n"
                "[green]Smart File Manager with Threading & Rich UI[/green]\n"
                "[dim]Optimized for Android/Termux[/dim]",
                box=box.DOUBLE,
                padding=(1, 2)
            )
            self.console.print(header)
            self.console.print()
        else:
            print("📱" + "="*40 + "📱")
            print("   🗂️  FileFlow Mobile Enhanced v2.0  🗂️")
            print("   Smart File Manager with Threading")
            print("📱" + "="*40 + "📱\n")
    
    def format_size(self, bytes_size):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f}{unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f}TB"
    
    def estimate_time_remaining(self, current, total, start_time):
        """Estimate time remaining for operation"""
        if current == 0:
            return "Calculating..."
        
        elapsed = time.time() - start_time
        rate = current / elapsed
        remaining = (total - current) / rate if rate > 0 else 0
        
        if remaining < 60:
            return f"{remaining:.0f}s"
        elif remaining < 3600:
            return f"{remaining/60:.0f}m {remaining%60:.0f}s"
        else:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            return f"{hours:.0f}h {minutes:.0f}m"
    
    def get_android_path(self, path_key):
        """Get Android-specific path with fallback"""
        if path_key in self.android_paths:
            android_path = Path(self.android_paths[path_key])
            if android_path.exists():
                return android_path
            else:
                if RICH_AVAILABLE:
                    self.console.print(f"[yellow]⚠️  Path {android_path} not accessible[/yellow]")
                else:
                    print(f"⚠️  Path {android_path} not accessible")
                return Path('.')
        return Path(path_key)
    
    def interactive_path_selector(self, allow_change=True):
        """Enhanced interactive path selection"""
        if RICH_AVAILABLE:
            table = Table(title="📂 Select Directory", box=box.ROUNDED)
            table.add_column("Option", style="cyan", no_wrap=True)
            table.add_column("Path", style="green")
            table.add_column("Description", style="dim")
            
            paths = [
                ("1", "Downloads", "/sdcard/Download", "Downloaded files"),
                ("2", "Pictures", "/sdcard/Pictures", "Photos and images"), 
                ("3", "DCIM", "/sdcard/DCIM", "Camera photos"),
                ("4", "Documents", "/sdcard/Documents", "Text and office files"),
                ("5", "Music", "/sdcard/Music", "Audio files"),
                ("6", "Videos", "/sdcard/Movies", "Video files"),
                ("7", "WhatsApp", "/sdcard/WhatsApp/Media", "WhatsApp media"),
                ("8", "Telegram", "/sdcard/Telegram", "Telegram files"),
                ("9", "Current", str(self.current_path), "Current directory"),
                ("0", "Custom", "Enter manually", "Custom path")
            ]
            
            if allow_change:
                paths.append(("c", "Change", "Update paths", "Modify file categories"))
            
            for num, name, path, desc in paths:
                table.add_row(num, path, desc)
            
            self.console.print(table)
        else:
            print("📂 Select Directory:")
            print("-" * 30)
            paths = [
                ("1", "Downloads", "downloads"),
                ("2", "Pictures", "pictures"), 
                ("3", "DCIM (Camera)", "dcim"),
                ("4", "Documents", "documents"),
                ("5", "Music", "music"),
                ("6", "Videos", "videos"),
                ("7", "WhatsApp Media", "whatsapp"),
                ("8", "Telegram", "telegram"),
                ("9", "Current Folder", "current"),
                ("0", "Custom Path", "custom")
            ]
            
            for num, name, _ in paths:
                print(f"  {num}. {name}")
        
        while True:
            if RICH_AVAILABLE:
                choice = Prompt.ask("👆 Enter choice", choices=["1","2","3","4","5","6","7","8","9","0","c"] if allow_change else ["1","2","3","4","5","6","7","8","9","0"])
            else:
                choice = input(f"\n👆 Enter choice (1-9, 0{', c' if allow_change else ''} for custom): ").strip()
            
            if choice == "c" and allow_change:
                self.change_file_paths()
                continue
            elif choice == "0":
                if RICH_AVAILABLE:
                    custom_path = Prompt.ask("📁 Enter custom path")
                else:
                    custom_path = input("📁 Enter custom path: ").strip()
                self.current_path = Path(custom_path)
                return self.current_path
            elif choice in ["1","2","3","4","5","6","7","8","9"]:
                path_mapping = {
                    "1": "downloads", "2": "pictures", "3": "dcim", "4": "documents",
                    "5": "music", "6": "videos", "7": "whatsapp", "8": "telegram", "9": "current"
                }
                selected_path = self.get_android_path(path_mapping[choice])
                self.current_path = selected_path
                return selected_path
            else:
                if RICH_AVAILABLE:
                    self.console.print("[red]❌ Invalid choice. Try again.[/red]")
                else:
                    print("❌ Invalid choice. Try again.")
    
    def change_file_paths(self):
        """Allow users to modify file organization paths"""
        if RICH_AVAILABLE:
            self.console.print(Panel("🔧 Change File Organization Paths", box=box.ROUNDED))
            
            table = Table(title="Current File Categories", box=box.SIMPLE)
            table.add_column("Category", style="cyan")
            table.add_column("Extensions", style="green")
            
            for category, extensions in self.file_categories.items():
                ext_str = ", ".join(extensions[:5])  # Show first 5 extensions
                if len(extensions) > 5:
                    ext_str += f" (+{len(extensions)-5} more)"
                table.add_row(category, ext_str)
            
            self.console.print(table)
            
            action = Prompt.ask("What would you like to do?", 
                              choices=["add_category", "modify_category", "add_extension", "back"],
                              default="back")
            
            if action == "add_category":
                category_name = Prompt.ask("Enter new category name")
                extensions = Prompt.ask("Enter extensions (comma-separated, with dots)").split(',')
                extensions = [ext.strip() for ext in extensions if ext.strip().startswith('.')]
                self.file_categories[category_name] = extensions
                self.console.print(f"[green]✅ Added category '{category_name}' with {len(extensions)} extensions[/green]")
                
            elif action == "modify_category":
                category = Prompt.ask("Enter category to modify", 
                                    choices=list(self.file_categories.keys()))
                extensions = Prompt.ask(f"Enter new extensions for {category} (comma-separated)").split(',')
                extensions = [ext.strip() for ext in extensions if ext.strip().startswith('.')]
                self.file_categories[category] = extensions
                self.console.print(f"[green]✅ Updated category '{category}'[/green]")
                
            elif action == "add_extension":
                category = Prompt.ask("Add extension to which category?", 
                                    choices=list(self.file_categories.keys()))
                extension = Prompt.ask("Enter extension (with dot)")
                if extension.startswith('.'):
                    self.file_categories[category].append(extension)
                    self.console.print(f"[green]✅ Added '{extension}' to '{category}'[/green]")
                
            input("\nPress Enter to continue...")
    
    def scan_files_threaded(self, path, max_workers=4):
        """Multi-threaded file scanning with real-time display"""
        path = Path(path)
        if not path.exists():
            if RICH_AVAILABLE:
                self.console.print(f"[red]❌ Path {path} doesn't exist[/red]")
            else:
                print(f"❌ Path {path} doesn't exist")
            return []
        
        all_files = []
        scan_results_queue = queue.Queue()
        
        def scan_directory(directory):
            """Scan a single directory"""
            local_files = []
            try:
                for item in directory.iterdir():
                    if item.is_file():
                        local_files.append(item)
                        scan_results_queue.put(('file', item))
                    elif item.is_dir():
                        scan_results_queue.put(('dir', item))
            except PermissionError:
                scan_results_queue.put(('error', f"Permission denied: {directory}"))
            return local_files
        
        # Get all directories first
        directories = [path]
        for item in path.rglob("*"):
            if item.is_dir():
                directories.append(item)
        
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeRemainingColumn(),
                console=self.console
            ) as progress:
                
                scan_task = progress.add_task("🔍 Scanning directories...", total=len(directories))
                file_display_task = progress.add_task("📄 Files found: 0", total=None)
                
                # Use ThreadPoolExecutor for parallel scanning
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    # Submit all directory scan tasks
                    future_to_dir = {executor.submit(scan_directory, directory): directory 
                                   for directory in directories}
                    
                    completed_dirs = 0
                    file_count = 0
                    
                    # Process results as they come in
                    for future in as_completed(future_to_dir):
                        directory = future_to_dir[future]
                        try:
                            directory_files = future.result()
                            all_files.extend(directory_files)
                            
                            # Process any queued scan results
                            while not scan_results_queue.empty():
                                try:
                                    result_type, result_data = scan_results_queue.get_nowait()
                                    if result_type == 'file':
                                        file_count += 1
                                        progress.update(file_display_task, 
                                                      description=f"📄 Files found: {file_count} - Current: {result_data.name[:30]}...")
                                except queue.Empty:
                                    break
                            
                            completed_dirs += 1
                            progress.update(scan_task, completed=completed_dirs)
                            
                        except Exception as exc:
                            progress.update(scan_task, 
                                          description=f"🔍 Scanning directories... (Error in {directory.name})")
                
                progress.update(file_display_task, description=f"✅ Scan complete! Found {len(all_files)} files")
        else:
            print("🔍 Scanning files...")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(scan_directory, directory) for directory in directories]
                for i, future in enumerate(as_completed(futures)):
                    try:
                        directory_files = future.result()
                        all_files.extend(directory_files)
                        print(f"\rScanned {i+1}/{len(directories)} directories, found {len(all_files)} files", end="")
                    except Exception:
                        continue
            print()
        
        return all_files
    
    def smart_organize_threaded(self, path, confirm=True, max_workers=4):
        """Enhanced smart organization with threading"""
        path = Path(path)
        if not path.exists():
            if RICH_AVAILABLE:
                self.console.print(f"[red]❌ Path {path} doesn't exist[/red]")
            else:
                print(f"❌ Path {path} doesn't exist")
            return
        
        if RICH_AVAILABLE:
            self.console.print(f"🔍 Analyzing: [cyan]{path}[/cyan]")
        else:
            print(f"🔍 Analyzing: {path}")
        
        # Scan files with threading
        all_files = self.scan_files_threaded(path, max_workers)
        
        if not all_files:
            if RICH_AVAILABLE:
                self.console.print("📂 No files to organize in this directory")
            else:
                print("📂 No files to organize in this directory")
            return
        
        total_files = len(all_files)
        if RICH_AVAILABLE:
            self.console.print(f"📊 Found [bold cyan]{total_files}[/bold cyan] files to organize")
        else:
            print(f"📊 Found {total_files} files to organize")
        
        if confirm:
            if RICH_AVAILABLE:
                proceed = Confirm.ask("🤔 Continue with organization?")
            else:
                proceed = input("🤔 Continue with organization? (y/N): ").lower() == 'y'
            
            if not proceed:
                if RICH_AVAILABLE:
                    self.console.print("[red]❌ Operation cancelled[/red]")
                else:
                    print("❌ Operation cancelled")
                return
        
        # Organize files with threading and progress tracking
        organized_count = 0
        error_count = 0
        start_time = time.time()
        
        def organize_file(file_path):
            """Organize a single file"""
            file_ext = file_path.suffix.lower()
            category_found = False
            
            # Find matching category
            for category, extensions in self.file_categories.items():
                if file_ext in extensions:
                    category_dir = path / category
                    category_dir.mkdir(exist_ok=True)
                    
                    try:
                        new_path = category_dir / file_path.name
                        # Handle name conflicts
                        counter = 1
                        while new_path.exists():
                            name_parts = file_path.stem, counter, file_path.suffix
                            new_path = category_dir / f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                            counter += 1
                        
                        shutil.move(str(file_path), str(new_path))
                        return 'success', category
                    except Exception as e:
                        return 'error', str(e)
            
            # Files without specific category go to 'Others'
            if not category_found and file_ext:
                others_dir = path / 'Others'
                others_dir.mkdir(exist_ok=True)
                try:
                    new_path = others_dir / file_path.name
                    counter = 1
                    while new_path.exists():
                        name_parts = file_path.stem, counter, file_path.suffix
                        f"{name_parts[0]}_{name_parts[1]}{name_parts[2]}"
                        counter += 1
                    
                    shutil.move(str(file_path), str(new_path))
                    return 'success', 'Others'
                except Exception as e:
                    return 'error', str(e)
            
            return 'skipped', 'No extension'
        
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeRemainingColumn(),
                console=self.console
            ) as progress:
                
                organize_task = progress.add_task("🗂️ Organizing files...", total=total_files)
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_file = {executor.submit(organize_file, file_path): file_path 
                                    for file_path in all_files}
                    
                    for future in as_completed(future_to_file):
                        file_path = future_to_file[future]
                        try:
                            result, info = future.result()
                            if result == 'success':
                                organized_count += 1
                            elif result == 'error':
                                error_count += 1
                            
                            progress.update(organize_task, advance=1,
                                          description=f"🗂️ Organizing: {file_path.name[:30]}...")
                            
                        except Exception as exc:
                            error_count += 1
                            progress.update(organize_task, advance=1)
            
            # Show results
            results_table = Table(title="📊 Organization Results", box=box.ROUNDED)
            results_table.add_column("Metric", style="cyan")
            results_table.add_column("Count", style="green")
            
            results_table.add_row("Total Files", str(total_files))
            results_table.add_row("Successfully Organized", str(organized_count))
            results_table.add_row("Errors", str(error_count))
            results_table.add_row("Time Taken", f"{time.time() - start_time:.1f}s")
            
            self.console.print(results_table)
        else:
            print("🗂️ Organizing files...")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(organize_file, file_path) for file_path in all_files]
                for i, future in enumerate(as_completed(futures)):
                    try:
                        result, info = future.result()
                        if result == 'success':
                            organized_count += 1
                        elif result == 'error':
                            error_count += 1
                        print(f"\rOrganized {i+1}/{total_files} files", end="")
                    except Exception:
                        error_count += 1
            
            print(f"\n✅ Successfully organized {organized_count} files!")
            if error_count > 0:
                print(f"⚠️  {error_count} errors encountered")
        
        input("\n📱 Press Enter to continue...")
    
    def find_duplicates_threaded(self, path, auto_remove=False, max_workers=4):
        """Enhanced duplicate finder with threading"""
        path = Path(path)
        if not path.exists():
            if RICH_AVAILABLE:
                self.console.print(f"[red]❌ Path {path} doesn't exist[/red]")
            else:
                print(f"❌ Path {path} doesn't exist")
            return
        
        if RICH_AVAILABLE:
            self.console.print("🔍 Scanning for duplicate files...")
            self.console.print("⏳ This might take a while for large directories")
        else:
            print("🔍 Scanning for duplicate files...")
            print("⏳ This might take a while for large directories")
        
        # Scan files
        all_files = self.scan_files_threaded(path, max_workers)
        
        if not all_files:
            if RICH_AVAILABLE:
                self.console.print("📂 No files found")
            else:
                print("📂 No files found")
            return
        
        total_files = len(all_files)
        if RICH_AVAILABLE:
            self.console.print(f"📊 Analyzing [bold cyan]{total_files}[/bold cyan] files for duplicates...")
        else:
            print(f"📊 Analyzing {total_files} files for duplicates...")
        
        # Hash files with threading
        hash_to_files = defaultdict(list)
        
        def get_file_hash(filepath):
            """Generate MD5 hash for file content"""
            hash_md5 = hashlib.md5()
            try:
                with open(filepath, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        hash_md5.update(chunk)
                return filepath, hash_md5.hexdigest()
            except Exception:
                return filepath, None
        
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TimeRemainingColumn(),
                console=self.console
            ) as progress:
                
                hash_task = progress.add_task("🔐 Computing hashes...", total=total_files)
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_file = {executor.submit(get_file_hash, file_path): file_path 
                                    for file_path in all_files}
                    
                    for future in as_completed(future_to_file):
                        file_path = future_to_file[future]
                        try:
                            filepath, file_hash = future.result()
                            if file_hash:
                                hash_to_files[file_hash].append(filepath)
                            
                            progress.update(hash_task, advance=1,
                                          description=f"🔐 Hashing: {file_path.name[:30]}...")
                            
                        except Exception:
                            progress.update(hash_task, advance=1)
        else:
            print("🔐 Computing file hashes...")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(get_file_hash, file_path) for file_path in all_files]
                for i, future in enumerate(as_completed(futures)):
                    try:
                        filepath, file_hash = future.result()
                        if file_hash:
                            hash_to_files[file_hash].append(filepath)
                        print(f"\rProcessed {i+1}/{total_files} files", end="")
                    except Exception:
                        continue
            print()
        
        # Find duplicates
        duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}
        
        if not duplicates:
            if RICH_AVAILABLE:
                self.console.print("[green]✅ No duplicates found![/green]")
            else:
                print("✅ No duplicates found!")
            input("\n📱 Press Enter to continue...")
            return
        
        total_duplicates = sum(len(files) - 1 for files in duplicates.values())
        duplicate_size = 0
        
        if RICH_AVAILABLE:
            self.console.print(f"\n🔍 Found [bold red]{len(duplicates)}[/bold red] sets of duplicates ([bold yellow]{total_duplicates}[/bold yellow] files)")
            
            # Create detailed duplicate report
            for i, (file_hash, files) in enumerate(duplicates.items(), 1):
                file_size = files[0].stat().st_size
                duplicate_size += file_size * (len(files) - 1)
                
                duplicate_table = Table(title=f"Duplicate Set #{i}", box=box.SIMPLE)
                duplicate_table.add_column("Status", style="cyan")
                duplicate_table.add_column("File Path", style="green")
                duplicate_table.add_column("Size", style="yellow")
                
                for j, file_path in enumerate(files):
                    status = "KEEP" if j == 0 else "DUPE"
                    duplicate_table.add_row(status, str(file_path), self.format_size(file_size))
                
                self.console.print(duplicate_table)
            
            self.console.print(f"\n💾 Total space wasted: [bold red]{self.format_size(duplicate_size)}[/bold red]")
        else:
            print(f"\n🔍 Found {len(duplicates)} sets of duplicates ({total_duplicates} files)")
            
            for i, (file_hash, files) in enumerate(duplicates.items(), 1):
                file_size = files[0].stat().st_size
                duplicate_size += file_size * (len(files) - 1)
                
                print(f"\n📄 Duplicate Set #{i} ({len(files)} files, {self.format_size(file_size)} each):")
                for j, file_path in enumerate(files):
                    status = "KEEP" if j == 0 else "DUPE"
                    print(f"  {status}: {file_path.name}")
            
            print(f"\n💾 Total space wasted: {self.format_size(duplicate_size)}")
        
        if auto_remove:
            if RICH_AVAILABLE:
                remove_confirm = Confirm.ask(f"🗑️  Remove {total_duplicates} duplicate files?")
            else:
                remove_confirm = input(f"\n🗑️  Remove {total_duplicates} duplicate files? (y/N): ").lower() == 'y'
            
            if remove_confirm:
                removed = 0
                for files in duplicates.values():
                    for file_path in files[1:]:  # Keep first, remove others
                        try:
                            file_path.unlink()
                            removed += 1
                        except Exception as e:
                            if RICH_AVAILABLE:
                                self.console.print(f"[red]⚠️  Failed to remove {file_path.name}: {e}[/red]")
                            else:
                                print(f"⚠️  Failed to remove {file_path.name}: {e}")
                
                if RICH_AVAILABLE:
                    self.console.print(f"[green]✅ Removed {removed} duplicate files[/green]")
                    self.console.print(f"[green]💾 Freed up {self.format_size(duplicate_size)} of space[/green]")
            
            else:
                if RICH_AVAILABLE:
                    self.console.print("[yellow]❌ Duplicate removal cancelled[/yellow]")
                else:
                    print("❌ Duplicate removal cancelled")
        
        input("\n📱 Press Enter to continue...")
    
    def clean_temp_files(self, path, confirm=True):
        """Clean temporary and cache files"""
        path = Path(path)
        if not path.exists():
            if RICH_AVAILABLE:
                self.console.print(f"[red]❌ Path {path} doesn't exist[/red]")
            else:
                print(f"❌ Path {path} doesn't exist")
            return
        
        if RICH_AVAILABLE:
            self.console.print("🧹 Scanning for temporary files...")
        else:
            print("🧹 Scanning for temporary files...")
        
        temp_files = []
        total_size = 0
        
        # Scan for temporary files
        for file_path in path.rglob("*"):
            if file_path.is_file():
                # Check by extension
                if any(file_path.name.endswith(ext) for ext in self.temp_extensions):
                    temp_files.append(file_path)
                    total_size += file_path.stat().st_size
                # Check by name patterns
                elif any(pattern in file_path.name.lower() for pattern in ['cache', 'temp', 'tmp', 'backup']):
                    temp_files.append(file_path)
                    total_size += file_path.stat().st_size
        
        if not temp_files:
            if RICH_AVAILABLE:
                self.console.print("[green]✅ No temporary files found![/green]")
            else:
                print("✅ No temporary files found!")
            input("\n📱 Press Enter to continue...")
            return
        
        if RICH_AVAILABLE:
            self.console.print(f"🗑️  Found [bold yellow]{len(temp_files)}[/bold yellow] temporary files")
            self.console.print(f"💾 Total size: [bold red]{self.format_size(total_size)}[/bold red]")
            
            # Show sample files
            temp_table = Table(title="Temporary Files Found", box=box.ROUNDED)
            temp_table.add_column("File Name", style="yellow")
            temp_table.add_column("Size", style="red")
            temp_table.add_column("Type", style="dim")
            
            for temp_file in temp_files[:10]:  # Show first 10
                file_size = temp_file.stat().st_size
                file_type = "Extension" if temp_file.suffix in self.temp_extensions else "Pattern"
                temp_table.add_row(temp_file.name[:50], self.format_size(file_size), file_type)
            
            if len(temp_files) > 10:
                temp_table.add_row(f"... and {len(temp_files) - 10} more", "", "")
            
            self.console.print(temp_table)
        else:
            print(f"🗑️  Found {len(temp_files)} temporary files")
            print(f"💾 Total size: {self.format_size(total_size)}")
            
            print("\nSample files:")
            for temp_file in temp_files[:5]:
                print(f"  - {temp_file.name}")
            if len(temp_files) > 5:
                print(f"  ... and {len(temp_files) - 5} more")
        
        if confirm:
            if RICH_AVAILABLE:
                proceed = Confirm.ask("🗑️  Delete all temporary files?")
            else:
                proceed = input("\n🗑️  Delete all temporary files? (y/N): ").lower() == 'y'
            
            if not proceed:
                if RICH_AVAILABLE:
                    self.console.print("[yellow]❌ Cleanup cancelled[/yellow]")
                else:
                    print("❌ Cleanup cancelled")
                input("\n📱 Press Enter to continue...")
                return
        
        # Delete temporary files
        deleted_count = 0
        deleted_size = 0
        
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                console=self.console
            ) as progress:
                
                delete_task = progress.add_task("🗑️  Deleting temp files...", total=len(temp_files))
                
                for temp_file in temp_files:
                    try:
                        file_size = temp_file.stat().st_size
                        temp_file.unlink()
                        deleted_count += 1
                        deleted_size += file_size
                        progress.update(delete_task, advance=1, 
                                      description=f"🗑️  Deleting: {temp_file.name[:30]}...")
                    except Exception as e:
                        progress.update(delete_task, advance=1)
        else:
            print("🗑️  Deleting temporary files...")
            for i, temp_file in enumerate(temp_files):
                try:
                    file_size = temp_file.stat().st_size
                    temp_file.unlink()
                    deleted_count += 1
                    deleted_size += file_size
                    print(f"\rDeleted {i+1}/{len(temp_files)} files", end="")
                except Exception:
                    continue
            print()
        
        if RICH_AVAILABLE:
            self.console.print(f"[green]✅ Deleted {deleted_count} temporary files[/green]")
            self.console.print(f"[green]💾 Freed up {self.format_size(deleted_size)} of space[/green]")
        else:
            print(f"✅ Deleted {deleted_count} temporary files")
            print(f"💾 Freed up {self.format_size(deleted_size)} of space")
        
        input("\n📱 Press Enter to continue...")
    
    def analyze_directory_threaded(self, path, max_workers=4):
        """Comprehensive directory analysis with threading"""
        path = Path(path)
        if not path.exists():
            if RICH_AVAILABLE:
                self.console.print(f"[red]❌ Path {path} doesn't exist[/red]")
            else:
                print(f"❌ Path {path} doesn't exist")
            return
        
        if RICH_AVAILABLE:
            self.console.print(f"📊 Analyzing directory: [cyan]{path}[/cyan]")
        else:
            print(f"📊 Analyzing directory: {path}")
        
        # Scan all files with threading
        all_files = self.scan_files_threaded(path, max_workers)
        
        if not all_files:
            if RICH_AVAILABLE:
                self.console.print("📂 No files found in directory")
            else:
                print("📂 No files found in directory")
            return
        
        # Analyze file statistics
        file_stats = {
            'total_files': len(all_files),
            'total_size': 0,
            'categories': defaultdict(lambda: {'count': 0, 'size': 0}),
            'largest_files': [],
            'extensions': Counter(),
            'oldest_file': None,
            'newest_file': None
        }
        
        def analyze_file(file_path):
            """Analyze a single file"""
            try:
                stat = file_path.stat()
                file_size = stat.st_size
                file_ext = file_path.suffix.lower()
                
                # Find category
                category = 'Others'
                for cat, extensions in self.file_categories.items():
                    if file_ext in extensions:
                        category = cat
                        break
                
                return {
                    'path': file_path,
                    'size': file_size,
                    'extension': file_ext,
                    'category': category,
                    'modified_time': stat.st_mtime
                }
            except Exception:
                return None
        
        # Analyze files with threading
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                console=self.console
            ) as progress:
                
                analyze_task = progress.add_task("📊 Analyzing files...", total=len(all_files))
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_file = {executor.submit(analyze_file, file_path): file_path 
                                    for file_path in all_files}
                    
                    for future in as_completed(future_to_file):
                        try:
                            result = future.result()
                            if result:
                                # Update statistics
                                file_stats['total_size'] += result['size']
                                file_stats['categories'][result['category']]['count'] += 1
                                file_stats['categories'][result['category']]['size'] += result['size']
                                file_stats['extensions'][result['extension']] += 1
                                
                                # Track largest files
                                file_stats['largest_files'].append((result['path'], result['size']))
                                
                                # Track oldest/newest
                                if not file_stats['oldest_file'] or result['modified_time'] < file_stats['oldest_file'][1]:
                                    file_stats['oldest_file'] = (result['path'], result['modified_time'])
                                if not file_stats['newest_file'] or result['modified_time'] > file_stats['newest_file'][1]:
                                    file_stats['newest_file'] = (result['path'], result['modified_time'])
                            
                            progress.update(analyze_task, advance=1)
                        except Exception:
                            progress.update(analyze_task, advance=1)
        else:
            print("📊 Analyzing files...")
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(analyze_file, file_path) for file_path in all_files]
                for i, future in enumerate(as_completed(futures)):
                    try:
                        result = future.result()
                        if result:
                            file_stats['total_size'] += result['size']
                            file_stats['categories'][result['category']]['count'] += 1
                            file_stats['categories'][result['category']]['size'] += result['size']
                            file_stats['extensions'][result['extension']] += 1
                            file_stats['largest_files'].append((result['path'], result['size']))
                            
                            if not file_stats['oldest_file'] or result['modified_time'] < file_stats['oldest_file'][1]:
                                file_stats['oldest_file'] = (result['path'], result['modified_time'])
                            if not file_stats['newest_file'] or result['modified_time'] > file_stats['newest_file'][1]:
                                file_stats['newest_file'] = (result['path'], result['modified_time'])
                        
                        print(f"\rAnalyzed {i+1}/{len(all_files)} files", end="")
                    except Exception:
                        continue
            print()
        
        # Sort largest files
        file_stats['largest_files'].sort(key=lambda x: x[1], reverse=True)
        file_stats['largest_files'] = file_stats['largest_files'][:10]
        
        # Display comprehensive analysis
        if RICH_AVAILABLE:
            # Overview table
            overview_table = Table(title="📊 Directory Analysis Overview", box=box.ROUNDED)
            overview_table.add_column("Metric", style="cyan")
            overview_table.add_column("Value", style="green")
            
            overview_table.add_row("Total Files", str(file_stats['total_files']))
            overview_table.add_row("Total Size", self.format_size(file_stats['total_size']))
            overview_table.add_row("Average File Size", self.format_size(file_stats['total_size'] // file_stats['total_files']) if file_stats['total_files'] > 0 else "0B")
            overview_table.add_row("Unique Extensions", str(len(file_stats['extensions'])))
            
            if file_stats['oldest_file']:
                oldest_date = datetime.fromtimestamp(file_stats['oldest_file'][1]).strftime('%Y-%m-%d %H:%M')
                overview_table.add_row("Oldest File", f"{file_stats['oldest_file'][0].name} ({oldest_date})")
            
            if file_stats['newest_file']:
                newest_date = datetime.fromtimestamp(file_stats['newest_file'][1]).strftime('%Y-%m-%d %H:%M')
                overview_table.add_row("Newest File", f"{file_stats['newest_file'][0].name} ({newest_date})")
            
            self.console.print(overview_table)
            
            # Categories breakdown
            if file_stats['categories']:
                cat_table = Table(title="📁 File Categories", box=box.ROUNDED)
                cat_table.add_column("Category", style="cyan")
                cat_table.add_column("Files", style="yellow")
                cat_table.add_column("Size", style="green")
                cat_table.add_column("Percentage", style="magenta")
                
                for category, stats in sorted(file_stats['categories'].items(), key=lambda x: x[1]['size'], reverse=True):
                    percentage = (stats['size'] / file_stats['total_size'] * 100) if file_stats['total_size'] > 0 else 0
                    cat_table.add_row(
                        category,
                        str(stats['count']),
                        self.format_size(stats['size']),
                        f"{percentage:.1f}%"
                    )
                
                self.console.print(cat_table)
            
            # Largest files
            if file_stats['largest_files']:
                large_table = Table(title="📈 Largest Files", box=box.ROUNDED)
                large_table.add_column("Rank", style="dim")
                large_table.add_column("File Name", style="cyan")
                large_table.add_column("Size", style="red")
                
                for i, (file_path, size) in enumerate(file_stats['largest_files'], 1):
                    large_table.add_row(str(i), file_path.name[:50], self.format_size(size))
                
                self.console.print(large_table)
            
            # Top extensions
            if file_stats['extensions']:
                ext_table = Table(title="🔧 Most Common Extensions", box=box.ROUNDED)
                ext_table.add_column("Extension", style="cyan")
                ext_table.add_column("Count", style="green")
                
                for ext, count in file_stats['extensions'].most_common(10):
                    ext_display = ext if ext else "(no extension)"
                    ext_table.add_row(ext_display, str(count))
                
                self.console.print(ext_table)
        else:
            print(f"\n📊 Directory Analysis Results:")
            print(f"==========================================")
            print(f"Total Files: {file_stats['total_files']}")
            print(f"Total Size: {self.format_size(file_stats['total_size'])}")
            print(f"Average File Size: {self.format_size(file_stats['total_size'] // file_stats['total_files']) if file_stats['total_files'] > 0 else '0B'}")
            
            print(f"\n📁 File Categories:")
            for category, stats in sorted(file_stats['categories'].items(), key=lambda x: x[1]['size'], reverse=True):
                percentage = (stats['size'] / file_stats['total_size'] * 100) if file_stats['total_size'] > 0 else 0
                print(f"  {category}: {stats['count']} files, {self.format_size(stats['size'])} ({percentage:.1f}%)")
            
            print(f"\n📈 Largest Files:")
            for i, (file_path, size) in enumerate(file_stats['largest_files'][:5], 1):
                print(f"  {i}. {file_path.name}: {self.format_size(size)}")
        
        input("\n📱 Press Enter to continue...")
    
    def show_directory_tree(self, path, max_depth=3):
        """Display directory tree structure"""
        path = Path(path)
        if not path.exists():
            if RICH_AVAILABLE:
                self.console.print(f"[red]❌ Path {path} doesn't exist[/red]")
            else:
                print(f"❌ Path {path} doesn't exist")
            return
        
        if RICH_AVAILABLE:
            tree = Tree(f"📁 {path.name or str(path)}", guide_style="bold bright_blue")
            
            def add_to_tree(current_path, tree_node, depth=0):
                if depth >= max_depth:
                    return
                
                try:
                    items = sorted(current_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                    dirs = [item for item in items if item.is_dir()]
                    files = [item for item in items if item.is_file()]
                    
                    # Add directories first
                    for directory in dirs[:10]:  # Limit to 10 directories per level
                        dir_branch = tree_node.add(f"📁 {directory.name}", style="blue")
                        add_to_tree(directory, dir_branch, depth + 1)
                    
                    if len(dirs) > 10:
                        tree_node.add(f"📁 ... and {len(dirs) - 10} more directories", style="dim")
                    
                    # Add files
                    for file_path in files[:10]:  # Limit to 10 files per level
                        file_size = self.format_size(file_path.stat().st_size)
                        tree_node.add(f"📄 {file_path.name} ({file_size})", style="green")
                    
                    if len(files) > 10:
                        tree_node.add(f"📄 ... and {len(files) - 10} more files", style="dim")
                
                except PermissionError:
                    tree_node.add("❌ Permission denied", style="red")
                except Exception as e:
                    tree_node.add(f"❌ Error: {str(e)}", style="red")
            
            add_to_tree(path, tree)
            self.console.print(tree)
        else:
            def print_tree(current_path, prefix="", depth=0):
                if depth >= max_depth:
                    return
                
                try:
                    items = sorted(current_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
                    dirs = [item for item in items if item.is_dir()]
                    files = [item for item in items if item.is_file()]
                    
                    # Print directories
                    for i, directory in enumerate(dirs[:5]):
                        is_last_dir = i == len(dirs[:5]) - 1 and len(files) == 0
                        current_prefix = "└── " if is_last_dir else "├── "
                        print(f"{prefix}{current_prefix}📁 {directory.name}/")
                        
                        next_prefix = prefix + ("    " if is_last_dir else "│   ")
                        print_tree(directory, next_prefix, depth + 1)
                    
                    if len(dirs) > 5:
                        print(f"{prefix}├── 📁 ... and {len(dirs) - 5} more directories")
                    
                    # Print files
                    for i, file_path in enumerate(files[:5]):
                        is_last = i == len(files[:5]) - 1
                        current_prefix = "└── " if is_last else "├── "
                        file_size = self.format_size(file_path.stat().st_size)
                        print(f"{prefix}{current_prefix}📄 {file_path.name} ({file_size})")
                    
                    if len(files) > 5:
                        print(f"{prefix}└── 📄 ... and {len(files) - 5} more files")
                
                except PermissionError:
                    print(f"{prefix}└── ❌ Permission denied")
                except Exception as e:
                    print(f"{prefix}└── ❌ Error: {str(e)}")
            
            print(f"📁 Directory Tree: {path}")
            print("=" * 50)
            print_tree(path)
        
        input("\n📱 Press Enter to continue...")
    
    def main_menu(self):
        """Enhanced main menu with all features"""
        while True:
            self.print_header()
            
            if RICH_AVAILABLE:
                menu_table = Table(title="🔧 FileFlow Mobile Enhanced - Main Menu", box=box.ROUNDED)
                menu_table.add_column("Option", style="cyan", no_wrap=True)
                menu_table.add_column("Feature", style="green")
                menu_table.add_column("Description", style="dim")
                
                menu_options = [
                    ("1", "Smart Organize", "Auto-organize files by type with threading"),
                    ("2", "Find Duplicates", "Find and remove duplicate files"),
                    ("3", "Clean Temp Files", "Remove temporary and cache files"),
                    ("4", "Directory Analysis", "Comprehensive directory statistics"),
                    ("5", "Directory Tree", "Visual directory structure display"),
                    ("6", "Change Directory", "Switch to different directory"),
                    ("7", "Settings", "Modify file categories and paths"),
                    ("0", "Exit", "Quit FileFlow Mobile Enhanced")
                ]
                
                for option, feature, description in menu_options:
                    menu_table.add_row(option, feature, description)
                
                self.console.print(menu_table)
                
                # Show current path
                current_info = Panel(
                    f"📂 Current Directory: [cyan]{self.current_path}[/cyan]",
                    box=box.SIMPLE,
                    padding=(0, 1)
                )
                self.console.print(current_info)
                
                choice = Prompt.ask("👆 Select option", choices=["1","2","3","4","5","6","7","0"])
            else:
                print("🔧 FileFlow Mobile Enhanced - Main Menu")
                print("=" * 45)
                print("1. 🗂️  Smart Organize Files")
                print("2. 🔍 Find Duplicate Files")
                print("3. 🧹 Clean Temporary Files")
                print("4. 📊 Directory Analysis")
                print("5. 🌳 Directory Tree View")
                print("6. 📂 Change Directory")
                print("7. ⚙️  Settings")
                print("0. 🚪 Exit")
                print("-" * 45)
                print(f"📂 Current Directory: {self.current_path}")
                
                choice = input("\n👆 Select option (0-7): ").strip()
            
            if choice == "1":
                self.smart_organize_threaded(self.current_path)
            elif choice == "2":
                self.find_duplicates_threaded(self.current_path, auto_remove=True)
            elif choice == "3":
                self.clean_temp_files(self.current_path)
            elif choice == "4":
                self.analyze_directory_threaded(self.current_path)
            elif choice == "5":
                self.show_directory_tree(self.current_path)
            elif choice == "6":
                self.current_path = self.interactive_path_selector()
            elif choice == "7":
                self.change_file_paths()
            elif choice == "0":
                if RICH_AVAILABLE:
                    self.console.print("\n[green]👋 Thank you for using FileFlow Mobile Enhanced![/green]")
                    self.console.print("[dim]Stay organized! 📱✨[/dim]")
                else:
                    print("\n👋 Thank you for using FileFlow Mobile Enhanced!")
                    print("Stay organized! 📱✨")
                break
            else:
                if RICH_AVAILABLE:
                    self.console.print("[red]❌ Invalid choice. Please try again.[/red]")
                else:
                    print("❌ Invalid choice. Please try again.")
                input("Press Enter to continue...")

def main():
    """Main entry point with error handling"""
    try:
        # Check if we're running on Android/Termux
        is_android = 'ANDROID_ROOT' in os.environ or 'PREFIX' in os.environ
        
        if is_android and RICH_AVAILABLE:
            console = Console()
            console.print("📱 [green]Android/Termux detected![/green]")
            console.print("🚀 [blue]Starting FileFlow Mobile Enhanced...[/blue]")
            time.sleep(1)
        elif is_android and not RICH_AVAILABLE:
            print("📱 Android/Termux detected!")
            print("🚀 Starting FileFlow Mobile Enhanced...")
            time.sleep(1)
        
        # Initialize and run the file manager
        file_manager = FileFlowMobileEnhanced()
        file_manager.main_menu()
        
    except KeyboardInterrupt:
        if RICH_AVAILABLE:
            console = Console()
            console.print("\n[yellow]⚠️  Operation interrupted by user[/yellow]")
        else:
            print("\n⚠️  Operation interrupted by user")
    except Exception as e:
        if RICH_AVAILABLE:
            console = Console()
            console.print(f"[red]❌ Unexpected error: {str(e)}[/red]")
            console.print("[dim]Please report this issue if it persists.[/dim]")
        else:
            print(f"❌ Unexpected error: {str(e)}")
            print("Please report this issue if it persists.")

if __name__ == "__main__":
    main()

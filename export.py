import os
import logging
from pathlib import Path
from typing import List, Set, Dict, Optional
from dataclasses import dataclass
import yaml
from concurrent.futures import ThreadPoolExecutor
import shutil
from io import StringIO

@dataclass
class FileProcessorConfig:
    extensions: Set[str]
    ignored_dirs: Set[str]
    ignored_files: Set[str]
    source_dir: Path
    output_dir: Path
    text_output: Path
    mirror_dir_structure: bool = False
    max_workers: int = 4

@dataclass
class ProcessingResults:
    tree_output: str
    combined_output: str

class FileProcessor:
    def __init__(self, config: FileProcessorConfig):
        self.config = config
        self.processed_files: List[Path] = []
        self.tree_output: Optional[str] = None
        self.combined_output: Optional[str] = None
        self.setup_logging()
        
    def setup_logging(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('file_processor.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def load_config(config_path: str) -> FileProcessorConfig:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                config_data = yaml.safe_load(f)
                return FileProcessorConfig(
                    extensions=set(config_data.get('extensions', [])),
                    ignored_dirs=set(config_data.get('ignored_dirs', [])),
                    ignored_files=set(config_data.get('ignored_files', [])),
                    source_dir=Path(config_data.get('source_dir', '.')),
                    output_dir=Path(config_data.get('output_dir', 'output')),
                    text_output=Path(config_data.get('text_output', '.')),
                    mirror_dir_structure=config_data.get('mirror_dir_structure', False),
                    max_workers=config_data.get('max_workers', 4)
                )
        except Exception as e:
            raise RuntimeError(f"Failed to load config: {str(e)}")

    def generate_unique_filename(self, base_path: Path, filename: str) -> Path:
        """Generate a unique filename in the given directory."""
        path = Path(base_path) / filename
        if not path.exists():
            return path
        
        name, ext = path.stem, path.suffix
        counter = 1
        while True:
            new_path = Path(base_path) / f"{name}_{counter}{ext}"
            if not new_path.exists():
                return new_path
            counter += 1

    def process_file(self, file_path: Path) -> Dict[str, str]:
        """Process a single file and return its content and metadata."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                return {
                    'path': str(file_path.relative_to(self.config.source_dir)),
                    'content': content
                }
        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {str(e)}")
            return None

    def write_output_file(self, file_data: Dict[str, str]) -> None:
        """Write processed file to output directory."""
        if not file_data:
            return

        try:
            if self.config.mirror_dir_structure:
                rel_path = Path(file_data['path'])
                output_path = self.config.output_dir / rel_path
            else:
                # Original flat structure
                output_path = self.config.output_dir / Path(file_data['path']).name
                output_path = self.generate_unique_filename(self.config.output_dir, output_path.name)
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(file_data['content'])
            
            self.logger.info(f"Written: {output_path}")
            self.processed_files.append(output_path)
        except Exception as e:
            self.logger.error(f"Error writing output file: {str(e)}")

    def should_process_file(self, file_path: Path) -> bool:
        """Determine if a file should be processed based on configuration."""
        return (
            any(str(file_path).endswith(ext) for ext in self.config.extensions)
            and file_path.name not in self.config.ignored_files
        )

    def process_directory(self) -> ProcessingResults:
        """Process all files in the directory structure and return results."""
        try:
            # Clear output directory
            if self.config.output_dir.exists():
                shutil.rmtree(self.config.output_dir)
            self.config.output_dir.mkdir(parents=True)

            # Collect all files to process
            files_to_process = []
            for root, dirs, files in os.walk(self.config.source_dir):
                dirs[:] = [d for d in dirs if d not in self.config.ignored_dirs]
                
                for file in files:
                    file_path = Path(root) / file
                    if self.should_process_file(file_path):
                        files_to_process.append(file_path)

            # Process files in parallel
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                for file_data in executor.map(self.process_file, files_to_process):
                    self.write_output_file(file_data)

            # Generate outputs
            tree_output = self.generate_tree_output()
            combined_output = self.generate_combined_output()
            
            return ProcessingResults(
                tree_output=tree_output,
                combined_output=combined_output
            )
            
        except Exception as e:
            self.logger.error(f"Error during directory processing: {str(e)}")
            raise

    def generate_tree_output(self) -> str:
        """Generate directory tree structure and return as string."""
        try:
            tree_content = self._generate_tree(self.config.source_dir)
            tree_text = '\n'.join(tree_content)
            
            self.config.text_output.mkdir(parents=True, exist_ok=True)
            
            tree_file = self.config.text_output.absolute() / 'combined.tree.txt'
            with open(tree_file, 'w', encoding='utf-8') as f:
                f.write(tree_text)
            self.logger.info(f"Generated tree structure: {tree_file}")
            
            return tree_text
        except Exception as e:
            self.logger.error(f"Error generating tree output: {str(e)}")
            return ""

    def generate_combined_output(self) -> str:
        """Generate combined file content and return as string."""
        try:
            combined_content = []
            for file_path in self.processed_files:
                with open(file_path, 'r', encoding='utf-8') as f:
                    combined_content.append(f"File: {file_path}\n{f.read()}\n\n")
            
            combined_text = ''.join(combined_content)
            
            self.config.text_output.mkdir(parents=True, exist_ok=True)
            
            combined_file = self.config.text_output.absolute() / 'combined.txt'
            with open(combined_file, 'w', encoding='utf-8') as f:
                f.write(combined_text)
            self.logger.info(f"Generated combined output: {combined_file}")
            
            return combined_text
        except Exception as e:
            self.logger.error(f"Error generating combined output: {str(e)}")
            return ""

    def _generate_tree(self, path: Path, prefix: str = "") -> List[str]:
        """Generate tree-like structure of directory contents."""
        if path.name in self.config.ignored_dirs:
            return []

        try:
            path.relative_to(self.config.text_output)
        except ValueError:
            return []

        contents = []
        try:
            paths = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except PermissionError:
            return []
            
        for i, p in enumerate(paths):
            if p.name in self.config.ignored_dirs:
                continue
                
            is_last = i == len(paths) - 1
            connector = "└── " if is_last else "├── "
            contents.append(f"{prefix}{connector}{p.name}")
            
            if p.is_dir():
                extension = "    " if is_last else "│   "
                contents.extend(self._generate_tree(p, prefix + extension))
        
        return contents

def process_files(config_path: str = 'config.yml') -> ProcessingResults:
    """Main function to process files and return results."""
    try:
        config = FileProcessor.load_config(config_path)
        processor = FileProcessor(config)
        return processor.process_directory()
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        raise

def main():
    try:
        results = process_files()
        print("\nDirectory Tree:")
        print(results.tree_output)
        print("\nFirst 500 characters of combined output:")
        print(results.combined_output[:500] + "...")
    except Exception as e:
        logging.error(f"Application error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
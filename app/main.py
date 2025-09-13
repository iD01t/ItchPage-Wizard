"""
ItchPage Wizard - Main GUI Application
Cross-platform desktop tool for generating itch.io page assets
"""

import os
import json
import threading
import argparse
import inspect
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import PySimpleGUI as sg
except Exception:
    sg = None

from .covers import CoverGenerator
from .collage import ScreenshotCollage
from .gifopt import GIFOptimizer
from .packager import ZipPackager
from .presets import PresetManager
from .utils import validate_image, get_asset_path, show_error

# Application constants
APP_VERSION = "1.0.0"
APP_TITLE = "ItchPage Wizard"
CONFIG_FILE = "config.json"
PREVIEW_SIZE = (400, 320)

class ItchPageWizard:
    def __init__(self, gui_mode: bool = True):
        self.config = self.load_config()
        self.cover_gen = CoverGenerator()
        self.collage_gen = ScreenshotCollage()
        self.gif_opt = GIFOptimizer()
        self.packager = ZipPackager()
        self.preset_manager = PresetManager()

        # GUI state
        self.current_preview = None
        self.selected_images = []
        self.window = None

        if gui_mode and sg:
            # Setup theme
            sg.theme('DarkBlue3')

    def load_config(self) -> Dict[str, Any]:
        """Load application configuration"""
        default_config = {
            'last_output_dir': str(Path.home() / 'Desktop'),
            'preferred_fonts': ['Arial', 'Helvetica', 'Times New Roman'],
            'gif_quality': 80,
            'last_window_size': (1200, 800)
        }

        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    return {**default_config, **config}
        except Exception:
            pass

        return default_config

    def save_config(self):
        """Save current configuration"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Could not save config: {e}")

    def create_layout(self):
        """Create the main application layout"""
        # Left sidebar - Inputs
        input_column = [
            [sg.Text("PROJECT SETUP", font=('Arial', 12, 'bold'))],
            [sg.Text("Title:"), sg.Input(key='-TITLE-', size=(25, 1), enable_events=True)],
            [sg.Text("Studio:"), sg.Input(key='-STUDIO-', size=(25, 1), enable_events=True)],
            [sg.Text("Version:"), sg.Input(key='-VERSION-', size=(25, 1), enable_events=True)],

            [sg.HSeparator()],
            [sg.Text("TOOL SELECTION", font=('Arial', 12, 'bold'))],
            [sg.Radio("Cover Generator", "TOOL", key='-TOOL_COVER-', default=True, enable_events=True)],
            [sg.Radio("Screenshot Collage", "TOOL", key='-TOOL_COLLAGE-', enable_events=True)],
            [sg.Radio("GIF Optimizer", "TOOL", key='-TOOL_GIF-', enable_events=True)],

            [sg.HSeparator()],
            [sg.Text("COVER OPTIONS", font=('Arial', 10, 'bold'), key='-COVER_LABEL-')],
            [sg.Text("Background:"), sg.Combo(['Solid Color', 'Gradient', 'Image Blur'],
                                              default_value='Solid Color', key='-BG_TYPE-', enable_events=True)],
            [sg.Text("Color:"), sg.ColorChooserButton("Choose", key='-BG_COLOR-', button_color=('#FFFFFF', '#000000'))],
            [sg.Text("Font:"), sg.Combo(['Arial', 'Helvetica', 'Times New Roman', 'Impact'],
                                        default_value='Arial', key='-FONT-', enable_events=True)],
            [sg.Checkbox("Bold", key='-BOLD-', enable_events=True)],
            [sg.Checkbox("Drop Shadow", key='-SHADOW-', default=True, enable_events=True)],

            [sg.Text("COLLAGE OPTIONS", font=('Arial', 10, 'bold'), key='-COLLAGE_LABEL-', visible=False)],
            [sg.Text("Layout:"), sg.Combo(['Grid', 'Masonry', 'Linear'],
                                          default_value='Grid', key='-LAYOUT-', enable_events=True, visible=False)],
            [sg.Text("Gutter:"), sg.Slider(range=(4, 32), default_value=12, orientation='h',
                                           key='-GUTTER-', enable_events=True, visible=False)],

            [sg.Text("GIF OPTIONS", font=('Arial', 10, 'bold'), key='-GIF_LABEL-', visible=False)],
            [sg.Text("Target Size:"), sg.Slider(range=(1, 10), default_value=3, orientation='h',
                                                key='-GIF_SIZE-', enable_events=True, visible=False)],
            [sg.Text("Quality:"), sg.Slider(range=(1, 100), default_value=80, orientation='h',
                                           key='-GIF_QUALITY-', enable_events=True, visible=False)],

            [sg.HSeparator()],
            [sg.Button("Apply Jam Preset", key='-PRESET_JAM-', size=(20, 1))],
            [sg.Button("Load Images", key='-LOAD_IMAGES-', size=(20, 1))],
        ]

        # Center preview area
        preview_column = [
            [sg.Text("LIVE PREVIEW", font=('Arial', 14, 'bold'), justification='center')],
            [sg.Image(key='-PREVIEW-', size=PREVIEW_SIZE, background_color='white')],
            [sg.Text("Drag and drop images here", key='-PREVIEW_TEXT-', justification='center')],
            [sg.Multiline("", key='-LOG-', size=(50, 8), disabled=True, autoscroll=True)],
        ]

        # Right panel - Export
        export_column = [
            [sg.Text("EXPORT SETTINGS", font=('Arial', 12, 'bold'))],
            [sg.Text("Output Directory:")],
            [sg.Input(self.config['last_output_dir'], key='-OUTPUT_DIR-', size=(35, 1)),
             sg.FolderBrowse()],

            [sg.HSeparator()],
            [sg.Text("EXPORT OPTIONS", font=('Arial', 10, 'bold'))],
            [sg.Checkbox("PNG Format", key='-EXPORT_PNG-', default=True)],
            [sg.Checkbox("JPG Format", key='-EXPORT_JPG-')],
            [sg.Checkbox("Include Metadata", key='-METADATA-', default=True)],

            [sg.HSeparator()],
            [sg.Button("Generate Cover", key='-EXPORT_COVER-', size=(20, 2))],
            [sg.Button("Create Collage", key='-EXPORT_COLLAGE-', size=(20, 2))],
            [sg.Button("Optimize GIF", key='-EXPORT_GIF-', size=(20, 2))],
            [sg.Button("Package All Assets", key='-PACKAGE_ALL-', size=(20, 2))],

            [sg.HSeparator()],
            [sg.Text("PROGRESS", font=('Arial', 10, 'bold'))],
            [sg.ProgressBar(100, orientation='h', size=(25, 20), key='-PROGRESS-')],
            [sg.Text("Ready", key='-STATUS-', text_color='green')],
        ]

        # Main layout
        layout = [
            [sg.MenuBar([['File', ['New Project', 'Open Project', 'Save Project', '---', 'Exit']],
                        ['Tools', ['Batch Process', 'Preferences']],
                        ['Help', ['Documentation', 'About']]])],
            [sg.Column(input_column, vertical_alignment='top', size=(300, 600)),
             sg.VSeperator(),
             sg.Column(preview_column, vertical_alignment='top', size=(500, 600)),
             sg.VSeperator(),
             sg.Column(export_column, vertical_alignment='top', size=(350, 600))],
            [sg.StatusBar("ItchPage Wizard v1.0.0 Ready", key='-STATUSBAR-')]
        ]

        return layout

    def update_tool_visibility(self, tool_type: str):
        """Update UI visibility based on selected tool"""
        window = self.window

        # Hide all tool-specific options
        cover_elements = ['-COVER_LABEL-', '-BG_TYPE-', '-BG_COLOR-', '-FONT-', '-BOLD-', '-SHADOW-']
        collage_elements = ['-COLLAGE_LABEL-', '-LAYOUT-', '-GUTTER-']
        gif_elements = ['-GIF_LABEL-', '-GIF_SIZE-', '-GIF_QUALITY-']

        all_elements = cover_elements + collage_elements + gif_elements
        for elem in all_elements:
            window[elem].update(visible=False)

        # Show relevant elements
        if tool_type == 'cover':
            for elem in cover_elements:
                window[elem].update(visible=True)
        elif tool_type == 'collage':
            for elem in collage_elements:
                window[elem].update(visible=True)
        elif tool_type == 'gif':
            for elem in gif_elements:
                window[elem].update(visible=True)

    def update_preview(self, values: Dict[str, Any]):
        """Update the live preview"""
        try:
            if values['-TOOL_COVER-']:
                self.update_cover_preview(values)
            elif values['-TOOL_COLLAGE-']:
                self.update_collage_preview(values)
            elif values['-TOOL_GIF-']:
                self.update_gif_preview(values)
        except Exception as e:
            self.log(f"Preview update failed: {e}")

    def update_cover_preview(self, values: Dict[str, Any]):
        """Update cover preview"""
        if not values['-TITLE-']:
            return

        # Generate preview cover
        cover_data = {
            'title': values['-TITLE-'],
            'studio': values['-STUDIO-'],
            'version': values['-VERSION-'],
            'background_type': values['-BG_TYPE-'],
            'background_color': values['-BG_COLOR-'],
            'font': values['-FONT-'],
            'bold': values['-BOLD-'],
            'shadow': values['-SHADOW-']
        }

        preview_image = self.cover_gen.generate_preview(cover_data, PREVIEW_SIZE)
        if preview_image:
            self.window['-PREVIEW-'].update(data=preview_image)

    def update_collage_preview(self, values: Dict[str, Any]):
        """Update collage preview"""
        if not self.selected_images:
            return

        collage_data = {
            'layout': values['-LAYOUT-'],
            'gutter': int(values['-GUTTER-']),
            'images': self.selected_images[:5]  # Preview with first 5 images
        }

        preview_image = self.collage_gen.generate_preview(collage_data, PREVIEW_SIZE)
        if preview_image:
            self.window['-PREVIEW-'].update(data=preview_image)

    def update_gif_preview(self, values: Dict[str, Any]):
        """Update GIF preview (show first frame)"""
        if not self.selected_images:
            return

        # Show first frame of GIF/video
        preview_image = self.gif_opt.get_preview_frame(self.selected_images[0], PREVIEW_SIZE)
        if preview_image:
            self.window['-PREVIEW-'].update(data=preview_image)

    def log(self, message: str):
        """Add message to log area"""
        if hasattr(self, 'window') and self.window:
            current_log = self.window['-LOG-'].get()
            new_log = f"{current_log}\n{message}" if current_log else message
            self.window['-LOG-'].update(new_log)
            # Auto-scroll to bottom
            self.window['-LOG-'].Widget.see("end")

    def handle_file_drop(self, files):
        """Handle dropped files"""
        valid_images = []
        for file_path in files:
            if validate_image(file_path):
                valid_images.append(file_path)
            else:
                self.log(f"Invalid image: {file_path}")

        if valid_images:
            self.selected_images.extend(valid_images)
            self.log(f"Added {len(valid_images)} images")
            self.update_preview(self.get_current_values())

    def get_current_values(self):
        """Get current window values"""
        if hasattr(self, 'window') and self.window:
            return self.window.read(timeout=0)[1]
        return {}

    def export_cover(self, values: Dict[str, Any]):
        """Export cover image"""
        def export_thread():
            try:
                self.window['-STATUS-'].update("Generating cover...", text_color='orange')
                self.window['-PROGRESS-'].update(25)

                output_path = self.cover_gen.generate_cover(
                    title=values['-TITLE-'],
                    studio=values['-STUDIO-'],
                    version=values['-VERSION-'],
                    output_dir=values['-OUTPUT_DIR-'],
                    export_png=values['-EXPORT_PNG-'],
                    export_jpg=values['-EXPORT_JPG-'],
                    include_metadata=values['-METADATA-'],
                    background_type=values['-BG_TYPE-'],
                    background_color=values['-BG_COLOR-'],
                    font=values['-FONT-'],
                    bold=values['-BOLD-'],
                    shadow=values['-SHADOW-']
                )

                self.window['-PROGRESS-'].update(100)
                self.window['-STATUS-'].update("Cover exported!", text_color='green')
                self.log(f"Cover saved: {output_path}")

            except Exception as e:
                self.window['-STATUS-'].update("Export failed", text_color='red')
                self.log(f"Cover export failed: {e}")
                show_error(f"Cover export failed: {e}")

        threading.Thread(target=export_thread, daemon=True).start()

    def export_collage(self, values: Dict[str, Any]):
        """Export collage image"""
        def export_thread():
            try:
                self.window['-STATUS-'].update("Creating collage...", text_color='orange')
                self.window['-PROGRESS-'].update(25)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"screens-inline-920w_{timestamp}.png"
                output_path = os.path.join(values['-OUTPUT_DIR-'], output_filename)

                self.collage_gen.create_collage(
                    image_paths=self.selected_images,
                    output_path=output_path,
                    layout=values['-LAYOUT-'],
                    gutter=int(values['-GUTTER-'])
                )

                self.window['-PROGRESS-'].update(100)
                self.window['-STATUS-'].update("Collage created!", text_color='green')
                self.log(f"Collage saved: {output_path}")

            except Exception as e:
                self.window['-STATUS-'].update("Export failed", text_color='red')
                self.log(f"Collage export failed: {e}")
                show_error(f"Collage export failed: {e}")

        threading.Thread(target=export_thread, daemon=True).start()

    def export_gif(self, values: Dict[str, Any]):
        """Export optimized GIF"""
        def export_thread():
            try:
                self.window['-STATUS-'].update("Optimizing GIF...", text_color='orange')
                self.window['-PROGRESS-'].update(25)

                input_path = self.selected_images[0] # Assume first selected image is the input
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"promo_{timestamp}.gif"
                output_path = os.path.join(values['-OUTPUT_DIR-'], output_filename)

                if input_path.lower().endswith('.gif'):
                    self.gif_opt.optimize_gif(
                        input_path=input_path,
                        output_path=output_path,
                        target_size_mb=float(values['-GIF_SIZE-']),
                        quality=int(values['-GIF_QUALITY-'])
                    )
                else:
                    self.gif_opt.convert_video_to_gif(
                        video_path=input_path,
                        output_path=output_path,
                        target_size_mb=float(values['-GIF_SIZE-']),
                        quality=int(values['-GIF_QUALITY-'])
                    )

                self.window['-PROGRESS-'].update(100)
                self.window['-STATUS-'].update("GIF optimized!", text_color='green')
                self.log(f"GIF saved: {output_path}")

            except Exception as e:
                self.window['-STATUS-'].update("Export failed", text_color='red')
                self.log(f"GIF optimization failed: {e}")
                show_error(f"GIF optimization failed: {e}")

        threading.Thread(target=export_thread, daemon=True).start()

    def package_all_assets(self, values: Dict[str, Any]):
        """Package all generated assets into a zip file."""
        # TODO: This needs a way to track the paths of the last generated assets.
        # For now, it's a placeholder.
        self.log("Package All Assets button is not fully implemented yet for GUI mode.")
        show_error("Packaging from the GUI is not yet implemented. Please use the CLI batch mode for now.")

    def run_batch(self, project_path: str):
        """Run the application in batch mode from a project file."""
        print(f"Starting batch processing for: {project_path}")

        if not os.path.exists(project_path):
            print(f"Error: Project file not found at {project_path}")
            return

        with open(project_path, 'r') as f:
            project_data = json.load(f)

        output_dir = project_data.get('output', {}).get('directory', 'output')
        os.makedirs(output_dir, exist_ok=True)
        print(f"Batch mode: Output directory set to {output_dir}")

        project_info = project_data.get('project', {})

        # 1. Generate Cover
        if 'cover' in project_data:
            print("Generating cover...")
            try:
                cover_config = project_data['cover']

                sig = inspect.signature(self.cover_gen.generate_cover)
                allowed_keys = {p.name for p in sig.parameters.values()}
                filtered_config = {k: v for k, v in cover_config.items() if k in allowed_keys}

                output_path = self.cover_gen.generate_cover(
                    title=project_info.get('title', 'Untitled'),
                    studio=project_info.get('studio', ''),
                    version=project_info.get('version', ''),
                    output_dir=output_dir,
                    **filtered_config
                )
                print(f"Cover generated: {output_path}")
            except Exception as e:
                print(f"Failed to generate cover: {e}")

        # 2. Create Collage
        if 'collage' in project_data and project_data['collage'].get('images'):
            print("Creating collage...")
            try:
                collage_config = project_data['collage']
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"screens-inline-920w_{timestamp}.png"
                output_path = os.path.join(output_dir, output_filename)

                self.collage_gen.create_collage(
                    image_paths=collage_config.get('images', []),
                    output_path=output_path,
                    layout=collage_config.get('layout', 'Grid'),
                    gutter=collage_config.get('gutter', 12)
                )
                print(f"Collage created: {output_path}")
            except Exception as e:
                print(f"Failed to create collage: {e}")

        # 3. Optimize GIF
        if 'gif' in project_data and project_data['gif'].get('input'):
            print("Optimizing GIF...")
            try:
                gif_config = project_data['gif']
                input_path = gif_config['input']
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"promo_{timestamp}.gif"
                output_path = os.path.join(output_dir, output_filename)

                if input_path.lower().endswith('.gif'):
                    self.gif_opt.optimize_gif(
                        input_path=input_path,
                        output_path=output_path,
                        target_size_mb=gif_config.get('target_size_mb', 3.0),
                        quality=gif_config.get('quality', 80)
                    )
                else:
                    self.gif_opt.convert_video_to_gif(
                        video_path=input_path,
                        output_path=output_path,
                        target_size_mb=gif_config.get('target_size_mb', 3.0),
                        quality=gif_config.get('quality', 80),
                        start_time=gif_config.get('start_time', 0),
                        duration=gif_config.get('duration')
                    )
                print(f"GIF optimized: {output_path}")
            except Exception as e:
                print(f"Failed to optimize GIF: {e}")

        print("Batch processing finished.")

    def run_batch_covers(self, csv_path: str):
        """Run batch cover generation from a CSV file."""
        print(f"Starting batch cover generation from: {csv_path}")

        if not os.path.exists(csv_path):
            print(f"Error: CSV file not found at {csv_path}")
            return

        output_dir = os.path.join(os.path.dirname(csv_path), 'covers_output')
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output directory: {output_dir}")

        try:
            with open(csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                required_headers = ['title']
                if not all(h in reader.fieldnames for h in required_headers):
                    print(f"Error: CSV must contain the following headers: {required_headers}")
                    return

                sig = inspect.signature(self.cover_gen.generate_cover)
                allowed_keys = {p.name for p in sig.parameters.values()}

                for i, row in enumerate(reader):
                    print(f"Processing row {i+1}: {row.get('title')}")
                    try:
                        cover_params = {k: v for k, v in row.items() if k in allowed_keys and v}

                        if 'bold' in cover_params:
                            cover_params['bold'] = cover_params['bold'].upper() == 'TRUE'
                        if 'shadow' in cover_params:
                            cover_params['shadow'] = cover_params['shadow'].upper() == 'TRUE'

                        title = row.get('title', f'cover_{i+1}')
                        sanitized_title = "".join(c for c in title if c.isalnum() or c in (' ', '_')).rstrip()
                        sanitized_title = sanitized_title.replace(' ', '_')
                        filename_stem = f"{sanitized_title}_630x500"
                        cover_params['filename_stem'] = filename_stem

                        self.cover_gen.generate_cover(
                            output_dir=output_dir,
                            **cover_params
                        )
                    except Exception as e:
                        print(f"  -> Failed to generate cover for row {i+1}: {e}")
            print("Batch cover generation finished.")
        except Exception as e:
            print(f"An error occurred while processing the CSV file: {e}")

    def run_batch_collage(self, folder_path: str, layout: str, gutter: int):
        """Run batch collage generation from a folder of images."""
        print(f"Starting batch collage generation for folder: {folder_path}")
        print(f"Layout: {layout}, Gutter: {gutter}px")

        if not os.path.isdir(folder_path):
            print(f"Error: Folder not found at {folder_path}")
            return

        image_paths = sorted([
            os.path.join(folder_path, f) for f in os.listdir(folder_path)
            if validate_image(os.path.join(folder_path, f))
        ])

        if not image_paths:
            print("No valid images found in the specified folder.")
            return

        print(f"Found {len(image_paths)} valid images.")

        output_dir = os.path.join(folder_path, 'collage_output')
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"collage_{layout}_{timestamp}.png"
        output_path = os.path.join(output_dir, output_filename)

        try:
            self.collage_gen.create_collage(
                image_paths=image_paths,
                output_path=output_path,
                layout=layout,
                gutter=gutter
            )
            print(f"Collage created successfully: {output_path}")
        except Exception as e:
            print(f"Failed to create collage: {e}")

    def run(self):
        """Main application loop"""
        layout = self.create_layout()
        self.window = sg.Window(
            APP_TITLE,
            layout,
            size=self.config['last_window_size'],
            finalize=True,
            enable_close_attempted_event=True,
            drop_callback=self.handle_file_drop
        )

        # Initial UI setup
        self.update_tool_visibility('cover')

        while True:
            event, values = self.window.read(timeout=100)

            if event in (sg.WIN_CLOSED, '-WINDOW CLOSE ATTEMPTED-', 'Exit'):
                break

            # Tool selection
            if event in ['-TOOL_COVER-', '-TOOL_COLLAGE-', '-TOOL_GIF-']:
                if values['-TOOL_COVER-']:
                    self.update_tool_visibility('cover')
                elif values['-TOOL_COLLAGE-']:
                    self.update_tool_visibility('collage')
                elif values['-TOOL_GIF-']:
                    self.update_tool_visibility('gif')
                self.update_preview(values)

            # Live preview updates
            if event in ['-TITLE-', '-STUDIO-', '-VERSION-', '-BG_TYPE-', '-BG_COLOR-',
                        '-FONT-', '-BOLD-', '-SHADOW-', '-LAYOUT-', '-GUTTER-']:
                self.update_preview(values)

            # Preset application
            if event == '-PRESET_JAM-':
                self.preset_manager.apply_jam_preset(self.window)
                self.update_preview(self.window.read(timeout=0)[1])

            # File operations
            if event == '-LOAD_IMAGES-':
                files = sg.popup_get_file(
                    'Select Images',
                    multiple_files=True,
                    file_types=(('Image Files', '*.png *.jpg *.jpeg *.gif *.bmp'),)
                )
                if files:
                    file_list = files.split(';') if ';' in files else [files]
                    self.handle_file_drop(file_list)

            # Export operations
            if event == '-EXPORT_COVER-' and values['-TITLE-']:
                self.export_cover(values)

            if event == '-EXPORT_COLLAGE-' and self.selected_images:
                self.export_collage(values)

            if event == '-EXPORT_GIF-' and self.selected_images:
                self.export_gif(values)

            if event == '-PACKAGE_ALL-':
                self.package_all_assets(values)

            # Menu events
            if event == 'About':
                sg.popup(f'{APP_TITLE} v{APP_VERSION}',
                        'Cross-platform itch.io asset generator',
                        'Built with Python and love ❤️',
                        title='About')

        # Save config before exit
        self.config['last_output_dir'] = values['-OUTPUT_DIR-']
        self.config['last_window_size'] = self.window.size
        self.save_config()

        self.window.close()

def main():
    """Application entry point"""
    parser = argparse.ArgumentParser(description="ItchPage Wizard - itch.io asset generator.")
    parser.add_argument('--project', type=str, help='Path to project.json file for batch processing.')
    parser.add_argument('--batch', action='store_true', help='Run in project batch mode (requires --project).')
    parser.add_argument('--csv-covers', type=str, help='Path to a CSV file for batch cover generation.')
    parser.add_argument('--collage-folder', type=str, help='Path to a folder of images for batch collage generation.')
    parser.add_argument('--collage-layout', type=str, default='Grid', help='Layout for batch collage (Grid, Masonry, Linear).')
    parser.add_argument('--collage-gutter', type=int, default=12, help='Gutter size for batch collage.')
    args = parser.parse_args()

    is_batch_project_mode = args.batch and args.project
    is_batch_csv_mode = args.csv_covers is not None
    is_batch_collage_mode = args.collage_folder is not None
    is_gui_mode = not (is_batch_project_mode or is_batch_csv_mode or is_batch_collage_mode)

    try:
        app = ItchPageWizard(gui_mode=is_gui_mode)

        if is_batch_project_mode:
            app.run_batch(args.project)
        elif is_batch_csv_mode:
            app.run_batch_covers(args.csv_covers)
        elif is_batch_collage_mode:
            app.run_batch_collage(args.collage_folder, args.collage_layout, args.collage_gutter)
        else:
            if sg is None:
                raise RuntimeError("Cannot run in GUI mode: PySimpleGUI failed to import, likely due to a missing display.")
            app.run()

    except Exception as e:
        if not is_gui_mode or sg is None:
            print(f"Application failed to start: {e}")
        else:
            sg.popup_error(f"Application failed to start: {e}")

if __name__ == "__main__":
    main()

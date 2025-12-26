#!/usr/bin/env python3
"""Convert Ink spec files from markdown metadata to YAML frontmatter."""

import re
import sys
from pathlib import Path


def parse_markdown_metadata(content: str) -> tuple[dict, str]:
    """Parse markdown metadata section and return (metadata_dict, remaining_content)."""
    metadata = {}

    # Extract title from header: # Spec: E01-F01 - CDL Parser
    title_match = re.match(r'^# Spec:\s*[\w-]+\s*-\s*(.+)$', content, re.MULTILINE)
    if title_match:
        metadata['title'] = title_match.group(1).strip()

    # Find the Metadata section
    metadata_match = re.search(
        r'^## Metadata\n((?:- \*\*[^*]+\*\*:.*\n?)+)',
        content,
        re.MULTILINE
    )

    if not metadata_match:
        return {}, content

    metadata_text = metadata_match.group(1)

    # Parse each metadata line
    for line in metadata_text.strip().split('\n'):
        match = re.match(r'- \*\*([^*]+)\*\*:\s*(.*)', line)
        if match:
            key = match.group(1).strip()
            value = match.group(2).strip()

            # Normalize keys to snake_case
            key_map = {
                'ID': 'id',
                'Type': 'type',
                'Priority': 'priority',
                'Status': 'status',
                'Parent': 'parent',
                'Created': 'created',
                'Estimated Hours': 'estimated_hours',
                'Actual Hours': 'actual_hours',
                'Effort': 'effort',
                'Tags': 'tags',
                'PRD Sections': 'prd_sections',
            }

            normalized_key = key_map.get(key, key.lower().replace(' ', '_'))

            # Parse parent link: [E01](../E01.spec.md) -> E01
            if normalized_key == 'parent':
                parent_match = re.match(r'\[([^\]]+)\]', value)
                if parent_match:
                    value = parent_match.group(1)

            # Parse tags: [] or [tag1, tag2]
            if normalized_key == 'tags':
                if value == '[]':
                    value = []
                else:
                    # Extract tags from [tag1, tag2]
                    tags_match = re.match(r'\[(.*)\]', value)
                    if tags_match:
                        value = [t.strip() for t in tags_match.group(1).split(',') if t.strip()]
                    else:
                        value = []

            # Handle empty values
            if value == '' or value is None:
                value = None

            metadata[normalized_key] = value

    # Remove the Metadata section from content
    # Find where metadata section ends (at the next --- or ## section)
    content_after_metadata = content[metadata_match.end():]

    # Remove leading --- separator if present
    content_after_metadata = re.sub(r'^\s*---\s*\n', '', content_after_metadata)

    # Get the title line (# Spec: ...)
    title_match = re.match(r'^(# Spec:.*?\n)', content)
    title_line = title_match.group(1) if title_match else ''

    # Reconstruct content without metadata section
    remaining = title_line + '\n' + content_after_metadata.lstrip()

    return metadata, remaining


def metadata_to_yaml(metadata: dict) -> str:
    """Convert metadata dict to YAML frontmatter string."""
    lines = ['---']

    # Define preferred order
    order = ['id', 'title', 'type', 'priority', 'status', 'parent', 'prd_sections',
             'created', 'estimated_hours', 'actual_hours', 'effort', 'tags']

    for key in order:
        if key in metadata:
            value = metadata[key]
            if value is None or value == '':
                lines.append(f'{key}:')
            elif isinstance(value, list):
                if len(value) == 0:
                    lines.append(f'{key}: []')
                else:
                    lines.append(f'{key}:')
                    for item in value:
                        lines.append(f'  - {item}')
            elif isinstance(value, str) and (':' in value or '#' in value or value.startswith('[')):
                # Quote strings with special characters
                lines.append(f'{key}: "{value}"')
            else:
                lines.append(f'{key}: {value}')

    # Add any remaining keys not in the order list
    for key, value in metadata.items():
        if key not in order:
            if value is None or value == '':
                lines.append(f'{key}:')
            elif isinstance(value, list):
                if len(value) == 0:
                    lines.append(f'{key}: []')
                else:
                    lines.append(f'{key}:')
                    for item in value:
                        lines.append(f'  - {item}')
            else:
                lines.append(f'{key}: {value}')

    lines.append('---')
    return '\n'.join(lines)


def is_task_or_subtask(spec_id: str) -> bool:
    """Check if spec ID is task level (E01-F01-T01) or subtask level (E01-F01-T01-S01)."""
    # Task: E##-F##-T## or deeper
    return bool(re.match(r'^E\d+-F\d+-T\d+', spec_id))


def convert_spec_file(file_path: Path) -> bool:
    """Convert a single spec file. Returns True if converted."""
    content = file_path.read_text()

    # If already has YAML frontmatter, check if updates are needed
    if content.startswith('---'):
        # Parse existing frontmatter
        end_marker = content.find('---', 3)
        if end_marker == -1:
            print(f'  ⚠️  Malformed frontmatter: {file_path.name}')
            return False

        frontmatter_text = content[4:end_marker].strip()
        remaining_content = content[end_marker + 3:].lstrip()

        # Extract spec ID from frontmatter
        id_match = re.search(r'^id:\s*(.+)$', frontmatter_text, re.MULTILINE)
        spec_id = id_match.group(1).strip() if id_match else ''

        needs_update = False
        lines = frontmatter_text.split('\n')
        new_lines = []

        # Check what needs to be added
        has_title = 'title:' in frontmatter_text
        has_clickup_id = 'clickup_task_id:' in frontmatter_text
        needs_clickup_id = is_task_or_subtask(spec_id) and not has_clickup_id

        if has_title and not needs_clickup_id:
            print(f'  ⏭️  Already complete: {file_path.name}')
            return False

        # Extract title if needed
        title = None
        if not has_title:
            title_match = re.match(r'^# Spec:\s*[\w-]+\s*-\s*(.+)$', remaining_content, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()
                needs_update = True

        if needs_clickup_id:
            needs_update = True

        if not needs_update:
            print(f'  ⏭️  No updates needed: {file_path.name}')
            return False

        # Rebuild frontmatter with additions
        for line in lines:
            new_lines.append(line)
            # Add title after id line
            if line.startswith('id:') and title and not has_title:
                new_lines.append(f'title: {title}')

        # Add clickup_task_id at the end for tasks/subtasks
        if needs_clickup_id:
            new_lines.append("clickup_task_id: ''")

        new_frontmatter = '---\n' + '\n'.join(new_lines) + '\n---'
        new_content = new_frontmatter + '\n\n' + remaining_content
        file_path.write_text(new_content)

        updates = []
        if title and not has_title:
            updates.append('title')
        if needs_clickup_id:
            updates.append('clickup_task_id')
        print(f'  ✅ Added {", ".join(updates)}: {file_path.name}')
        return True

    # Parse and convert from markdown format
    metadata, remaining_content = parse_markdown_metadata(content)

    if not metadata:
        print(f'  ⚠️  No metadata found: {file_path.name}')
        return False

    # Build new content
    yaml_frontmatter = metadata_to_yaml(metadata)
    new_content = yaml_frontmatter + '\n\n' + remaining_content.lstrip()

    # Write back
    file_path.write_text(new_content)
    print(f'  ✅ Converted: {file_path.name}')
    return True


def main():
    specs_dir = Path(__file__).parent.parent / 'specs'

    if not specs_dir.exists():
        print(f'❌ Specs directory not found: {specs_dir}')
        sys.exit(1)

    print(f'🔄 Converting specs in {specs_dir}...\n')

    # Find all spec files
    spec_files = list(specs_dir.rglob('*.spec.md'))
    print(f'📁 Found {len(spec_files)} spec files\n')

    converted = 0
    skipped = 0
    failed = 0

    for spec_file in sorted(spec_files):
        try:
            if convert_spec_file(spec_file):
                converted += 1
            else:
                skipped += 1
        except Exception as e:
            print(f'  ❌ Error converting {spec_file.name}: {e}')
            failed += 1

    print(f'\n📊 Summary:')
    print(f'   Converted: {converted}')
    print(f'   Skipped:   {skipped}')
    print(f'   Failed:    {failed}')


if __name__ == '__main__':
    main()

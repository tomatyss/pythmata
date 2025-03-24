"""Version diff module for comparing process versions."""

import difflib
import json
import uuid
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.models.process import ChangeType, ProcessElementChange, ProcessVersion


class VersionDiff:
    """Service for comparing different process versions."""

    def __init__(self, session: AsyncSession):
        """Initialize the version diff service.

        Args:
            session: The database session.
        """
        self.session = session

    async def get_element_changes(
        self, version_id: uuid.UUID
    ) -> List[ProcessElementChange]:
        """Get all element changes for a specific version.

        Args:
            version_id: The version ID.

        Returns:
            List of element changes.
        """
        result = await self.session.execute(
            select(ProcessElementChange).where(ProcessElementChange.version_id == version_id)
        )
        return result.scalars().all()

    async def compare_versions(
        self, from_version_id: uuid.UUID, to_version_id: uuid.UUID
    ) -> Dict:
        """Compare two versions and return their differences.

        Args:
            from_version_id: The source version ID.
            to_version_id: The target version ID.

        Returns:
            Dictionary containing the differences between versions.

        Raises:
            ValueError: If either version is not found.
        """
        from_version = await self.session.get(ProcessVersion, from_version_id)
        if not from_version:
            raise ValueError(f"Version {from_version_id} not found")

        to_version = await self.session.get(ProcessVersion, to_version_id)
        if not to_version:
            raise ValueError(f"Version {to_version_id} not found")

        # Get changes for both versions
        from_changes = await self.get_element_changes(from_version_id)
        to_changes = await self.get_element_changes(to_version_id)

        # Compare BPMN XML structure
        xml_diff = self._diff_text(from_version.bpmn_xml_snapshot, to_version.bpmn_xml_snapshot)

        # Compare variable definitions
        var_diff = self._diff_json(
            from_version.variable_definitions_snapshot, to_version.variable_definitions_snapshot
        )

        # Collect elements changed in both versions
        from_elements = {change.element_id for change in from_changes}
        to_elements = {change.element_id for change in to_changes}

        # Find common and unique elements
        common_elements = from_elements.intersection(to_elements)
        only_in_from = from_elements - to_elements
        only_in_to = to_elements - from_elements

        # Process element changes
        element_changes = {
            "common": [
                self._compare_element_changes(
                    element_id,
                    [c for c in from_changes if c.element_id == element_id],
                    [c for c in to_changes if c.element_id == element_id],
                )
                for element_id in common_elements
            ],
            "only_in_from": [
                self._format_element_change(change) for change in from_changes
                if change.element_id in only_in_from
            ],
            "only_in_to": [
                self._format_element_change(change) for change in to_changes
                if change.element_id in only_in_to
            ],
        }

        return {
            "from_version": {
                "id": str(from_version.id),
                "version_number": from_version.version_number,
                "author": from_version.author,
                "commit_message": from_version.commit_message,
                "created_at": from_version.created_at.isoformat(),
            },
            "to_version": {
                "id": str(to_version.id),
                "version_number": to_version.version_number,
                "author": to_version.author,
                "commit_message": to_version.commit_message,
                "created_at": to_version.created_at.isoformat(),
            },
            "xml_diff": xml_diff,
            "variable_definitions_diff": var_diff,
            "element_changes": element_changes,
        }

    def _diff_text(self, text1: str, text2: str) -> List[Dict]:
        """Create a diff between two text strings.

        Args:
            text1: The first text.
            text2: The second text.

        Returns:
            List of diff entries with line numbers and change type.
        """
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        
        differ = difflib.Differ()
        diff = list(differ.compare(lines1, lines2))
        
        result = []
        line1 = 0
        line2 = 0
        
        for line in diff:
            change_type = line[0]
            content = line[2:]
            
            if change_type == ' ':  # No change
                result.append({
                    "type": "unchanged",
                    "line1": line1,
                    "line2": line2,
                    "content": content
                })
                line1 += 1
                line2 += 1
            elif change_type == '-':  # Deletion
                result.append({
                    "type": "deleted",
                    "line1": line1,
                    "line2": None,
                    "content": content
                })
                line1 += 1
            elif change_type == '+':  # Addition
                result.append({
                    "type": "added",
                    "line1": None,
                    "line2": line2,
                    "content": content
                })
                line2 += 1
        
        return result

    def _diff_json(self, json1: List[Dict], json2: List[Dict]) -> Dict:
        """Create a diff between two JSON structures.

        Args:
            json1: The first JSON structure.
            json2: The second JSON structure.

        Returns:
            Dictionary with added, removed, and modified items.
        """
        # Convert lists to dictionaries keyed by an identifying field
        def list_to_dict(items):
            result = {}
            for item in items:
                if "name" in item:
                    key = item["name"]
                elif "id" in item:
                    key = item["id"]
                else:
                    key = json.dumps(item, sort_keys=True)
                result[key] = item
            return result
        
        dict1 = list_to_dict(json1)
        dict2 = list_to_dict(json2)
        
        keys1 = set(dict1.keys())
        keys2 = set(dict2.keys())
        
        # Find items that were added, removed, or modified
        added = keys2 - keys1
        removed = keys1 - keys2
        potential_modified = keys1.intersection(keys2)
        
        modified = {}
        for key in potential_modified:
            if dict1[key] != dict2[key]:
                modified[key] = {
                    "from": dict1[key],
                    "to": dict2[key]
                }
        
        return {
            "added": [dict2[key] for key in added],
            "removed": [dict1[key] for key in removed],
            "modified": modified
        }

    def _compare_element_changes(
        self,
        element_id: str,
        from_changes: List[ProcessElementChange],
        to_changes: List[ProcessElementChange],
    ) -> Dict:
        """Compare changes for a single element between two versions.

        Args:
            element_id: The element ID.
            from_changes: Changes in the source version.
            to_changes: Changes in the target version.

        Returns:
            Dictionary with element change details.
        """
        # Pick the first change from each list (should typically be only one per element)
        from_change = from_changes[0] if from_changes else None
        to_change = to_changes[0] if to_changes else None
        
        result = {
            "element_id": element_id,
            "element_type": from_change.element_type if from_change else to_change.element_type,
            "changes": {
                "from": self._format_element_change(from_change) if from_change else None,
                "to": self._format_element_change(to_change) if to_change else None,
            }
        }
        
        return result

    def _format_element_change(self, change: ProcessElementChange) -> Dict:
        """Format a ProcessElementChange for output.

        Args:
            change: The element change to format.

        Returns:
            Dictionary with formatted change information.
        """
        if not change:
            return None
            
        return {
            "version_id": str(change.version_id),
            "change_type": change.change_type.value,
            "previous_values": change.previous_values,
            "new_values": change.new_values,
        } 
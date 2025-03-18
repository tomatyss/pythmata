"""Version conflict resolution module."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.models.process import (
    ChangeType,
    ProcessDefinition,
    ProcessElementChange,
    ProcessVersion,
)


class ConflictResolver:
    """Service for resolving conflicts between process versions."""

    def __init__(self, session: AsyncSession):
        """Initialize the conflict resolver.

        Args:
            session: The database session.
        """
        self.session = session

    async def detect_conflicts(
        self, base_version_id: uuid.UUID, version1_id: uuid.UUID, version2_id: uuid.UUID
    ) -> Dict:
        """Detect conflicts between two versions based on a common ancestor.

        Args:
            base_version_id: The common ancestor version ID.
            version1_id: The first version ID to compare.
            version2_id: The second version ID to compare.

        Returns:
            Dictionary with conflict information.

        Raises:
            ValueError: If any of the versions is not found.
        """
        # Verify versions exist
        base_version = await self.session.get(ProcessVersion, base_version_id)
        if not base_version:
            raise ValueError(f"Base version {base_version_id} not found")

        version1 = await self.session.get(ProcessVersion, version1_id)
        if not version1:
            raise ValueError(f"First version {version1_id} not found")

        version2 = await self.session.get(ProcessVersion, version2_id)
        if not version2:
            raise ValueError(f"Second version {version2_id} not found")

        # Get all element changes
        changes_query = await self.session.execute(
            select(ProcessElementChange).where(
                ProcessElementChange.version_id.in_(
                    [base_version_id, version1_id, version2_id]
                )
            )
        )
        all_changes = changes_query.scalars().all()

        # Group changes by element ID and version
        changes_by_element = {}
        for change in all_changes:
            element_id = change.element_id
            if element_id not in changes_by_element:
                changes_by_element[element_id] = {
                    "base": None,
                    "version1": None,
                    "version2": None,
                }

            if str(change.version_id) == str(base_version_id):
                changes_by_element[element_id]["base"] = change
            elif str(change.version_id) == str(version1_id):
                changes_by_element[element_id]["version1"] = change
            elif str(change.version_id) == str(version2_id):
                changes_by_element[element_id]["version2"] = change

        # Find conflicting elements
        conflicts = []
        for element_id, changes in changes_by_element.items():
            v1_change = changes["version1"]
            v2_change = changes["version2"]

            # If both versions modified the same element, check for conflict
            if v1_change and v2_change:
                if self._is_conflicting(v1_change, v2_change):
                    conflicts.append(
                        {
                            "element_id": element_id,
                            "element_type": v1_change.element_type,
                            "version1_change": {
                                "change_type": v1_change.change_type.value,
                                "previous_values": v1_change.previous_values,
                                "new_values": v1_change.new_values,
                            },
                            "version2_change": {
                                "change_type": v2_change.change_type.value,
                                "previous_values": v2_change.previous_values,
                                "new_values": v2_change.new_values,
                            },
                        }
                    )

        return {
            "base_version": {
                "id": str(base_version.id),
                "version_number": base_version.version_number,
            },
            "version1": {
                "id": str(version1.id),
                "version_number": version1.version_number,
                "author": version1.author,
            },
            "version2": {
                "id": str(version2.id),
                "version_number": version2.version_number,
                "author": version2.author,
            },
            "has_conflicts": len(conflicts) > 0,
            "conflict_count": len(conflicts),
            "conflicts": conflicts,
        }

    def _is_conflicting(
        self, change1: ProcessElementChange, change2: ProcessElementChange
    ) -> bool:
        """Determine if two changes to the same element conflict.

        Args:
            change1: The first change.
            change2: The second change.

        Returns:
            True if the changes conflict, False otherwise.
        """
        # If one deleted and the other modified, it's a conflict
        if (
            change1.change_type == ChangeType.DELETED
            and change2.change_type != ChangeType.DELETED
        ) or (
            change2.change_type == ChangeType.DELETED
            and change1.change_type != ChangeType.DELETED
        ):
            return True

        # If both renamed, check if to the same name
        if (
            change1.change_type == ChangeType.RENAMED
            and change2.change_type == ChangeType.RENAMED
        ):
            if change1.new_values.get("name") != change2.new_values.get("name"):
                return True

        # If both modified properties, check for property overlap
        if (
            change1.change_type == ChangeType.MODIFIED
            and change2.change_type == ChangeType.MODIFIED
        ):
            # Check if they modified the same properties
            props1 = set(change1.new_values.keys())
            props2 = set(change2.new_values.keys())
            common_props = props1.intersection(props2)
            
            # If they modified common properties, check if values match
            for prop in common_props:
                if change1.new_values.get(prop) != change2.new_values.get(prop):
                    return True

        # If both moved, check if to the same position
        if (
            change1.change_type == ChangeType.MOVED
            and change2.change_type == ChangeType.MOVED
        ):
            if change1.new_values.get("position") != change2.new_values.get("position"):
                return True

        # No conflict detected
        return False

    async def apply_resolution(
        self,
        process_definition_id: uuid.UUID,
        conflicting_version_id: uuid.UUID,
        resolution_choices: Dict[str, str],
        author: str,
        commit_message: str,
    ) -> ProcessVersion:
        """Apply conflict resolution choices and create a new version.

        Args:
            process_definition_id: The process definition ID.
            conflicting_version_id: The version with conflicts.
            resolution_choices: Dictionary mapping element_id to chosen version ("version1", "version2", or "manual").
            author: The author applying the resolution.
            commit_message: The commit message for the new version.

        Returns:
            The newly created merged version.

        Raises:
            ValueError: If the process definition or version is not found.
        """
        process_def = await self.session.get(ProcessDefinition, process_definition_id)
        if not process_def:
            raise ValueError(f"Process definition {process_definition_id} not found")

        # Get conflicting version
        conflicting_version = await self.session.get(ProcessVersion, conflicting_version_id)
        if not conflicting_version:
            raise ValueError(f"Version {conflicting_version_id} not found")

        # Get current version
        current_version_result = await self.session.execute(
            select(ProcessVersion)
            .where(ProcessVersion.process_definition_id == process_definition_id)
            .where(ProcessVersion.is_current == True)  # noqa: E712
        )
        current_version = current_version_result.scalar_one_or_none()
        if not current_version:
            raise ValueError(f"No current version found for process {process_definition_id}")

        # Start with the XML from the current version
        merged_xml = current_version.bpmn_xml_snapshot
        merged_variables = current_version.variable_definitions_snapshot

        # For now, this is a simplified merge approach
        # A real implementation would need to actually parse and modify the BPMN XML
        # based on the conflict resolutions
        
        # Create a new version that represents the merged result
        new_version = ProcessVersion(
            process_definition_id=process_definition_id,
            parent_version_id=current_version.id,
            version_number=self._calculate_next_version(current_version),
            major_version=current_version.major_version,
            minor_version=current_version.minor_version + 1,  # Increment minor version for merges
            patch_version=0,
            branch_type=current_version.branch_type,
            branch_name=current_version.branch_name,
            commit_message=commit_message,
            author=author,
            bpmn_xml_snapshot=merged_xml,
            variable_definitions_snapshot=merged_variables,
            is_current=True,
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(new_version)

        # Mark all existing versions as not current
        await self.session.execute(
            select(ProcessVersion)
            .where(ProcessVersion.process_definition_id == process_definition_id)
            .where(ProcessVersion.is_current == True)  # noqa: E712
            .update({ProcessVersion.is_current: False})
        )

        # Update the process definition with the merged content
        process_def.bpmn_xml = merged_xml
        process_def.variable_definitions = merged_variables
        process_def.current_version_number = new_version.version_number
        process_def.latest_commit_message = commit_message
        process_def.latest_commit_author = author
        process_def.latest_commit_timestamp = datetime.now(timezone.utc)

        await self.session.commit()
        return new_version

    def _calculate_next_version(self, current_version: ProcessVersion) -> str:
        """Calculate the next version number for a merge.

        Args:
            current_version: The current version.

        Returns:
            The new version number string.
        """
        return f"{current_version.major_version}.{current_version.minor_version + 1}.0" 
"""Version management service for process definitions."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Union

from sqlalchemy import select, func, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.models.process import (
    BranchType,
    ChangeType,
    ProcessDefinition,
    ProcessElementChange,
    ProcessVersion,
)


class VersionManager:
    """Service for managing process definition versions."""

    def __init__(self, session: AsyncSession):
        """Initialize the version manager.

        Args:
            session: The database session.
        """
        self.session = session

    async def create_initial_version(
        self,
        process_definition_id: uuid.UUID,
        author: str,
        commit_message: str = "Initial version",
        branch_type: BranchType = BranchType.MAIN,
        branch_name: Optional[str] = None,
    ) -> ProcessVersion:
        """Create the initial version for a process definition.

        Args:
            process_definition_id: The process definition ID.
            author: The author of the version.
            commit_message: The commit message.
            branch_type: The branch type.
            branch_name: The branch name (required for non-MAIN branches).

        Returns:
            The created process version.

        Raises:
            ValueError: If the process definition already has versions.
        """
        process_def = await self.session.get(ProcessDefinition, process_definition_id)
        if not process_def:
            raise ValueError(f"Process definition {process_definition_id} not found")

        # Check if process already has versions
        existing_versions = await self.session.execute(
            select(ProcessVersion).where(
                ProcessVersion.process_definition_id == process_definition_id
            )
        )
        if existing_versions.first():
            raise ValueError(
                f"Process definition {process_definition_id} already has versions"
            )

        # Create initial version
        version = ProcessVersion(
            process_definition_id=process_definition_id,
            parent_version_id=None,
            version_number="1.0.0",
            major_version=1,
            minor_version=0,
            patch_version=0,
            branch_type=branch_type,
            branch_name=branch_name,
            commit_message=commit_message,
            author=author,
            bpmn_xml_snapshot=process_def.bpmn_xml,
            variable_definitions_snapshot=process_def.variable_definitions,
            is_current=True,
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(version)

        # Update process definition metadata
        process_def.current_version_number = "1.0.0"
        process_def.current_branch = branch_name if branch_name else "main"
        process_def.latest_commit_message = commit_message
        process_def.latest_commit_author = author
        process_def.latest_commit_timestamp = datetime.now(timezone.utc)

        await self.session.commit()
        return version

    async def create_new_version(
        self,
        process_definition_id: uuid.UUID,
        author: str,
        bpmn_xml: str,
        variable_definitions: List[Dict],
        commit_message: str,
        parent_version_id: Optional[uuid.UUID] = None,
        version_increment: str = "patch",
        element_changes: Optional[List[Dict]] = None,
        branch_type: BranchType = BranchType.MAIN,
        branch_name: Optional[str] = None,
    ) -> ProcessVersion:
        """Create a new version for a process definition.

        Args:
            process_definition_id: The process definition ID.
            author: The author of the version.
            bpmn_xml: The BPMN XML content.
            variable_definitions: The variable definitions.
            commit_message: The commit message.
            parent_version_id: The parent version ID (optional).
            version_increment: The type of version increment ("major", "minor", "patch").
            element_changes: List of element changes to record.
            branch_type: The branch type.
            branch_name: The branch name (required for non-MAIN branches).

        Returns:
            The created process version.

        Raises:
            ValueError: If the process definition or parent version is not found.
        """
        process_def = await self.session.get(ProcessDefinition, process_definition_id)
        if not process_def:
            raise ValueError(f"Process definition {process_definition_id} not found")

        # Get parent version (either specified or current)
        parent_version = None
        if parent_version_id:
            parent_version = await self.session.get(ProcessVersion, parent_version_id)
            if not parent_version:
                raise ValueError(f"Parent version {parent_version_id} not found")
        else:
            # Get current version
            result = await self.session.execute(
                select(ProcessVersion)
                .where(ProcessVersion.process_definition_id == process_definition_id)
                .where(ProcessVersion.is_current == True)  # noqa: E712
            )
            parent_version = result.scalar_one_or_none()
            if not parent_version:
                # No current version exists, create initial version instead
                return await self.create_initial_version(
                    process_definition_id, author, commit_message, branch_type, branch_name
                )

        # Calculate new version number
        major, minor, patch = (
            parent_version.major_version,
            parent_version.minor_version,
            parent_version.patch_version,
        )

        if version_increment == "major":
            major += 1
            minor = 0
            patch = 0
        elif version_increment == "minor":
            minor += 1
            patch = 0
        else:  # patch
            patch += 1

        version_number = f"{major}.{minor}.{patch}"

        # Mark all existing versions as not current
        await self.session.execute(
            update(ProcessVersion)
            .where(ProcessVersion.process_definition_id == process_definition_id)
            .where(ProcessVersion.is_current == True)  # noqa: E712
            .values(is_current=False)
        )

        # Create new version
        version = ProcessVersion(
            process_definition_id=process_definition_id,
            parent_version_id=parent_version.id,
            version_number=version_number,
            major_version=major,
            minor_version=minor,
            patch_version=patch,
            branch_type=branch_type,
            branch_name=branch_name,
            commit_message=commit_message,
            author=author,
            bpmn_xml_snapshot=bpmn_xml,
            variable_definitions_snapshot=variable_definitions,
            is_current=True,
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(version)
        # Flush the session to generate the version ID before adding element changes
        await self.session.flush()

        # Add element changes if provided
        if element_changes:
            for change in element_changes:
                element_change = ProcessElementChange(
                    version_id=version.id,
                    element_id=change["element_id"],
                    element_type=change["element_type"],
                    change_type=change["change_type"],
                    previous_values=change.get("previous_values"),
                    new_values=change.get("new_values"),
                    created_at=datetime.now(timezone.utc),
                )
                self.session.add(element_change)

        # Update process definition metadata
        process_def.current_version_number = version_number
        process_def.current_branch = branch_name if branch_name else "main"
        process_def.latest_commit_message = commit_message
        process_def.latest_commit_author = author
        process_def.latest_commit_timestamp = datetime.now(timezone.utc)

        # Update the process definition with the new content
        process_def.bpmn_xml = bpmn_xml
        process_def.variable_definitions = variable_definitions

        await self.session.commit()
        return version

    async def get_version_history(
        self, process_definition_id: uuid.UUID, limit: int = 20, offset: int = 0
    ) -> List[ProcessVersion]:
        """Get the version history for a process definition.

        Args:
            process_definition_id: The process definition ID.
            limit: Maximum number of versions to return.
            offset: Offset for pagination.

        Returns:
            The list of process versions.
        """
        result = await self.session.execute(
            select(ProcessVersion)
            .where(ProcessVersion.process_definition_id == process_definition_id)
            .order_by(ProcessVersion.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()

    async def get_version_count(self, process_definition_id: uuid.UUID) -> int:
        """Get the total count of versions for a process definition.

        Args:
            process_definition_id: The process definition ID.

        Returns:
            The count of versions.
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(ProcessVersion)
            .where(ProcessVersion.process_definition_id == process_definition_id)
        )
        return result.scalar_one()

    async def get_version(self, version_id: uuid.UUID) -> Optional[ProcessVersion]:
        """Get a specific version by ID.

        Args:
            version_id: The version ID.

        Returns:
            The process version or None if not found.
        """
        return await self.session.get(ProcessVersion, version_id)

    async def get_version_by_number(
        self, process_definition_id: uuid.UUID, version_number: str
    ) -> Optional[ProcessVersion]:
        """Get a specific version by number.

        Args:
            process_definition_id: The process definition ID.
            version_number: The version number (e.g., "1.0.0").

        Returns:
            The process version or None if not found.
        """
        result = await self.session.execute(
            select(ProcessVersion)
            .where(ProcessVersion.process_definition_id == process_definition_id)
            .where(ProcessVersion.version_number == version_number)
        )
        return result.scalar_one_or_none()

    async def get_version_element_changes(
        self, version_id: uuid.UUID
    ) -> List[ProcessElementChange]:
        """Get all element changes for a specific version.

        Args:
            version_id: The version ID.

        Returns:
            The list of element changes.
        """
        result = await self.session.execute(
            select(ProcessElementChange)
            .where(ProcessElementChange.version_id == version_id)
            .order_by(ProcessElementChange.created_at)
        )
        return result.scalars().all()

    async def restore_version(
        self, 
        version_id: uuid.UUID, 
        author: str, 
        commit_message: Optional[str] = None,
        branch_type: BranchType = BranchType.MAIN,
        branch_name: Optional[str] = None,
    ) -> ProcessVersion:
        """Restore a previous version.

        This creates a new version with the content of the specified version.

        Args:
            version_id: The version ID to restore.
            author: The author of the restoration.
            commit_message: The commit message (defaults to "Restored version X.Y.Z").
            branch_type: The branch type for the new version.
            branch_name: The branch name for the new version.

        Returns:
            The newly created version.

        Raises:
            ValueError: If the version is not found.
        """
        # Get the version to restore
        version_to_restore = await self.session.get(ProcessVersion, version_id)
        if not version_to_restore:
            raise ValueError(f"Version {version_id} not found")

        # Default commit message if not provided
        if not commit_message:
            commit_message = f"Restored version {version_to_restore.version_number}"

        # Create a new version with the content of the restored version
        return await self.create_new_version(
            process_definition_id=version_to_restore.process_definition_id,
            author=author,
            bpmn_xml=version_to_restore.bpmn_xml_snapshot,
            variable_definitions=version_to_restore.variable_definitions_snapshot,
            commit_message=commit_message,
            version_increment="minor",  # Restoring uses minor version increment by default
            branch_type=branch_type,
            branch_name=branch_name,
        )

    async def create_branch(
        self,
        process_definition_id: uuid.UUID,
        branch_name: str,
        branch_type: BranchType,
        parent_version_id: Optional[uuid.UUID] = None,
        author: str = "system",
        commit_message: Optional[str] = None,
    ) -> ProcessVersion:
        """Create a new branch from a version.

        Args:
            process_definition_id: The process definition ID.
            branch_name: The name of the new branch.
            branch_type: The type of branch.
            parent_version_id: The parent version ID (optional, uses current if not specified).
            author: The author of the branch.
            commit_message: The commit message (defaults to "Created branch X").

        Returns:
            The new branch version.

        Raises:
            ValueError: If the process definition or parent version is not found.
        """
        # Check if branch name is provided
        if not branch_name:
            raise ValueError("Branch name is required")

        # Default commit message if not provided
        if not commit_message:
            commit_message = f"Created branch {branch_name}"

        process_def = await self.session.get(ProcessDefinition, process_definition_id)
        if not process_def:
            raise ValueError(f"Process definition {process_definition_id} not found")

        # Get parent version (either specified or current)
        parent_version = None
        if parent_version_id:
            parent_version = await self.session.get(ProcessVersion, parent_version_id)
            if not parent_version:
                raise ValueError(f"Parent version {parent_version_id} not found")
        else:
            # Get current version
            result = await self.session.execute(
                select(ProcessVersion)
                .where(ProcessVersion.process_definition_id == process_definition_id)
                .where(ProcessVersion.is_current == True)  # noqa: E712
            )
            parent_version = result.scalar_one_or_none()
            if not parent_version:
                raise ValueError(
                    f"No current version found for process {process_definition_id}"
                )

        # Create a new version with the new branch
        branch_version = ProcessVersion(
            process_definition_id=process_definition_id,
            parent_version_id=parent_version.id,
            version_number=f"{parent_version.major_version}.{parent_version.minor_version}.{parent_version.patch_version}",
            major_version=parent_version.major_version,
            minor_version=parent_version.minor_version,
            patch_version=parent_version.patch_version,
            branch_type=branch_type,
            branch_name=branch_name,
            commit_message=commit_message,
            author=author,
            bpmn_xml_snapshot=parent_version.bpmn_xml_snapshot,
            variable_definitions_snapshot=parent_version.variable_definitions_snapshot,
            is_current=False,  # Branch is not current by default
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(branch_version)
        await self.session.commit()
        return branch_version

    async def has_conflicts(
        self, version_id: uuid.UUID, current_version_id: uuid.UUID
    ) -> Tuple[bool, List[Dict]]:
        """Check if there are conflicts between two versions.

        Args:
            version_id: The version ID to check.
            current_version_id: The current version ID to compare against.

        Returns:
            A tuple containing (has_conflicts, conflict_details).

        Raises:
            ValueError: If either version is not found.
        """
        # Get both versions
        version = await self.session.get(ProcessVersion, version_id)
        current_version = await self.session.get(ProcessVersion, current_version_id)

        if not version:
            raise ValueError(f"Version {version_id} not found")
        if not current_version:
            raise ValueError(f"Current version {current_version_id} not found")

        # Get changes for both versions since their common ancestor
        # This is a simplified conflict detection - in a real system,
        # you would implement a more sophisticated diff algorithm

        # Get element changes for both versions
        version_changes = await self.get_version_element_changes(version_id)
        current_changes = await self.get_version_element_changes(current_version_id)

        # Map changes by element ID
        version_changes_by_element = {
            change.element_id: change for change in version_changes
        }
        current_changes_by_element = {
            change.element_id: change for change in current_changes
        }

        # Find elements changed in both versions
        conflicts = []
        for element_id in set(version_changes_by_element.keys()) & set(
            current_changes_by_element.keys()
        ):
            version_change = version_changes_by_element[element_id]
            current_change = current_changes_by_element[element_id]

            # If both made changes of the same type to the same element, it's a conflict
            if version_change.change_type == current_change.change_type:
                conflicts.append(
                    {
                        "element_id": element_id,
                        "element_type": version_change.element_type,
                        "change_type": version_change.change_type.value,
                        "your_changes": version_change.new_values,
                        "current_changes": current_change.new_values,
                    }
                )

        return len(conflicts) > 0, conflicts 
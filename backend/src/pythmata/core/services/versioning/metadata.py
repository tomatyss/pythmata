"""Version metadata handling module."""

import uuid
from typing import Dict, List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from pythmata.models.process import ProcessDefinition, ProcessVersion


class VersionMetadata:
    """Service for handling version metadata."""

    def __init__(self, session: AsyncSession):
        """Initialize the version metadata service.

        Args:
            session: The database session.
        """
        self.session = session

    async def get_version_info(self, version_id: uuid.UUID) -> Optional[Dict]:
        """Get detailed information about a specific version.

        Args:
            version_id: The version ID.

        Returns:
            Dictionary with version information, or None if not found.
        """
        version = await self.session.get(ProcessVersion, version_id)
        if not version:
            return None

        # Get parent version details if available
        parent_version = None
        if version.parent_version_id:
            parent_version = await self.session.get(ProcessVersion, version.parent_version_id)

        # Get process definition
        process_def = await self.session.get(ProcessDefinition, version.process_definition_id)

        # Get child versions
        result = await self.session.execute(
            select(ProcessVersion).where(ProcessVersion.parent_version_id == version_id)
        )
        child_versions = result.scalars().all()

        return {
            "id": str(version.id),
            "process_definition": {
                "id": str(process_def.id),
                "name": process_def.name,
            },
            "version_number": version.version_number,
            "semantic_version": {
                "major": version.major_version,
                "minor": version.minor_version,
                "patch": version.patch_version,
            },
            "branch_info": {
                "type": version.branch_type.value,
                "name": version.branch_name,
            },
            "commit_message": version.commit_message,
            "author": version.author,
            "created_at": version.created_at.isoformat(),
            "is_current": version.is_current,
            "parent_version": {
                "id": str(parent_version.id) if parent_version else None,
                "version_number": parent_version.version_number if parent_version else None,
            },
            "child_versions": [
                {
                    "id": str(child.id),
                    "version_number": child.version_number,
                    "branch_type": child.branch_type.value,
                    "branch_name": child.branch_name,
                }
                for child in child_versions
            ],
        }

    async def get_branch_info(self, process_definition_id: uuid.UUID) -> Dict:
        """Get information about branches for a process definition.

        Args:
            process_definition_id: The process definition ID.

        Returns:
            Dictionary with branch information.
        """
        # Get all versions for this process
        result = await self.session.execute(
            select(ProcessVersion).where(
                ProcessVersion.process_definition_id == process_definition_id
            )
        )
        versions = result.scalars().all()

        # Group versions by branch
        branches = {}
        for version in versions:
            branch_name = version.branch_name or "main"
            if branch_name not in branches:
                branches[branch_name] = {
                    "name": branch_name,
                    "type": version.branch_type.value,
                    "versions": [],
                    "current_version": None,
                }
            branches[branch_name]["versions"].append(
                {
                    "id": str(version.id),
                    "version_number": version.version_number,
                    "created_at": version.created_at.isoformat(),
                    "is_current": version.is_current,
                    "author": version.author,
                    "commit_message": version.commit_message,
                }
            )
            if version.is_current:
                branches[branch_name]["current_version"] = {
                    "id": str(version.id),
                    "version_number": version.version_number,
                }

        # Sort versions within each branch by creation time
        for branch in branches.values():
            branch["versions"].sort(key=lambda v: v["created_at"], reverse=True)

        return {"branches": list(branches.values())}

    async def get_version_stats(self, process_definition_id: uuid.UUID) -> Dict:
        """Get statistics about versions for a process definition.

        Args:
            process_definition_id: The process definition ID.

        Returns:
            Dictionary with version statistics.
        """
        # Get total version count
        version_count_result = await self.session.execute(
            select(func.count(ProcessVersion.id)).where(
                ProcessVersion.process_definition_id == process_definition_id
            )
        )
        version_count = version_count_result.scalar_one()

        # Get branch count
        branch_count_result = await self.session.execute(
            select(func.count(func.distinct(ProcessVersion.branch_name))).where(
                ProcessVersion.process_definition_id == process_definition_id
            )
        )
        branch_count = branch_count_result.scalar_one()

        # Get author count
        author_count_result = await self.session.execute(
            select(func.count(func.distinct(ProcessVersion.author))).where(
                ProcessVersion.process_definition_id == process_definition_id
            )
        )
        author_count = author_count_result.scalar_one()

        # Get most recent version
        recent_version_result = await self.session.execute(
            select(ProcessVersion)
            .where(ProcessVersion.process_definition_id == process_definition_id)
            .order_by(ProcessVersion.created_at.desc())
            .limit(1)
        )
        recent_version = recent_version_result.scalar_one_or_none()

        # Get current version
        current_version_result = await self.session.execute(
            select(ProcessVersion)
            .where(ProcessVersion.process_definition_id == process_definition_id)
            .where(ProcessVersion.is_current == True)  # noqa: E712
        )
        current_version = current_version_result.scalar_one_or_none()

        return {
            "total_versions": version_count,
            "branch_count": branch_count,
            "author_count": author_count,
            "first_version_date": None,  # Would need separate query
            "most_recent_version": {
                "id": str(recent_version.id) if recent_version else None,
                "version_number": recent_version.version_number if recent_version else None,
                "date": recent_version.created_at.isoformat() if recent_version else None,
                "author": recent_version.author if recent_version else None,
            },
            "current_version": {
                "id": str(current_version.id) if current_version else None,
                "version_number": current_version.version_number if current_version else None,
                "date": current_version.created_at.isoformat() if current_version else None,
                "author": current_version.author if current_version else None,
            },
        } 
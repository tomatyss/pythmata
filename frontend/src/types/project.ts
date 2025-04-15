/**
 * Project management types
 */

import { User } from './auth';

/**
 * API response wrapper
 */
export interface ApiResponse<T> {
  data: T;
  message?: string;
}

/**
 * Paginated response wrapper
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

/**
 * Project status enum
 */
export enum ProjectStatus {
  DRAFT = 'DRAFT',
  ACTIVE = 'ACTIVE',
  ARCHIVED = 'ARCHIVED',
  COMPLETED = 'COMPLETED',
}

/**
 * Tag model
 */
export interface Tag {
  id: string;
  name: string;
  color: string;
  createdAt: string;
}

/**
 * Tag create request
 */
export interface TagCreate {
  name: string;
  color: string;
}

/**
 * Tag update request
 */
export interface TagUpdate {
  name?: string;
  color?: string;
}

/**
 * Project role permissions
 */
export interface ProjectRolePermissions {
  manageProject: boolean;
  manageMembers: boolean;
  manageProcesses: boolean;
  viewProcesses: boolean;
  executeProcesses: boolean;
  editDescription?: boolean;
}

/**
 * Project role model
 */
export interface ProjectRole {
  id: string;
  name: string;
  permissions: ProjectRolePermissions;
  createdAt: string;
  updatedAt: string;
}

/**
 * Project role create request
 */
export interface ProjectRoleCreate {
  name: string;
  permissions: ProjectRolePermissions;
}

/**
 * Project role update request
 */
export interface ProjectRoleUpdate {
  name?: string;
  permissions?: ProjectRolePermissions;
}

/**
 * Project member model
 */
export interface ProjectMember {
  id: string;
  user: User;
  role: ProjectRole;
  joinedAt: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * Project member create request
 */
export interface ProjectMemberCreate {
  userId: string;
  roleId: string;
}

/**
 * Project member update request
 */
export interface ProjectMemberUpdate {
  roleId: string;
}

/**
 * Project description model
 */
export interface ProjectDescription {
  id: string;
  projectId: string;
  content: string;
  version: number;
  isCurrent: boolean;
  createdAt: string;
  tags: Tag[];
}

/**
 * Project description create request
 */
export interface ProjectDescriptionCreate {
  content: string;
  tagIds?: string[];
}

/**
 * Project description update request
 */
export interface ProjectDescriptionUpdate {
  content?: string;
  tagIds?: string[];
}

/**
 * Project base model
 */
export interface ProjectBase {
  name: string;
  description?: string;
  status: ProjectStatus | string;
}

/**
 * Project model
 */
export interface Project extends ProjectBase {
  id: string;
  ownerId: string;
  createdAt: string;
  updatedAt: string;
  owner: User;
  members: ProjectMember[];
  currentDescription?: ProjectDescription;
  descriptions?: ProjectDescription[];
  processCount?: number;
}

/**
 * Project create request
 */
export type ProjectCreate = ProjectBase;

/**
 * Project update request
 */
export interface ProjectUpdate {
  name?: string;
  description?: string;
  status?: ProjectStatus | string;
}

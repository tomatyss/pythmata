/**
 * Project management API service
 * Provides methods for interacting with the project management API endpoints
 */

import { AxiosResponse } from 'axios';
import axiosInstance from '@/lib/axios';
import { ApiError } from '@/lib/errors';
import { convertKeysToSnake } from '@/utils/case';
import {
  Project,
  ProjectCreate,
  ProjectUpdate,
  ProjectMember,
  ProjectMemberCreate,
  ProjectMemberUpdate,
  ProjectRole,
  ProjectRoleCreate,
  ProjectRoleUpdate,
  ProjectDescription,
  ProjectDescriptionCreate,
  Tag,
  TagCreate,
  TagUpdate,
  ApiResponse,
} from '@/types/project';

class ProjectService {
  /**
   * Get a list of projects
   * @param options - Query options for filtering and pagination
   * @returns Promise with the list of projects
   */
  async getProjects(options?: {
    skip?: number;
    limit?: number;
    status?: string;
  }): Promise<ApiResponse<Project[]>> {
    try {
      const params = {
        ...(options?.skip !== undefined ? { skip: options.skip } : {}),
        ...(options?.limit !== undefined ? { limit: options.limit } : {}),
        ...(options?.status ? { status: options.status } : {}),
      };

      const response: AxiosResponse = await axiosInstance.get('/projects', {
        params,
      });
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to fetch projects', 500);
    }
  }

  /**
   * Get a project by ID
   * @param id - Project ID
   * @returns Promise with the project details
   */
  async getProject(id: string): Promise<ApiResponse<Project>> {
    try {
      const response: AxiosResponse = await axiosInstance.get(
        `/projects/${id}`
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to fetch project', 500);
    }
  }

  /**
   * Create a new project
   * @param data - Project data
   * @returns Promise with the created project
   */
  async createProject(data: ProjectCreate): Promise<ApiResponse<Project>> {
    try {
      const response: AxiosResponse = await axiosInstance.post(
        '/projects',
        convertKeysToSnake(data)
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to create project', 500);
    }
  }

  /**
   * Update a project
   * @param id - Project ID
   * @param data - Project data to update
   * @returns Promise with the updated project
   */
  async updateProject(
    id: string,
    data: ProjectUpdate
  ): Promise<ApiResponse<Project>> {
    try {
      const response: AxiosResponse = await axiosInstance.put(
        `/projects/${id}`,
        convertKeysToSnake(data)
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to update project', 500);
    }
  }

  /**
   * Delete a project
   * @param id - Project ID
   * @returns Promise with no content
   */
  async deleteProject(id: string): Promise<void> {
    try {
      await axiosInstance.delete(`/projects/${id}`);
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to delete project', 500);
    }
  }

  /**
   * Get project members
   * @param projectId - Project ID
   * @returns Promise with the list of project members
   */
  async getProjectMembers(
    projectId: string
  ): Promise<ApiResponse<ProjectMember[]>> {
    try {
      const response: AxiosResponse = await axiosInstance.get(
        `/projects/${projectId}/members`
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to fetch project members', 500);
    }
  }

  /**
   * Add a member to a project
   * @param projectId - Project ID
   * @param data - Member data
   * @returns Promise with the added member
   */
  async addProjectMember(
    projectId: string,
    data: ProjectMemberCreate
  ): Promise<ApiResponse<ProjectMember>> {
    try {
      const response: AxiosResponse = await axiosInstance.post(
        `/projects/${projectId}/members`,
        convertKeysToSnake(data)
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to add project member', 500);
    }
  }

  /**
   * Update a project member's role
   * @param projectId - Project ID
   * @param userId - User ID
   * @param data - Member data to update
   * @returns Promise with the updated member
   */
  async updateProjectMember(
    projectId: string,
    userId: string,
    data: ProjectMemberUpdate
  ): Promise<ApiResponse<ProjectMember>> {
    try {
      const response: AxiosResponse = await axiosInstance.put(
        `/projects/${projectId}/members/${userId}`,
        convertKeysToSnake(data)
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to update project member', 500);
    }
  }

  /**
   * Remove a member from a project
   * @param projectId - Project ID
   * @param userId - User ID
   * @returns Promise with no content
   */
  async removeProjectMember(projectId: string, userId: string): Promise<void> {
    try {
      await axiosInstance.delete(`/projects/${projectId}/members/${userId}`);
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to remove project member', 500);
    }
  }

  /**
   * Get project descriptions
   * @param projectId - Project ID
   * @returns Promise with the list of project descriptions
   */
  async getProjectDescriptions(
    projectId: string
  ): Promise<ApiResponse<ProjectDescription[]>> {
    try {
      const response: AxiosResponse = await axiosInstance.get(
        `/projects/${projectId}/descriptions`
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to fetch project descriptions', 500);
    }
  }

  /**
   * Create a new project description
   * @param projectId - Project ID
   * @param data - Description data
   * @returns Promise with the created description
   */
  async createProjectDescription(
    projectId: string,
    data: ProjectDescriptionCreate
  ): Promise<ApiResponse<ProjectDescription>> {
    try {
      const response: AxiosResponse = await axiosInstance.post(
        `/projects/${projectId}/descriptions`,
        convertKeysToSnake(data)
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to create project description', 500);
    }
  }

  /**
   * Get a project description by ID
   * @param projectId - Project ID
   * @param descriptionId - Description ID
   * @returns Promise with the description details
   */
  async getProjectDescription(
    projectId: string,
    descriptionId: string
  ): Promise<ApiResponse<ProjectDescription>> {
    try {
      const response: AxiosResponse = await axiosInstance.get(
        `/projects/${projectId}/descriptions/${descriptionId}`
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to fetch project description', 500);
    }
  }

  /**
   * Set a description as the current version
   * @param projectId - Project ID
   * @param descriptionId - Description ID
   * @returns Promise with the updated description
   */
  async setCurrentDescription(
    projectId: string,
    descriptionId: string
  ): Promise<ApiResponse<ProjectDescription>> {
    try {
      const response: AxiosResponse = await axiosInstance.put(
        `/projects/${projectId}/descriptions/${descriptionId}/set-current`
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to set current description', 500);
    }
  }

  /**
   * Get project roles
   * @param projectId - Project ID
   * @returns Promise with the list of project roles
   */
  async getProjectRoles(
    projectId: string
  ): Promise<ApiResponse<ProjectRole[]>> {
    try {
      const response: AxiosResponse = await axiosInstance.get(
        `/projects/${projectId}/roles`
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to fetch project roles', 500);
    }
  }

  /**
   * Create a new project role
   * @param data - Role data
   * @returns Promise with the created role
   */
  async createProjectRole(
    data: ProjectRoleCreate
  ): Promise<ApiResponse<ProjectRole>> {
    try {
      const response: AxiosResponse = await axiosInstance.post(
        '/projects/roles',
        convertKeysToSnake(data)
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to create project role', 500);
    }
  }

  /**
   * Update a project role
   * @param roleId - Role ID
   * @param data - Role data to update
   * @returns Promise with the updated role
   */
  async updateProjectRole(
    roleId: string,
    data: ProjectRoleUpdate
  ): Promise<ApiResponse<ProjectRole>> {
    try {
      const response: AxiosResponse = await axiosInstance.put(
        `/projects/roles/${roleId}`,
        convertKeysToSnake(data)
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to update project role', 500);
    }
  }

  /**
   * Get tags
   * @returns Promise with the list of tags
   */
  async getTags(): Promise<ApiResponse<Tag[]>> {
    try {
      const response: AxiosResponse = await axiosInstance.get('/projects/tags');
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to fetch tags', 500);
    }
  }

  /**
   * Create a new tag
   * @param data - Tag data
   * @returns Promise with the created tag
   */
  async createTag(data: TagCreate): Promise<ApiResponse<Tag>> {
    try {
      const response: AxiosResponse = await axiosInstance.post(
        '/projects/tags',
        convertKeysToSnake(data)
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to create tag', 500);
    }
  }

  /**
   * Update a tag
   * @param tagId - Tag ID
   * @param data - Tag data to update
   * @returns Promise with the updated tag
   */
  async updateTag(tagId: string, data: TagUpdate): Promise<ApiResponse<Tag>> {
    try {
      const response: AxiosResponse = await axiosInstance.put(
        `/projects/tags/${tagId}`,
        convertKeysToSnake(data)
      );
      return response.data;
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to update tag', 500);
    }
  }

  /**
   * Delete a tag
   * @param tagId - Tag ID
   * @returns Promise with no content
   */
  async deleteTag(tagId: string): Promise<void> {
    try {
      await axiosInstance.delete(`/projects/tags/${tagId}`);
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Failed to delete tag', 500);
    }
  }
}

// Create a singleton instance
const projectService = new ProjectService();

export default projectService;

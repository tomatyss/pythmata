// Version Enums
export enum VersionIncrement {
  MAJOR = 'MAJOR',
  MINOR = 'MINOR',
  PATCH = 'PATCH',
}

export enum BranchType {
  MAIN = 'MAIN',
  FEATURE = 'FEATURE',
  BUGFIX = 'BUGFIX',
  RELEASE = 'RELEASE',
}

export enum ChangeType {
  ADDED = 'ADDED',
  MODIFIED = 'MODIFIED',
  REMOVED = 'REMOVED',
}

// Variable Definition Types
export interface VariableDefinition {
  id: string;
  name: string;
  type: string;
  defaultValue?: unknown;
  description?: string;
}

// Version Types
export interface ElementChange {
  elementId: string;
  elementType: string;
  changeType: ChangeType;
  previousValues?: Record<string, unknown>;
  newValues?: Record<string, unknown>;
}

export interface VersionBase {
  author: string;
  commitMessage: string;
  branchType: BranchType;
  branchName?: string;
}

export interface VersionCreate extends VersionBase {
  processDefinitionId: string;
  bpmnXml: string;
  variableDefinitions?: VariableDefinition[];
  parentVersionId?: string;
  versionIncrement: VersionIncrement;
  elementChanges?: ElementChange[];
}

export interface Version {
  id: string;
  processDefinitionId: string;
  author: string;
  versionNumber: string;
  commitMessage: string;
  branchType: BranchType;
  branchName?: string;
  createdAt: string;
}

export interface VersionDetail extends Version {
  bpmnXml: string;
  variableDefinitions: VariableDefinition[];
  parentVersionId?: string;
  elementChanges: ElementChange[];
}

export interface VersionResponse {
  id: string;
  processDefinitionId: string;
  author: string;
  versionNumber: string;
  commitMessage: string;
  branchType: BranchType;
  branchName?: string;
  createdAt: string;
}

export interface VersionListResponse {
  versions: Version[];
  total: number;
}

export interface VersionDetailResponse extends VersionResponse {
  bpmnXml: string;
  variableDefinitions: VariableDefinition[];
  parentVersionId?: string;
  elementChanges: ElementChange[];
}

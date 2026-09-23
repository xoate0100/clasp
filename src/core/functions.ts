// Copyright 2025 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

// This file defines the `Functions` class, which provides methods for
// listing and executing functions within a Google Apps Script project.

import Debug from 'debug';
import {google} from 'googleapis';

import {ClaspOptions, assertAuthenticated, assertScriptConfigured, handleApiError} from './utils.js';

const debug = Debug('clasp:core');

/**
 * Provides methods for interacting with functions within a Google Apps Script project,
 * such as listing available functions and executing them remotely.
 */
export class Functions {
  private options: ClaspOptions;

  constructor(options: ClaspOptions) {
    this.options = options;
  }

  /**
   * Retrieves a list of all function names in the Apps Script project.
   * @returns {Promise<string[]>} A promise that resolves to an array of function names.
   * @throws {Error} If there's an API error or authentication/configuration issues.
   */
  async getFunctionNames(): Promise<Array<string>> {
    debug('Fetching runnable functions');
    assertAuthenticated(this.options);
    assertScriptConfigured(this.options);

    const credentials = this.options.credentials;
    const scriptId = this.options.project.scriptId;

    const script = google.script({version: 'v1', auth: credentials});
    const res = await script.projects.getContent({scriptId});

    const files = res.data.files;
    const functions: string[] = [];
    if (!files) {
      return functions;
    }

    return files.flatMap(file => file.functionSet?.values ?? []).map(func => func.name!);
  }

  /**
   * Executes a specified function in the Apps Script project.
   * @param {string} functionName - The name of the function to run.
   * @param {unknown[]} parameters - An array of parameters to pass to the function.
   * These will be JSON-stringified.
   * @param {boolean} [devMode=true] - Whether to run the function in development mode.
   * Dev mode executes the latest saved code instead of the last deployed version.
   * @returns {Promise<any>} A promise that resolves to the response from the function execution,
   * or undefined if an error occurs before the API call.
   * @throws {Error} If there's an API error, authentication/configuration issues,
   * or if the function execution itself returns an error.
   */
  async runFunction(functionName: string, parameters: unknown[], devMode = true, deploymentId?: string) {
    debug('Running script function %s', functionName);
    assertAuthenticated(this.options);
    assertScriptConfigured(this.options);

    const credentials = this.options.credentials;
    const scriptId = devMode ? this.options.project.scriptId : await this.nonDevScriptId(deploymentId);
    const script = google.script({version: 'v1', auth: credentials});

    try {
      const request = {
        scriptId,
        requestBody: {
          function: functionName,
          parameters: parameters ?? [],
          devMode,
        },
      };
      debug('Running function with request: %O', request);
      const res = await script.scripts.run(request);
      if (!res.data) {
        throw new Error('Function returned undefined');
      }
      return res.data;
    } catch (error) {
      handleApiError(error);
    }
  }

  /**
   * scripts.run rejects the project script ID when devMode is false.
   * The path must be an API-executable deployment ID.
   */
  private async nonDevScriptId(deploymentId?: string): Promise<string> {
    if (deploymentId) {
      return deploymentId;
    }
    const ids = await this.executionApiDeploymentIds();
    const only = ids[0];
    if (ids.length === 1 && only) {
      return only;
    }
    const detail = ids.length
      ? `Multiple API-executable deployments: ${ids.join(', ')}.`
      : 'No API-executable deployment was found.';
    throw new Error(`${detail} Pass --deploymentId with an EXECUTION_API deployment.`, {
      cause: {code: 'DEPLOYMENT_ID_REQUIRED', deploymentIds: ids},
    });
  }

  private async executionApiDeploymentIds(): Promise<string[]> {
    const project = this.options.project;
    const projectId = project?.scriptId;
    if (!project || !projectId) {
      throw new Error('Script ID is required to resolve an API-executable deployment.');
    }
    const script = google.script({version: 'v1', auth: this.options.credentials});
    const listed = await script.projects.deployments.list({scriptId: projectId});
    const ids: string[] = [];
    for (const deployment of listed.data.deployments ?? []) {
      const id = await this.executionApiId(script, projectId, deployment);
      if (id) {
        ids.push(id);
      }
    }
    return ids;
  }

  private async executionApiId(
    script: ReturnType<typeof google.script>,
    projectId: string,
    deployment: DeploymentWithEntryPoints,
  ): Promise<string | undefined> {
    const deploymentId = deployment.deploymentId ?? undefined;
    if (!deploymentId) {
      return undefined;
    }
    const entryPoints = deployment.entryPoints ?? (await this.fetchEntryPoints(script, projectId, deploymentId));
    const executable = entryPoints.some(entry => entry.entryPointType === 'EXECUTION_API');
    return executable ? deploymentId : undefined;
  }

  private async fetchEntryPoints(
    script: ReturnType<typeof google.script>,
    projectId: string,
    deploymentId: string,
  ): Promise<NonNullable<DeploymentWithEntryPoints['entryPoints']>> {
    const res = await script.projects.deployments.get({scriptId: projectId, deploymentId});
    return res.data.entryPoints ?? [];
  }
}

type DeploymentWithEntryPoints = {
  deploymentId?: string | null;
  entryPoints?: Array<{entryPointType?: string | null}> | null;
};

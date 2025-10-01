import type { AgentCompleteCreate, PromptCreateData } from './types';

export interface AIAgentConfig {
  name: string;
  description: string;
  return_type: 'structured' | 'unstructured';
  prompts: Array<{
    prompt_type: 'system' | 'user';
    content: string;
    placeholders: Record<string, string>;
  }>;
  schema_definition?: Record<string, any>;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  config?: AgentCompleteCreate;
}

/**
 * Validates and transforms AI-generated agent configuration to Django format
 */
export function validateAndTransformConfig(
  aiConfig: any,
  projectId: number,
  toolIds: number[] = []
): ValidationResult {
  const errors: string[] = [];

  // Basic structure validation
  if (!aiConfig || typeof aiConfig !== 'object') {
    return { isValid: false, errors: ['Invalid configuration object'] };
  }

  // Required fields validation
  if (!aiConfig.name || typeof aiConfig.name !== 'string' || !aiConfig.name.trim()) {
    errors.push('Agent name is required');
  }

  if (!aiConfig.description || typeof aiConfig.description !== 'string' || !aiConfig.description.trim()) {
    errors.push('Agent description is required');
  }

  if (!aiConfig.return_type || !['structured', 'unstructured'].includes(aiConfig.return_type)) {
    errors.push('Valid return type (structured/unstructured) is required');
  }

  // Prompts validation
  if (!Array.isArray(aiConfig.prompts) || aiConfig.prompts.length === 0) {
    errors.push('At least one prompt is required');
  } else {
    // Validate individual prompts
    for (let i = 0; i < aiConfig.prompts.length; i++) {
      const prompt = aiConfig.prompts[i];

      if (!prompt.prompt_type || !['system', 'user'].includes(prompt.prompt_type)) {
        errors.push(`Prompt ${i + 1}: Invalid prompt type`);
      }

      if (!prompt.content || typeof prompt.content !== 'string' || !prompt.content.trim()) {
        errors.push(`Prompt ${i + 1}: Content is required`);
      }

      if (!prompt.placeholders || typeof prompt.placeholders !== 'object') {
        errors.push(`Prompt ${i + 1}: Placeholders must be an object`);
      }
    }
  }

  // Schema validation for structured agents
  if (aiConfig.return_type === 'structured') {
    if (!aiConfig.schema_definition || typeof aiConfig.schema_definition !== 'object') {
      errors.push('Schema definition is required for structured agents');
    } else {
      const schema = aiConfig.schema_definition;

      if (schema.type !== 'object') {
        errors.push('Schema type must be "object"');
      }

      if (!schema.properties || typeof schema.properties !== 'object') {
        errors.push('Schema must have properties');
      }

      if (!Array.isArray(schema.required)) {
        errors.push('Schema must have required fields array');
      }
    }
  }

  // Project validation
  if (!projectId || projectId <= 0) {
    errors.push('Valid project ID is required');
  }

  if (errors.length > 0) {
    return { isValid: false, errors };
  }

  // Transform to Django format
  const prompts: PromptCreateData[] = aiConfig.prompts.map((prompt: any) => ({
    prompt_type: prompt.prompt_type,
    content: prompt.content,
    placeholders: prompt.placeholders || {},
  }));

  const transformedConfig: AgentCompleteCreate = {
    name: aiConfig.name.trim(),
    description: aiConfig.description.trim(),
    project: projectId,
    return_type: aiConfig.return_type,
    schema_definition: aiConfig.return_type === 'structured' ? aiConfig.schema_definition : undefined,
    prompts: prompts.length > 0 ? prompts : undefined,
    tool_ids: toolIds.length > 0 ? toolIds : undefined,
  };

  return {
    isValid: true,
    errors: [],
    config: transformedConfig,
  };
}

/**
 * Extracts placeholders from prompt content using {placeholder} syntax
 */
export function extractPlaceholders(content: string): Record<string, string> {
  const placeholderRegex = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g;
  const placeholders: Record<string, string> = {};
  let match;

  while ((match = placeholderRegex.exec(content)) !== null) {
    const placeholderName = match[1];
    if (!placeholders[placeholderName]) {
      placeholders[placeholderName] = `Provide a value for ${placeholderName}`;
    }
  }

  return placeholders;
}

/**
 * Health check for AI agent builder service
 */
export async function checkAgentBuilderHealth(baseUrl: string): Promise<boolean> {
  try {
    const response = await fetch(`${baseUrl}/healthz`, {
      method: 'GET',
      headers: { 'Accept': 'text/plain' },
      signal: AbortSignal.timeout(5000), // 5 second timeout for health check
    });

    return response.ok && (await response.text()) === 'ok';
  } catch (error) {
    console.error('Agent builder health check failed:', error);
    return false;
  }
}
export interface AIWorkflowConfig {
  name: string;
  description: string;
  nodes: Array<{
    id: string;
    type: string;
    position: { x: number; y: number };
    config: Record<string, any>;
  }>;
  edges: Array<{
    id: string;
    source: string;
    target: string;
  }>;
  properties?: {
    timeout?: number;
    retry_count?: number;
    schedule?: string;
    watermark_start_date?: string;
    watermark_end_date?: string;
    notification_email?: string;
  };
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  config?: AIWorkflowConfig;
}

/**
 * Validates AI-generated workflow configuration
 */
export function validateWorkflowConfig(aiConfig: any): ValidationResult {
  const errors: string[] = [];

  // Basic structure validation
  if (!aiConfig || typeof aiConfig !== 'object') {
    return { isValid: false, errors: ['Invalid configuration object'] };
  }

  // Required fields validation
  if (!aiConfig.name || typeof aiConfig.name !== 'string' || !aiConfig.name.trim()) {
    errors.push('Workflow name is required');
  }

  if (!aiConfig.description || typeof aiConfig.description !== 'string' || !aiConfig.description.trim()) {
    errors.push('Workflow description is required');
  }

  // Nodes validation
  if (!Array.isArray(aiConfig.nodes) || aiConfig.nodes.length === 0) {
    errors.push('At least one node is required');
  } else {
    // Validate individual nodes
    const validNodeTypes = new Set(['database', 'agent', 'output', 'filter', 'script', 'conditional']);
    const nodeIds = new Set<string>();

    for (let i = 0; i < aiConfig.nodes.length; i++) {
      const node = aiConfig.nodes[i];

      if (!node.id || typeof node.id !== 'string') {
        errors.push(`Node ${i + 1}: Invalid or missing ID`);
      } else {
        if (nodeIds.has(node.id)) {
          errors.push(`Node ${i + 1}: Duplicate node ID '${node.id}'`);
        }
        nodeIds.add(node.id);
      }

      if (!node.type || !validNodeTypes.has(node.type)) {
        errors.push(`Node ${i + 1}: Invalid node type '${node.type}'. Must be one of: ${Array.from(validNodeTypes).join(', ')}`);
      }

      if (!node.position || typeof node.position !== 'object') {
        errors.push(`Node ${i + 1}: Missing or invalid position`);
      } else {
        if (typeof node.position.x !== 'number' || typeof node.position.y !== 'number') {
          errors.push(`Node ${i + 1}: Position must have numeric x and y coordinates`);
        }
      }

      if (!node.config || typeof node.config !== 'object') {
        errors.push(`Node ${i + 1}: Missing or invalid config`);
      } else if (!node.config.label || typeof node.config.label !== 'string') {
        errors.push(`Node ${i + 1}: Config must have a label`);
      }
    }

    // Edges validation
    if (!Array.isArray(aiConfig.edges)) {
      errors.push('Edges must be an array');
    } else {
      const edgeIds = new Set<string>();

      for (let i = 0; i < aiConfig.edges.length; i++) {
        const edge = aiConfig.edges[i];

        if (!edge.id || typeof edge.id !== 'string') {
          errors.push(`Edge ${i + 1}: Invalid or missing ID`);
        } else {
          if (edgeIds.has(edge.id)) {
            errors.push(`Edge ${i + 1}: Duplicate edge ID '${edge.id}'`);
          }
          edgeIds.add(edge.id);
        }

        if (!edge.source || typeof edge.source !== 'string') {
          errors.push(`Edge ${i + 1}: Invalid or missing source`);
        } else if (!nodeIds.has(edge.source)) {
          errors.push(`Edge ${i + 1}: Source node '${edge.source}' does not exist`);
        }

        if (!edge.target || typeof edge.target !== 'string') {
          errors.push(`Edge ${i + 1}: Invalid or missing target`);
        } else if (!nodeIds.has(edge.target)) {
          errors.push(`Edge ${i + 1}: Target node '${edge.target}' does not exist`);
        }
      }
    }
  }

  // Properties validation (optional but must be valid if present)
  if (aiConfig.properties && typeof aiConfig.properties !== 'object') {
    errors.push('Properties must be an object');
  } else if (aiConfig.properties) {
    const props = aiConfig.properties;

    if (props.timeout !== undefined && (typeof props.timeout !== 'number' || props.timeout <= 0)) {
      errors.push('Timeout must be a positive number');
    }

    if (props.retry_count !== undefined && (typeof props.retry_count !== 'number' || props.retry_count < 0)) {
      errors.push('Retry count must be a non-negative number');
    }

    if (props.schedule !== undefined && typeof props.schedule !== 'string') {
      errors.push('Schedule must be a string');
    }

    if (props.notification_email !== undefined && typeof props.notification_email !== 'string') {
      errors.push('Notification email must be a string');
    }
  }

  if (errors.length > 0) {
    return { isValid: false, errors };
  }

  // Transform to validated config
  const validatedConfig: AIWorkflowConfig = {
    name: aiConfig.name.trim(),
    description: aiConfig.description.trim(),
    nodes: aiConfig.nodes.map((node: any) => ({
      id: node.id,
      type: node.type,
      position: { x: node.position.x, y: node.position.y },
      config: node.config,
    })),
    edges: aiConfig.edges.map((edge: any) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
    })),
    properties: aiConfig.properties || {
      timeout: 3600,
      retry_count: 3,
    },
  };

  return {
    isValid: true,
    errors: [],
    config: validatedConfig,
  };
}

/**
 * Health check for workflow builder service
 */
export async function checkWorkflowBuilderHealth(baseUrl: string): Promise<boolean> {
  try {
    const response = await fetch(`${baseUrl}/healthz`, {
      method: 'GET',
      headers: { 'Accept': 'text/plain' },
      signal: AbortSignal.timeout(5000), // 5 second timeout for health check
    });

    return response.ok && (await response.text()) === 'ok';
  } catch (error) {
    console.error('Workflow builder health check failed:', error);
    return false;
  }
}

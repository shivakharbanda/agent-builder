export interface WorkflowNode {
  id: string;
  type: string;
  position: { x: number; y: number };
  data: {
    label: string;
    config?: Record<string, any>;
    onDelete?: (id: string) => void;
    onConfigChange?: (id: string, config: Record<string, any>) => void;
  };
  selected?: boolean;
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  animated?: boolean;
  style?: Record<string, any>;
}

export interface WorkflowConfig {
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
  properties: {
    watermark_start_date?: string;
    watermark_end_date?: string;
    schedule?: string;
    timeout?: number;
    retry_count?: number;
    notification_email?: string;
  };
  metadata: {
    name: string;
    description: string;
    version: string;
    created: string;
    updated: string;
  };
}
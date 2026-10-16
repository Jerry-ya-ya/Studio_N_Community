export type MathGraphDirection = 'center' | 'dependency' | 'application';

export interface MathSymbolDefinition {
  symbol: string;
  latex: string;
  description: string;
}

export interface MathVisualizationDefinition {
  type: 'derivative-tangent';
  caption: string;
}

export interface MathKnowledgeNode {
  id: string;
  title: string;
  category: string;
  definition: string;
  latex: string;
  simpleExplanation: string;
  symbolDefinitions: MathSymbolDefinition[];
  visualization?: MathVisualizationDefinition;
}

export interface MathKnowledgeEdge {
  id: string;
  source: string;
  target: string;
  relation: string;
}

export interface MathKnowledgeDataset {
  version: number;
  defaultCenter: string;
  nodes: MathKnowledgeNode[];
  edges: MathKnowledgeEdge[];
}

export interface LocalMathNode extends MathKnowledgeNode {
  graphDirection: MathGraphDirection;
  graphDepth: number;
}

export interface LocalMathGraph {
  centerId: string;
  nodes: LocalMathNode[];
  edges: MathKnowledgeEdge[];
}

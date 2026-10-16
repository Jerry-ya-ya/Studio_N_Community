import { MathGraphTraversalService } from './math-graph-traversal.service';
import { MathKnowledgeDataset, MathKnowledgeNode } from './math-knowledge.models';

describe('MathGraphTraversalService', () => {
  const node = (id: string): MathKnowledgeNode => ({
    id,
    title: id,
    category: 'test',
    definition: id,
    latex: id,
    simpleExplanation: id,
    symbolDefinitions: [],
  });

  const dataset: MathKnowledgeDataset = {
    version: 1,
    defaultCenter: 'center',
    nodes: ['dependency-2', 'dependency-1', 'center', 'application-1', 'application-2']
      .map(node),
    edges: [
      { id: 'd2-d1', source: 'dependency-2', target: 'dependency-1', relation: 'requires' },
      { id: 'd1-center', source: 'dependency-1', target: 'center', relation: 'requires' },
      { id: 'center-a1', source: 'center', target: 'application-1', relation: 'supports' },
      { id: 'a1-a2', source: 'application-1', target: 'application-2', relation: 'supports' },
    ],
  };

  const service = new MathGraphTraversalService();

  it('walks incoming edges for dependencies and outgoing edges for applications', () => {
    const graph = service.createLocalGraph(dataset, 'center', 2, 1);

    expect(graph.nodes.map(item => item.id)).toEqual([
      'dependency-2',
      'dependency-1',
      'center',
      'application-1',
    ]);
    expect(graph.nodes.find(item => item.id === 'dependency-2')?.graphDepth).toBe(2);
    expect(graph.nodes.find(item => item.id === 'application-1')?.graphDirection)
      .toBe('application');
  });

  it('honors zero-depth boundaries independently', () => {
    const graph = service.createLocalGraph(dataset, 'center', 0, 0);

    expect(graph.nodes.map(item => item.id)).toEqual(['center']);
    expect(graph.edges).toEqual([]);
  });
});

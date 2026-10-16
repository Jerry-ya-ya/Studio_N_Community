import { Injectable } from '@angular/core';

import {
  LocalMathGraph,
  LocalMathNode,
  MathGraphDirection,
  MathKnowledgeDataset,
  MathKnowledgeEdge,
} from './math-knowledge.models';

interface TraversalRecord {
  direction: MathGraphDirection;
  depth: number;
}

@Injectable()
export class MathGraphTraversalService {
  createLocalGraph(
    dataset: MathKnowledgeDataset,
    centerId: string,
    dependencyDepth: number,
    applicationDepth: number,
  ): LocalMathGraph {
    const records = new Map<string, TraversalRecord>([
      [centerId, { direction: 'center', depth: 0 }],
    ]);

    this.traverse(dataset.edges, centerId, dependencyDepth, 'dependency', records);
    this.traverse(dataset.edges, centerId, applicationDepth, 'application', records);

    const nodes: LocalMathNode[] = dataset.nodes
      .filter(node => records.has(node.id))
      .map(node => {
        const record = records.get(node.id)!;
        return {
          ...node,
          graphDirection: record.direction,
          graphDepth: record.depth,
        };
      });
    const nodeIds = new Set(nodes.map(node => node.id));

    return {
      centerId,
      nodes,
      edges: dataset.edges.filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target)),
    };
  }

  private traverse(
    edges: MathKnowledgeEdge[],
    centerId: string,
    maximumDepth: number,
    direction: Exclude<MathGraphDirection, 'center'>,
    records: Map<string, TraversalRecord>,
  ): void {
    const queue: Array<{ id: string; depth: number }> = [{ id: centerId, depth: 0 }];
    const visited = new Map<string, number>([[centerId, 0]]);

    while (queue.length > 0) {
      const current = queue.shift()!;
      if (current.depth >= maximumDepth) {
        continue;
      }

      const neighbors = edges
        .filter(edge => direction === 'dependency' ? edge.target === current.id : edge.source === current.id)
        .map(edge => direction === 'dependency' ? edge.source : edge.target);

      for (const neighborId of neighbors) {
        const nextDepth = current.depth + 1;
        const previousDepth = visited.get(neighborId);
        if (previousDepth !== undefined && previousDepth <= nextDepth) {
          continue;
        }

        visited.set(neighborId, nextDepth);
        queue.push({ id: neighborId, depth: nextDepth });
        const existing = records.get(neighborId);
        if (!existing || nextDepth < existing.depth) {
          records.set(neighborId, { direction, depth: nextDepth });
        }
      }
    }
  }
}

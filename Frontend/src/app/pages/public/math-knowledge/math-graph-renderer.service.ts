import { Injectable } from '@angular/core';
import cytoscape, { Core, ElementDefinition, Position } from 'cytoscape';

import { LocalMathGraph, LocalMathNode } from './math-knowledge.models';

@Injectable()
export class MathGraphRendererService {
  private graph?: Core;

  mount(
    container: HTMLElement,
    localGraph: LocalMathGraph,
    onNodeSelected: (nodeId: string) => void,
  ): void {
    this.destroy();
    const elements: ElementDefinition[] = [
      ...localGraph.nodes.map(node => ({
        data: {
          id: node.id,
          label: node.title,
          category: node.category,
          depth: node.graphDepth,
        },
        classes: `${node.graphDirection} category-${node.category}`,
        position: this.positionNode(node, localGraph.nodes),
      })),
      ...localGraph.edges.map(edge => ({
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          relation: edge.relation,
        },
      })),
    ];

    const tokens = getComputedStyle(container);
    const text = tokens.getPropertyValue('--theme-text').trim() || '#e8f0ea';
    const muted = tokens.getPropertyValue('--theme-muted').trim() || '#9fb2a5';
    const accent = tokens.getPropertyValue('--theme-primary').trim() || '#7ee2a8';
    const surface = tokens.getPropertyValue('--theme-surface').trim() || '#14251d';
    const border = tokens.getPropertyValue('--theme-border').trim() || '#426454';

    const stylesheet: cytoscape.StylesheetJson = [
      {
        selector: 'node',
        style: {
          'width': 94,
          'height': 94,
          'background-color': surface,
          'border-width': 2,
          'border-color': border,
          'label': 'data(label)',
          'color': text,
          'font-size': 12,
          'font-weight': 700,
          'text-wrap': 'wrap',
          'text-max-width': '80px',
          'text-valign': 'center',
          'text-halign': 'center',
          'overlay-opacity': 0,
        },
      },
      {
        selector: 'node.dependency',
        style: {
          'border-color': muted,
          'background-color': surface,
        },
      },
      {
        selector: 'node.application',
        style: {
          'border-color': accent,
          'border-style': 'dashed',
        },
      },
      {
        selector: 'node.center',
        style: {
          'width': 122,
          'height': 122,
          'border-width': 5,
          'border-color': accent,
          'background-color': accent,
          'color': surface,
          'font-size': 14,
          'text-max-width': '98px',
          'z-index': 20,
        },
      },
      {
        selector: 'node.hovered',
        style: {
          'border-width': 5,
          'border-color': accent,
        },
      },
      {
        selector: 'edge',
        style: {
          'width': 2,
          'line-color': border,
          'target-arrow-color': border,
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'arrow-scale': 0.9,
          'opacity': 0.86,
        },
      },
      {
        selector: 'edge:selected',
        style: {
          'width': 4,
          'line-color': accent,
          'target-arrow-color': accent,
        },
      },
    ];

    this.graph = cytoscape({
      container,
      elements,
      style: stylesheet,
      layout: { name: 'preset', fit: true, padding: 72 },
      minZoom: 0.28,
      maxZoom: 2.4,
      boxSelectionEnabled: false,
      autoungrabify: true,
    });

    this.graph.on('tap', 'node', event => onNodeSelected(event.target.id()));
    this.graph.on('mouseover', 'node', event => event.target.addClass('hovered'));
    this.graph.on('mouseout', 'node', event => event.target.removeClass('hovered'));
  }

  fit(): void {
    this.graph?.resize();
    this.graph?.fit(undefined, 72);
  }

  destroy(): void {
    this.graph?.destroy();
    this.graph = undefined;
  }

  private positionNode(node: LocalMathNode, allNodes: LocalMathNode[]): Position {
    if (node.graphDirection === 'center') {
      return { x: 0, y: 0 };
    }

    const peers = allNodes.filter(candidate =>
      candidate.graphDirection === node.graphDirection && candidate.graphDepth === node.graphDepth
    );
    const peerIndex = peers.findIndex(candidate => candidate.id === node.id);
    const radius = 170 + (node.graphDepth - 1) * 145;
    const halfArc = Math.min(Math.PI * 0.36, Math.max(Math.PI * 0.12, peers.length * 0.15));
    const offset = peers.length === 1
      ? 0
      : -halfArc + (peerIndex / (peers.length - 1)) * halfArc * 2;
    const baseAngle = node.graphDirection === 'dependency' ? Math.PI : 0;
    const angle = baseAngle + offset;

    return {
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
    };
  }
}

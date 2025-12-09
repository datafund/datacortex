/**
 * Datacortex - D3.js Graph Visualization
 */

class GraphView {
    constructor(selector, app) {
        this.app = app;
        this.container = d3.select(selector);
        this.svg = this.container;
        this.simulation = null;

        this.width = 0;
        this.height = 0;

        this.colors = {
            types: {
                zettel: '#10b981',
                page: '#3b82f6',
                journal: '#f59e0b',
                literature: '#8b5cf6',
                clipping: '#f472b6',
                stub: '#6b7280',
                unknown: '#64748b'
            },
            spaces: {
                personal: '#ec4899',
                datafund: '#06b6d4',
                datacore: '#84cc16'
            }
        };

        this.setupSVG();
        this.setupZoom();
        this.setupTooltip();

        // Handle resize
        window.addEventListener('resize', () => this.resize());
    }

    setupSVG() {
        this.resize();

        // Create main group for zoom/pan
        this.mainGroup = this.svg.append('g').attr('class', 'main');

        // Create groups for links and nodes
        this.linksGroup = this.mainGroup.append('g').attr('class', 'links');
        this.nodesGroup = this.mainGroup.append('g').attr('class', 'nodes');
    }

    resize() {
        const container = document.getElementById('graph-container');
        this.width = container.clientWidth;
        this.height = container.clientHeight;

        this.svg
            .attr('width', this.width)
            .attr('height', this.height);

        if (this.simulation) {
            this.simulation.force('center', d3.forceCenter(this.width / 2, this.height / 2));
            this.simulation.alpha(0.3).restart();
        }
    }

    setupZoom() {
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                this.mainGroup.attr('transform', event.transform);
            });

        this.svg.call(zoom);

        // Double-click to reset
        this.svg.on('dblclick.zoom', () => {
            this.svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
        });
    }

    setupTooltip() {
        this.tooltip = d3.select('#tooltip');
    }

    render(data) {
        const { nodes, links } = data;

        // Clear previous
        this.linksGroup.selectAll('*').remove();
        this.nodesGroup.selectAll('*').remove();

        if (nodes.length === 0) {
            return;
        }

        // Create simulation
        this.simulation = d3.forceSimulation(nodes)
            .force('link', d3.forceLink(links)
                .id(d => d.id)
                .distance(80))
            .force('charge', d3.forceManyBody()
                .strength(-200))
            .force('center', d3.forceCenter(this.width / 2, this.height / 2))
            .force('collision', d3.forceCollide()
                .radius(d => this.nodeRadius(d) + 5));

        // Render links
        const link = this.linksGroup.selectAll('line')
            .data(links)
            .join('line')
            .attr('class', d => `link ${d.resolved ? '' : 'unresolved'}`)
            .attr('stroke-width', 1);

        // Render nodes
        const node = this.nodesGroup.selectAll('g')
            .data(nodes)
            .join('g')
            .attr('class', 'node')
            .call(this.drag(this.simulation));

        // Node circles
        node.append('circle')
            .attr('r', d => this.nodeRadius(d))
            .attr('fill', d => this.nodeColor(d))
            .attr('stroke', d => this.spaceColor(d.space))
            .attr('stroke-width', 2);

        // Node labels (for high-degree nodes)
        node.filter(d => d.degree >= 3)
            .append('text')
            .text(d => this.truncate(d.title, 20))
            .attr('dx', d => this.nodeRadius(d) + 4)
            .attr('dy', 4)
            .attr('font-size', '10px')
            .attr('fill', '#f1f5f9');

        // Event handlers
        node
            .on('mouseover', (event, d) => this.showTooltip(event, d))
            .on('mouseout', () => this.hideTooltip())
            .on('click', (event, d) => {
                event.stopPropagation();
                this.app.selectNode(d);
            });

        // Background click to deselect
        this.svg.on('click', () => {
            document.getElementById('details-panel').classList.add('hidden');
        });

        // Simulation tick
        this.simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });
    }

    nodeRadius(node) {
        // Scale by degree with sqrt for better visual balance
        const base = 5;
        const scale = 2;
        return base + Math.sqrt(node.degree || 0) * scale;
    }

    nodeColor(node) {
        return this.colors.types[node.type] || this.colors.types.unknown;
    }

    spaceColor(space) {
        return this.colors.spaces[space] || '#888';
    }

    truncate(str, maxLen) {
        if (!str) return '';
        return str.length > maxLen ? str.slice(0, maxLen) + '...' : str;
    }

    showTooltip(event, node) {
        this.tooltip
            .classed('hidden', false)
            .style('left', `${event.pageX + 10}px`)
            .style('top', `${event.pageY + 10}px`)
            .html(`
                <div class="tooltip-title">${node.title}</div>
                <div class="tooltip-row">
                    <span>Type:</span>
                    <span class="type-${node.type}">${node.type}</span>
                </div>
                <div class="tooltip-row">
                    <span>Space:</span>
                    <span class="space-${node.space}">${node.space}</span>
                </div>
                <div class="tooltip-row">
                    <span>Degree:</span>
                    <span>${node.degree} (in: ${node.in_degree}, out: ${node.out_degree})</span>
                </div>
                ${node.centrality ? `
                <div class="tooltip-row">
                    <span>Centrality:</span>
                    <span>${(node.centrality * 100).toFixed(1)}%</span>
                </div>
                ` : ''}
            `);
    }

    hideTooltip() {
        this.tooltip.classed('hidden', true);
    }

    drag(simulation) {
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }

        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }

        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }

        return d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended);
    }

    highlightNode(nodeId) {
        // Highlight a specific node (for search results)
        this.nodesGroup.selectAll('circle')
            .attr('opacity', d => d.id === nodeId ? 1 : 0.3);

        this.linksGroup.selectAll('line')
            .attr('opacity', d =>
                d.source.id === nodeId || d.target.id === nodeId ? 1 : 0.1);
    }

    clearHighlight() {
        this.nodesGroup.selectAll('circle').attr('opacity', 1);
        this.linksGroup.selectAll('line').attr('opacity', 0.5);
    }
}

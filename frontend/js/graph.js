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

        this.colorByCluster = false;

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

        // Color scale for clusters using d3.schemeCategory10
        this.clusterColorScale = d3.scaleOrdinal(d3.schemeCategory10);

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
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 8])
            .on('zoom', (event) => {
                this.mainGroup.attr('transform', event.transform);
                this.currentTransform = event.transform;
            });

        this.svg.call(this.zoom);
        this.currentTransform = d3.zoomIdentity;

        // Double-click to reset
        this.svg.on('dblclick.zoom', () => {
            this.resetZoom();
        });
    }

    // Graph view control methods
    zoomIn() {
        this.svg.transition().duration(300).call(this.zoom.scaleBy, 1.5);
    }

    zoomOut() {
        this.svg.transition().duration(300).call(this.zoom.scaleBy, 0.67);
    }

    resetZoom() {
        this.svg.transition().duration(500).call(this.zoom.transform, d3.zoomIdentity);
    }

    fitToScreen() {
        if (!this.simulation || !this.simulation.nodes()) return;

        const nodes = this.simulation.nodes();
        if (nodes.length === 0) return;

        // Calculate bounds
        let minX = Infinity, maxX = -Infinity;
        let minY = Infinity, maxY = -Infinity;

        nodes.forEach(n => {
            minX = Math.min(minX, n.x);
            maxX = Math.max(maxX, n.x);
            minY = Math.min(minY, n.y);
            maxY = Math.max(maxY, n.y);
        });

        const padding = 50;
        const graphWidth = maxX - minX + padding * 2;
        const graphHeight = maxY - minY + padding * 2;

        const scale = Math.min(
            this.width / graphWidth,
            this.height / graphHeight,
            2  // Max scale
        ) * 0.9;

        const centerX = (minX + maxX) / 2;
        const centerY = (minY + maxY) / 2;

        const transform = d3.zoomIdentity
            .translate(this.width / 2, this.height / 2)
            .scale(scale)
            .translate(-centerX, -centerY);

        this.svg.transition().duration(500).call(this.zoom.transform, transform);
    }

    togglePhysics() {
        if (!this.simulation) return;

        if (this.simulation.alpha() < 0.05) {
            // Restart simulation
            this.simulation.alpha(0.3).restart();
            return true;  // Physics enabled
        } else {
            // Stop simulation
            this.simulation.stop();
            return false;  // Physics disabled
        }
    }

    setLinkDistance(distance) {
        if (!this.simulation) return;
        this.simulation.force('link').distance(distance);
        this.simulation.alpha(0.3).restart();
    }

    setChargeStrength(strength) {
        if (!this.simulation) return;
        this.simulation.force('charge').strength(strength);
        this.simulation.alpha(0.3).restart();
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

        // Find top 10 hubs by degree
        const sortedByDegree = [...nodes].sort((a, b) => b.degree - a.degree);
        this.hubs = new Set(sortedByDegree.slice(0, 10).map(n => n.id));

        // Build adjacency for hover highlighting
        this.adjacency = new Map();
        links.forEach(l => {
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;
            if (!this.adjacency.has(sourceId)) this.adjacency.set(sourceId, new Set());
            if (!this.adjacency.has(targetId)) this.adjacency.set(targetId, new Set());
            this.adjacency.get(sourceId).add(targetId);
            this.adjacency.get(targetId).add(sourceId);
        });

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

        // Store references for hover highlighting
        this.linkElements = link;

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
            .attr('stroke', d => this.hubs.has(d.id) ? '#ffd700' : this.spaceColor(d.space))
            .attr('stroke-width', d => this.hubs.has(d.id) ? 3 : 2)
            .classed('hub-node', d => this.hubs.has(d.id));

        // Node labels (for high-degree nodes)
        node.filter(d => d.degree >= 3)
            .append('text')
            .text(d => this.truncate(d.title, 20))
            .attr('dx', d => this.nodeRadius(d) + 4)
            .attr('dy', 4)
            .attr('font-size', '10px')
            .attr('fill', '#f1f5f9');

        // Store references for hover highlighting
        this.nodeElements = node;

        // Event handlers
        node
            .on('mouseover', (event, d) => {
                this.showTooltip(event, d);
                this.highlightConnected(d);
            })
            .on('mouseout', () => {
                this.hideTooltip();
                this.clearHoverHighlight();
            })
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
        if (this.colorByCluster && node.cluster_id !== undefined) {
            return this.clusterColorScale(node.cluster_id);
        }
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
                ${node.cluster_id !== undefined ? `
                <div class="tooltip-row">
                    <span>Cluster:</span>
                    <span>${node.cluster_id}</span>
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

    highlightConnected(node) {
        // Get neighbors from adjacency map
        const neighbors = this.adjacency.get(node.id) || new Set();
        neighbors.add(node.id); // Include the hovered node itself

        // Dim non-neighbor nodes
        this.nodeElements.style('opacity', n => neighbors.has(n.id) ? 1 : 0.15);

        // Dim non-connected links
        this.linkElements.style('opacity', l => {
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;
            return (sourceId === node.id || targetId === node.id) ? 1 : 0.1;
        });
    }

    clearHoverHighlight() {
        // Restore full opacity
        this.nodeElements.style('opacity', 1);
        this.linkElements.style('opacity', 0.6);
    }

    setColorByCluster(enabled) {
        this.colorByCluster = enabled;
        // Update existing node colors without full re-render
        if (this.nodesGroup) {
            this.nodesGroup.selectAll('circle')
                .attr('fill', d => this.nodeColor(d));
        }
    }

    highlightPath(pathIds) {
        const pathSet = new Set(pathIds);

        // Highlight path nodes
        this.nodesGroup.selectAll('circle')
            .style('opacity', d => pathSet.has(d.id) ? 1 : 0.15)
            .attr('stroke', d => pathSet.has(d.id) ? '#00ff00' : d.space ? this.spaceColor(d.space) : 'none')
            .attr('stroke-width', d => pathSet.has(d.id) ? 3 : 2);

        // Highlight path edges
        this.linksGroup.selectAll('line').style('opacity', l => {
            const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
            const targetId = typeof l.target === 'object' ? l.target.id : l.target;
            const sourceIdx = pathIds.indexOf(sourceId);
            const targetIdx = pathIds.indexOf(targetId);
            // Check if consecutive in path
            return (Math.abs(sourceIdx - targetIdx) === 1) ? 1 : 0.1;
        });
    }
}

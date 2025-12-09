/**
 * Datacortex - Main Application
 */

const API_BASE = '/api';

class Datacortex {
    constructor() {
        this.graph = null;
        this.graphView = null;
        this.selectedNode = null;
        this.filters = {
            spaces: new Set(),
            types: new Set(),
            minDegree: 0,
            searchQuery: ''
        };

        this.init();
    }

    async init() {
        // Initialize graph visualization
        this.graphView = new GraphView('#graph', this);

        // Load initial data
        await this.loadGraph();
        await this.loadPulses();

        // Setup controls
        setupControls(this);

        console.log('Datacortex initialized');
    }

    async loadGraph(params = {}) {
        try {
            const queryParams = new URLSearchParams();

            if (this.filters.spaces.size > 0) {
                queryParams.set('spaces', Array.from(this.filters.spaces).join(','));
            }
            if (this.filters.types.size > 0) {
                queryParams.set('types', Array.from(this.filters.types).join(','));
            }
            if (this.filters.minDegree > 0) {
                queryParams.set('min_degree', this.filters.minDegree);
            }

            const url = `${API_BASE}/graph?${queryParams}`;
            const response = await fetch(url);
            this.graph = await response.json();

            // Apply search filter client-side
            let nodes = this.graph.nodes;
            let links = this.graph.links;

            if (this.filters.searchQuery) {
                const query = this.filters.searchQuery.toLowerCase();
                nodes = nodes.filter(n =>
                    n.title.toLowerCase().includes(query) ||
                    (n.tags && n.tags.some(t => t.toLowerCase().includes(query)))
                );
                const nodeIds = new Set(nodes.map(n => n.id));
                links = links.filter(l => nodeIds.has(l.source) || nodeIds.has(l.source.id));
            }

            // Update visualization
            this.graphView.render({ nodes, links });

            // Update stats
            this.updateStats();

        } catch (error) {
            console.error('Failed to load graph:', error);
        }
    }

    async loadPulses() {
        try {
            const response = await fetch(`${API_BASE}/pulse`);
            const data = await response.json();

            const pulseList = document.getElementById('pulse-list');
            if (data.pulses.length === 0) {
                pulseList.innerHTML = '<p class="text-secondary">No pulses yet</p>';
                return;
            }

            pulseList.innerHTML = data.pulses.slice(-10).reverse().map(pulse => `
                <div class="pulse-item" data-pulse-id="${pulse.id}">
                    <div class="pulse-id">${pulse.id}</div>
                    <div class="pulse-meta">${pulse.node_count} nodes, ${pulse.edge_count} edges</div>
                </div>
            `).join('');

            // Add click handlers
            pulseList.querySelectorAll('.pulse-item').forEach(item => {
                item.addEventListener('click', () => this.loadPulse(item.dataset.pulseId));
            });

        } catch (error) {
            console.error('Failed to load pulses:', error);
        }
    }

    async loadPulse(pulseId) {
        try {
            const response = await fetch(`${API_BASE}/pulse/${pulseId}`);
            const data = await response.json();

            // Render pulse graph
            this.graphView.render({ nodes: data.nodes, links: data.links });

            // Show pulse info
            alert(`Viewing pulse: ${pulseId}\nNodes: ${data.nodes.length}\nEdges: ${data.links.length}`);

        } catch (error) {
            console.error('Failed to load pulse:', error);
        }
    }

    async generatePulse() {
        try {
            const response = await fetch(`${API_BASE}/pulse/generate`, { method: 'POST' });
            const data = await response.json();

            alert(`Pulse generated: ${data.id}`);
            await this.loadPulses();

        } catch (error) {
            console.error('Failed to generate pulse:', error);
        }
    }

    updateStats() {
        const stats = this.graph.stats;
        const content = document.getElementById('stats-content');

        content.innerHTML = `
            <div class="stat-row">
                <span class="stat-label">Nodes</span>
                <span class="stat-value">${stats.node_count.toLocaleString()}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Edges</span>
                <span class="stat-value">${stats.edge_count.toLocaleString()}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Avg Degree</span>
                <span class="stat-value">${stats.avg_degree.toFixed(1)}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Clusters</span>
                <span class="stat-value">${stats.cluster_count || '-'}</span>
            </div>
            <div class="stat-row">
                <span class="stat-label">Orphans</span>
                <span class="stat-value">${stats.orphan_count}</span>
            </div>
        `;

        // Build filter checkboxes from data
        this.buildSpaceFilters(stats.nodes_by_space);
        this.buildTypeFilters(stats.nodes_by_type);
    }

    buildSpaceFilters(spaceStats) {
        const container = document.getElementById('space-filters');
        const colors = {
            personal: 'var(--space-personal)',
            datafund: 'var(--space-datafund)',
            datacore: 'var(--space-datacore)'
        };

        container.innerHTML = Object.entries(spaceStats).map(([space, count]) => `
            <label class="filter-checkbox">
                <input type="checkbox" data-space="${space}" checked>
                <span class="color-dot" style="background: ${colors[space] || '#888'}"></span>
                ${space} (${count})
            </label>
        `).join('');

        // Add event listeners
        container.querySelectorAll('input').forEach(input => {
            input.addEventListener('change', () => {
                if (input.checked) {
                    this.filters.spaces.delete(input.dataset.space);
                } else {
                    this.filters.spaces.add(input.dataset.space);
                }
                // Note: spaces filter is inverted (checked = include all)
                this.loadGraph();
            });
        });
    }

    buildTypeFilters(typeStats) {
        const container = document.getElementById('type-filters');
        const colors = {
            zettel: 'var(--node-zettel)',
            page: 'var(--node-page)',
            journal: 'var(--node-journal)',
            literature: 'var(--node-literature)',
            stub: 'var(--node-stub)'
        };

        container.innerHTML = Object.entries(typeStats).map(([type, count]) => `
            <label class="filter-checkbox">
                <input type="checkbox" data-type="${type}" checked>
                <span class="color-dot" style="background: ${colors[type] || '#888'}"></span>
                ${type} (${count})
            </label>
        `).join('');
    }

    selectNode(node) {
        this.selectedNode = node;
        showNodeDetails(node, this);
    }

    openNode(node) {
        // Open file in system - this would need backend support
        // For now, just log the path
        console.log('Opening:', node.path);
        alert(`File path:\n${node.path}\n\nCopy this path to open in your editor.`);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new Datacortex();
});

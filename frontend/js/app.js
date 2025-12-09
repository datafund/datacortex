/**
 * Datacortex - Main Application
 */

const API_BASE = '/api';

class Datacortex {
    constructor() {
        this.graph = null;
        this.graphView = null;
        this.selectedNode = null;
        this.pulses = [];
        this.filters = {
            spaces: new Set(),
            types: new Set(),
            minDegree: 1,
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
        await this.loadTags();

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
                // Handle both string IDs (from API) and object refs (after D3 render)
                links = links.filter(l => {
                    const sourceId = typeof l.source === 'object' ? l.source.id : l.source;
                    const targetId = typeof l.target === 'object' ? l.target.id : l.target;
                    return nodeIds.has(sourceId) && nodeIds.has(targetId);
                });
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

            this.pulses = data.pulses;
            this.updateTimelineSlider();

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

    updateTimelineSlider() {
        const slider = document.getElementById('timeline-slider');
        const label = document.getElementById('timeline-label');

        if (this.pulses.length === 0) {
            slider.disabled = true;
            label.textContent = 'No pulses';
            return;
        }

        slider.disabled = false;
        slider.max = this.pulses.length - 1;
        slider.value = this.pulses.length - 1;  // Latest
        label.textContent = this.pulses[slider.value].id;
    }

    async loadPulseByIndex(index) {
        const pulse = this.pulses[index];
        if (!pulse) return;

        document.getElementById('timeline-label').textContent = pulse.id;
        await this.loadPulse(pulse.id);
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

        // Add event listeners for type filters
        container.querySelectorAll('input').forEach(input => {
            input.addEventListener('change', () => {
                if (input.checked) {
                    this.filters.types.delete(input.dataset.type);
                } else {
                    this.filters.types.add(input.dataset.type);
                }
                // Note: types filter is inverted (checked = include, unchecked = exclude)
                this.loadGraph();
            });
        });
    }

    async loadOrphans() {
        try {
            const response = await fetch(`${API_BASE}/graph/orphans`);
            const data = await response.json();

            document.getElementById('orphan-count').textContent = `(${data.count})`;

            const list = document.getElementById('orphan-list');
            if (data.count === 0) {
                list.innerHTML = '<p class="text-secondary">No orphans found!</p>';
            } else {
                list.innerHTML = data.orphans.map(n => `
                    <div class="orphan-item" data-node-id="${n.id}">
                        <span class="orphan-title">${n.title}</span>
                        <span class="orphan-space">${n.space}</span>
                    </div>
                `).join('');

                // Add click handlers to select nodes
                list.querySelectorAll('.orphan-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const node = data.orphans.find(n => n.id === item.dataset.nodeId);
                        if (node) this.selectNode(node);
                    });
                });
            }
        } catch (error) {
            console.error('Failed to load orphans:', error);
        }
    }

    selectNode(node) {
        this.selectedNode = node;
        showNodeDetails(node, this);
    }

    async openNode(node) {
        // Open file in system editor via API
        try {
            const response = await fetch(`${API_BASE}/nodes/${encodeURIComponent(node.id)}/open`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('File opened:', data.path);

            // Show brief success notification
            const notification = document.createElement('div');
            notification.textContent = 'Opening file...';
            notification.style.cssText = 'position: fixed; top: 20px; right: 20px; background: var(--bg-secondary); padding: 12px 20px; border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,0.2); z-index: 1000;';
            document.body.appendChild(notification);
            setTimeout(() => notification.remove(), 2000);

        } catch (error) {
            console.error('Failed to open file:', error);
            alert(`Failed to open file:\n${error.message}\n\nPath: ${node.path}`);
        }
    }

    async findPath(sourceId, targetId) {
        try {
            const response = await fetch(`${API_BASE}/graph/path/${sourceId}/${targetId}`);
            const data = await response.json();

            const result = document.getElementById('path-result');
            if (!data.found) {
                result.textContent = 'No path found';
                return;
            }

            result.textContent = `Path length: ${data.length}`;
            this.graphView.highlightPath(data.path);
        } catch (error) {
            console.error('Failed to find path:', error);
        }
    }

    async loadTags() {
        try {
            const response = await fetch(`${API_BASE}/graph/tags`);
            const data = await response.json();

            const cloud = document.getElementById('tag-cloud');
            const maxCount = Math.max(...data.tags.map(t => t.count));

            cloud.innerHTML = data.tags.map(t => {
                // Scale font size based on frequency
                const size = 0.7 + (t.count / maxCount) * 0.8;
                return `<span class="tag-item" data-tag="${t.tag}" style="font-size: ${size}rem">${t.tag} (${t.count})</span>`;
            }).join(' ');

            // Add click handlers
            cloud.querySelectorAll('.tag-item').forEach(item => {
                item.addEventListener('click', () => {
                    this.filterByTag(item.dataset.tag);
                });
            });
        } catch (error) {
            console.error('Failed to load tags:', error);
        }
    }

    filterByTag(tag) {
        this.filters.searchQuery = tag;
        document.getElementById('search').value = tag;
        this.loadGraph();
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new Datacortex();
});

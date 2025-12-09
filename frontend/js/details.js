/**
 * Datacortex - Node Details Panel
 */

async function showNodeDetails(node, app) {
    const panel = document.getElementById('details-panel');
    const content = document.getElementById('details-content');

    panel.classList.remove('hidden');

    // Show loading state
    content.innerHTML = '<p>Loading...</p>';

    try {
        // Fetch full node details from API
        const response = await fetch(`/api/nodes/${encodeURIComponent(node.id)}`);
        const data = await response.json();

        const nodeData = data.node;

        content.innerHTML = `
            <h2>${nodeData.title}</h2>

            <div class="detail-section">
                <div class="detail-label">Type</div>
                <div class="detail-value type-${nodeData.type}">${nodeData.type}</div>
            </div>

            <div class="detail-section">
                <div class="detail-label">Space</div>
                <div class="detail-value space-${nodeData.space}">${nodeData.space}</div>
            </div>

            <div class="detail-section">
                <div class="detail-label">Connections</div>
                <div class="detail-value">
                    ${nodeData.degree} total (${nodeData.in_degree} in, ${nodeData.out_degree} out)
                </div>
            </div>

            ${nodeData.centrality ? `
            <div class="detail-section">
                <div class="detail-label">Centrality</div>
                <div class="detail-value">${(nodeData.centrality * 100).toFixed(1)}%</div>
            </div>
            ` : ''}

            ${nodeData.cluster_id !== null ? `
            <div class="detail-section">
                <div class="detail-label">Cluster</div>
                <div class="detail-value">#${nodeData.cluster_id}</div>
            </div>
            ` : ''}

            ${nodeData.maturity ? `
            <div class="detail-section">
                <div class="detail-label">Maturity</div>
                <div class="detail-value">${nodeData.maturity}</div>
            </div>
            ` : ''}

            ${nodeData.word_count ? `
            <div class="detail-section">
                <div class="detail-label">Word Count</div>
                <div class="detail-value">${nodeData.word_count.toLocaleString()}</div>
            </div>
            ` : ''}

            ${nodeData.tags && nodeData.tags.length > 0 ? `
            <div class="detail-section">
                <div class="detail-label">Tags</div>
                <div class="detail-value">
                    ${nodeData.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
                </div>
            </div>
            ` : ''}

            ${data.backlinks && data.backlinks.length > 0 ? `
            <div class="detail-section">
                <div class="detail-label">Backlinks (${data.backlink_count})</div>
                <ul class="link-list">
                    ${data.backlinks.slice(0, 10).map(link => `
                        <li data-node-id="${link.source_id}">${link.source_title}</li>
                    `).join('')}
                    ${data.backlink_count > 10 ? `<li>... and ${data.backlink_count - 10} more</li>` : ''}
                </ul>
            </div>
            ` : ''}

            ${data.outlinks && data.outlinks.length > 0 ? `
            <div class="detail-section">
                <div class="detail-label">Links to (${data.outlink_count})</div>
                <ul class="link-list">
                    ${data.outlinks.slice(0, 10).map(link => `
                        <li data-node-id="${link.target_id}" class="${link.resolved ? '' : 'unresolved'}">
                            ${link.target_title}${link.resolved ? '' : ' (stub)'}
                        </li>
                    `).join('')}
                    ${data.outlink_count > 10 ? `<li>... and ${data.outlink_count - 10} more</li>` : ''}
                </ul>
            </div>
            ` : ''}

            <div class="detail-section">
                <div class="detail-label">Path</div>
                <div class="detail-value" style="font-size: 0.75rem; word-break: break-all;">
                    ${nodeData.path}
                </div>
            </div>

            <button class="open-btn" id="open-node-btn">Open in Editor</button>
        `;

        // Add click handlers for linked nodes
        content.querySelectorAll('.link-list li[data-node-id]').forEach(li => {
            li.addEventListener('click', async () => {
                const linkedNodeId = li.dataset.nodeId;
                // Find the node in the current graph
                const linkedNode = app.graph.nodes.find(n => n.id === linkedNodeId);
                if (linkedNode) {
                    app.selectNode(linkedNode);
                    app.graphView.highlightNode(linkedNodeId);
                }
            });
        });

        // Open button handler
        document.getElementById('open-node-btn').addEventListener('click', () => {
            app.openNode(nodeData);
        });

    } catch (error) {
        console.error('Failed to load node details:', error);
        content.innerHTML = `
            <p>Failed to load details</p>
            <p style="color: var(--text-secondary); font-size: 0.875rem;">${error.message}</p>
        `;
    }
}

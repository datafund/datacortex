/**
 * Datacortex - Controls and Filters
 */

function setupControls(app) {
    // Min degree slider
    const minDegreeSlider = document.getElementById('min-degree');
    const minDegreeValue = document.getElementById('min-degree-value');

    minDegreeSlider.addEventListener('input', () => {
        minDegreeValue.textContent = minDegreeSlider.value;
    });

    minDegreeSlider.addEventListener('change', () => {
        app.filters.minDegree = parseInt(minDegreeSlider.value);
        app.loadGraph();
    });

    // Search input
    const searchInput = document.getElementById('search');
    let searchTimeout;

    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            app.filters.searchQuery = searchInput.value;
            app.loadGraph();
        }, 300);
    });

    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', () => {
        app.loadGraph();
    });

    // Generate pulse button
    document.getElementById('pulse-btn').addEventListener('click', () => {
        app.generatePulse();
    });

    // Show orphans button
    document.getElementById('show-orphans-btn').addEventListener('click', () => {
        const list = document.getElementById('orphan-list');
        list.classList.toggle('hidden');
        if (!list.classList.contains('hidden')) {
            app.loadOrphans();
        }
    });

    // Timeline slider
    document.getElementById('timeline-slider').addEventListener('input', (e) => {
        app.loadPulseByIndex(parseInt(e.target.value));
    });

    // Export SVG
    document.getElementById('export-svg').addEventListener('click', () => {
        const svg = document.getElementById('graph');
        const serializer = new XMLSerializer();
        const svgStr = serializer.serializeToString(svg);
        const blob = new Blob([svgStr], {type: 'image/svg+xml'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'datacortex-graph.svg';
        a.click();
        URL.revokeObjectURL(url);
    });

    // Export PNG
    document.getElementById('export-png').addEventListener('click', () => {
        const svg = document.getElementById('graph');
        const serializer = new XMLSerializer();
        const svgStr = serializer.serializeToString(svg);

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();

        img.onload = () => {
            canvas.width = svg.clientWidth * 2;  // 2x for retina
            canvas.height = svg.clientHeight * 2;
            ctx.scale(2, 2);
            ctx.fillStyle = '#0f172a';  // Background color from CSS var(--bg-primary)
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0);

            const a = document.createElement('a');
            a.href = canvas.toDataURL('image/png');
            a.download = 'datacortex-graph.png';
            a.click();
        };

        img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgStr)));
    });

    // Close details panel
    document.getElementById('close-details').addEventListener('click', () => {
        document.getElementById('details-panel').classList.add('hidden');
    });

    // Color by cluster toggle
    document.getElementById('color-by-cluster').addEventListener('change', (e) => {
        app.graphView.setColorByCluster(e.target.checked);
    });

    // Path finder button
    document.getElementById('find-path-btn').addEventListener('click', () => {
        const source = document.getElementById('path-source').value.trim();
        const target = document.getElementById('path-target').value.trim();
        if (source && target) {
            app.findPath(source, target);
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Escape to close details panel
        if (e.key === 'Escape') {
            document.getElementById('details-panel').classList.add('hidden');
        }

        // / to focus search
        if (e.key === '/' && document.activeElement !== searchInput) {
            e.preventDefault();
            searchInput.focus();
        }

        // r to refresh
        if (e.key === 'r' && !e.ctrlKey && !e.metaKey && document.activeElement !== searchInput) {
            app.loadGraph();
        }
    });
}

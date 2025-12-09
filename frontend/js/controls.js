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

    // Close details panel
    document.getElementById('close-details').addEventListener('click', () => {
        document.getElementById('details-panel').classList.add('hidden');
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

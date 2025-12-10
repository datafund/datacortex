"""Tests for insights module."""

import pytest
from datacortex.insights.analyzer import (
    ClusterAnalysis,
    InsightsResult,
    get_cluster_stats,
    get_hub_documents,
    get_tag_frequency,
    get_cluster_connections,
)
from datacortex.insights.formatter import format_insights, format_cluster_summary
from datacortex.core.models import Node, Edge, NodeType


def test_cluster_analysis_dataclass():
    """Test ClusterAnalysis dataclass creation."""
    analysis = ClusterAnalysis(
        cluster_id=1,
        size=10,
        stats={'avg_words': 200, 'total_words': 2000, 'avg_centrality': 0.05, 'density': 0.1},
        hubs=[{'title': 'Test Doc', 'centrality': 0.1, 'word_count': 500, 'tags': ['test'], 'path': '/test'}],
        tag_freq=[('test', 5), ('example', 3)],
        connections=[{'cluster_id': 2, 'link_count': 3}],
        samples=[{'title': 'Test', 'word_count': 500, 'excerpt': 'Test content...'}]
    )

    assert analysis.cluster_id == 1
    assert analysis.size == 10
    assert len(analysis.hubs) == 1
    assert len(analysis.tag_freq) == 2


def test_insights_result_dataclass():
    """Test InsightsResult dataclass creation."""
    result = InsightsResult(
        clusters=[],
        total_docs=100,
        total_clusters=5,
        generated_at='2025-12-10T12:00:00'
    )

    assert result.total_docs == 100
    assert result.total_clusters == 5
    assert len(result.clusters) == 0


def test_get_cluster_stats():
    """Test cluster statistics computation."""
    nodes = [
        Node(id='1', title='Doc 1', path='/1', space='test', word_count=100, centrality=0.1),
        Node(id='2', title='Doc 2', path='/2', space='test', word_count=200, centrality=0.2),
        Node(id='3', title='Doc 3', path='/3', space='test', word_count=300, centrality=0.3),
    ]

    edges = [
        Edge(id='e1', source='1', target='2', resolved=True),
        Edge(id='e2', source='2', target='3', resolved=True),
    ]

    stats = get_cluster_stats(nodes, edges)

    assert stats['total_words'] == 600
    assert stats['avg_words'] == 200
    assert 'avg_centrality' in stats
    assert 'density' in stats


def test_get_hub_documents():
    """Test hub document extraction."""
    nodes = [
        Node(id='1', title='High Hub', path='/1', space='test', centrality=0.9, word_count=500, tags=['important']),
        Node(id='2', title='Medium Hub', path='/2', space='test', centrality=0.5, word_count=300, tags=['medium']),
        Node(id='3', title='Low Hub', path='/3', space='test', centrality=0.1, word_count=100, tags=['low']),
    ]

    hubs = get_hub_documents(nodes, top_n=2)

    assert len(hubs) == 2
    assert hubs[0]['title'] == 'High Hub'
    assert hubs[1]['title'] == 'Medium Hub'
    assert 'centrality' in hubs[0]
    assert 'word_count' in hubs[0]


def test_get_tag_frequency():
    """Test tag frequency counting."""
    nodes = [
        Node(id='1', title='Doc 1', path='/1', space='test', tags=['ai', 'data']),
        Node(id='2', title='Doc 2', path='/2', space='test', tags=['ai', 'ml']),
        Node(id='3', title='Doc 3', path='/3', space='test', tags=['data', 'analytics']),
    ]

    tag_freq = get_tag_frequency(nodes)

    assert len(tag_freq) >= 2
    # 'ai' and 'data' should be most common
    tags_dict = dict(tag_freq)
    assert tags_dict.get('ai') == 2
    assert tags_dict.get('data') == 2


def test_get_cluster_connections():
    """Test cluster connection analysis."""
    clusters = {
        1: [
            Node(id='1', title='Doc 1', path='/1', space='test', cluster_id=1),
            Node(id='2', title='Doc 2', path='/2', space='test', cluster_id=1),
        ],
        2: [
            Node(id='3', title='Doc 3', path='/3', space='test', cluster_id=2),
        ]
    }

    edges = [
        Edge(id='e1', source='1', target='3', resolved=True),
        Edge(id='e2', source='2', target='3', resolved=True),
    ]

    connections = get_cluster_connections(1, clusters, edges)

    assert len(connections) > 0
    assert connections[0]['cluster_id'] == 2
    assert connections[0]['link_count'] == 2


def test_format_insights():
    """Test insights formatting."""
    analysis = ClusterAnalysis(
        cluster_id=1,
        size=10,
        stats={'avg_words': 200, 'total_words': 2000, 'avg_centrality': 0.05, 'density': 0.1},
        hubs=[{'title': 'Test Hub', 'centrality': 0.1, 'word_count': 500, 'tags': ['test'], 'path': '/test'}],
        tag_freq=[('test', 5)],
        connections=[{'cluster_id': 2, 'link_count': 3}],
        samples=[{'title': 'Sample', 'word_count': 500, 'excerpt': 'Test content...'}]
    )

    result = InsightsResult(
        clusters=[analysis],
        total_docs=100,
        total_clusters=5,
        generated_at='2025-12-10T12:00:00'
    )

    formatted = format_insights(result, include_samples=True)

    assert 'CLUSTER_INSIGHTS' in formatted
    assert 'total_docs=100' in formatted
    assert 'CLUSTER id=1 size=10' in formatted
    assert 'Test Hub' in formatted
    assert 'test: 5' in formatted


def test_format_insights_no_samples():
    """Test insights formatting without samples."""
    analysis = ClusterAnalysis(
        cluster_id=1,
        size=5,
        stats={'avg_words': 100, 'total_words': 500, 'avg_centrality': 0.02, 'density': 0.05},
        hubs=[],
        tag_freq=[],
        connections=[],
        samples=[]
    )

    result = InsightsResult(
        clusters=[analysis],
        total_docs=50,
        total_clusters=3,
        generated_at='2025-12-10T12:00:00'
    )

    formatted = format_insights(result, include_samples=False)

    assert 'CLUSTER id=1' in formatted
    assert 'SAMPLES' not in formatted


def test_format_cluster_summary():
    """Test cluster summary formatting."""
    analysis = ClusterAnalysis(
        cluster_id=1,
        size=10,
        stats={},
        hubs=[{'title': 'Main Hub', 'centrality': 0.1, 'word_count': 500, 'tags': [], 'path': '/test'}],
        tag_freq=[('tag1', 5), ('tag2', 3)],
        connections=[],
        samples=[]
    )

    result = InsightsResult(
        clusters=[analysis],
        total_docs=100,
        total_clusters=5,
        generated_at='2025-12-10T12:00:00'
    )

    summary = format_cluster_summary(result)

    assert 'CLUSTER SUMMARY' in summary
    assert 'Total clusters: 5' in summary
    assert 'Total documents: 100' in summary
    assert 'Main Hub' in summary

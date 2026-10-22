"""Regression tests for the literal stop and newest-file publication gate."""
import importlib.util
import json
from pathlib import Path

import pytest

from sys import path as syspath
ROOT = Path(__file__).resolve().parents[1]
syspath.insert(0, str(ROOT/'vendor'))
from gems57.uniqueness import binding_duplicate_decision

spec = importlib.util.spec_from_file_location('publish_crosslayer', ROOT/'scripts/publish_crosslayer.py')
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


def test_dense_lattice_is_binding_not_exempt():
    rows = [dict(file='lattice.tif', forward_overlap=.9989, spearman_full_footprint=.001,
                 halo_coverage=.99)]
    decision = binding_duplicate_decision(rows)
    assert decision['binding_rule'] == 'literal-all-rasters'
    assert decision['duplicate'] is True
    assert decision['worst_forward_overlap_file'] == 'lattice.tif'


def test_publication_hash_bound_and_fails_closed(monkeypatch, tmp_path):
    card = json.loads((ROOT/'evidence/crosslayer_run_card.json').read_text())
    assert card['verdict'] == 'negative' and not card['ok_to_submit']
    assert publisher.publish()['sha256'] == card['raster_sha256']
    homepage = (ROOT/'docs/index.html').read_text()
    assert 'data/protocol_preflight.json' in homepage
    assert '100% forward overlap' in homepage
    status = json.loads((ROOT/'docs/data/status.json').read_text())
    assert status['authoritative_card'] == 'release_audit.json'
    assert not status['current_review_new_tif_generated']
    monkeypatch.setattr(publisher, 'ROOT', tmp_path)
    (tmp_path/'evidence').mkdir()
    (tmp_path/'docs/downloads').mkdir(parents=True)
    (tmp_path/'evidence/crosslayer_run_card.json').write_text(json.dumps(card))
    (tmp_path/'docs/downloads'/card['validator_output']['file']).write_bytes(b'tampered')
    with pytest.raises(ValueError, match='SHA256'):
        publisher.publish()

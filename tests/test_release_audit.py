"""Current publication policy supersedes historical promotion cards."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('audit_release', ROOT / 'scripts/audit_release.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_forward_overlap_is_binding_not_mutual():
    rows = [dict(forward_overlap_mine_in_theirs3px=.73, mutual=.2)]
    assert audit.literal_failures(rows) == rows


def test_threshold_boundaries():
    assert not audit.literal_failures([dict(forward_overlap_mine_in_theirs3px=.70,
                                           spearman_full_footprint=.90)])
    assert audit.literal_failures([dict(forward_overlap_mine_in_theirs3px=.700001)])
    assert audit.literal_failures([dict(forward_overlap_mine_in_theirs3px=0,
                                      spearman_full_footprint=.900001)])


def test_release_evidence_is_strict_json_and_negative():
    def reject(value):
        raise AssertionError(value)
    card = json.loads((ROOT / 'evidence/release_audit.json').read_text(), parse_constant=reject)
    assert card['verdict'] == 'negative'
    assert not card['new_tif_generated'] and card['new_experiments'] == 0
    assert card['holdout']['seed'] == 20 and card['holdout']['withheld_positive_pixels'] == 11321
    assert card['current_repo_best_holdout']['dti'] > card['holdout']['dti']
    paired_ci = card['candidate_vs_h33_control_paired_difference']['ci95']
    assert paired_ci[0] < 0 < paired_ci[1]
    assert len(card['submission_note']) <= 140
    assert len(card['correlation_overlap_vs_registry']['failed_forward_rows']) >= 2
    assert all(c['validator']['all_passed'] for c in card['candidates'])
    # H78-SIGX session: exactly one candidate may be ok_to_submit, and only
    # via its independent gate report (fail closed otherwise).
    oks = [c for c in card['candidates'] if c['ok_to_submit']]
    assert [c['lane'] for c in oks] == ['H78-GSC']
    assert oks[0]['gate_report'] == 'evidence/h78gsc_gate_report.json'


def test_missing_input_fails_closed(tmp_path):
    assert not audit.validate(tmp_path / 'absent.tif')['all_passed']


def test_corrupt_zip_fails_overall_validation(tmp_path):
    import zipfile
    card = json.loads((ROOT / 'evidence/release_audit.json').read_text())
    source = ROOT / 'docs/downloads' / card['candidates'][0]['file']
    copied = tmp_path / source.name
    copied.write_bytes(source.read_bytes())
    with zipfile.ZipFile(copied.with_suffix('.zip'), 'w') as z:
        z.writestr(source.name, b'not the TIFF')
    assert not audit.validate(copied)['all_passed']


def test_builders_finish_with_release_audit():
    for name in ('build_site.py', 'build_site_mpc.py', 'build_session_site.py', 'build_site_cs.py', 'build_site_gsc.py'):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / name)],
                                cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        for page in ('index.html','executive-summary.html','h78mpc.html','h78mpc-executive-summary.html'):
            text = (ROOT / 'docs' / page).read_text()
            assert 'OK TO SUBMIT: YES — exactly one file:' in text
            assert 'gems78-h78gsc-oof-submod40k-20261021T033000Z-zeros.tif' in text
            assert 'h78sigx-fuse-b5-44090dots' in text
            assert 'Download historical TIFF — do not submit' in text
            assert 'data/protocol_preflight.json' in text
            assert '100% forward overlap' in text
            assert 'h78cs-collinear' in text
            assert 'h78spy-inspection' in text


def test_inventory_covers_every_published_tif():
    card = json.loads((ROOT / 'evidence/release_audit.json').read_text())
    files = {p.name for p in (ROOT / 'docs/downloads').glob('*.tif')}
    assert {c['file'] for c in card['candidates']} == files
    status = json.loads((ROOT / 'docs/data/status.json').read_text())
    assert status['candidates'] == card['candidates']
    assert status['review_date'] == '2026-10-22'


def test_wrong_shape_returns_structured_failure(tmp_path):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    path = tmp_path / 'small.tif'
    with rasterio.open(path, 'w', driver='GTiff', height=2, width=2,
                       count=1, dtype='float32', crs='EPSG:32611',
                       transform=from_origin(243350, 4508550, 100, 100)) as ds:
        ds.write(np.zeros((2, 2), dtype='float32'), 1)
    report = audit.validate(path)
    assert not report['all_passed']
    assert report['checks']['shape_3730x3292'] is False
    assert report['footprint_fraction'] is None


def test_zip_entry_name_must_match_tif(tmp_path):
    import zipfile
    source = next((ROOT / 'docs/downloads').glob('*.tif'))
    copied = tmp_path / source.name
    copied.write_bytes(source.read_bytes())
    with zipfile.ZipFile(copied.with_suffix('.zip'), 'w') as z:
        z.writestr('unexpected.bin', copied.read_bytes())
    assert not audit.validate(copied)['all_passed']


def test_corrupt_zip_returns_structured_failure(tmp_path):
    source = next((ROOT / 'docs/downloads').glob('*.tif'))
    copied = tmp_path / source.name
    copied.write_bytes(source.read_bytes())
    copied.with_suffix('.zip').write_bytes(b'broken zip')
    report = audit.validate(copied)
    assert report['all_passed'] is False
    assert 'error' in report

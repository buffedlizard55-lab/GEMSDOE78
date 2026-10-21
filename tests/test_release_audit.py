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
    assert not any(c['ok_to_submit'] for c in card['candidates'])


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
    for name in ('build_site.py', 'build_site_mpc.py'):
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / name)],
                                cwd=ROOT, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        for page in ('index.html','executive-summary.html','h78mpc.html','h78mpc-executive-summary.html'):
            text = (ROOT / 'docs' / page).read_text()
            assert 'OK TO SUBMIT: NO' in text
            assert 'OK TO SUBMIT: YES' not in text

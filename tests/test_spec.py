import math
from pathlib import Path

import numpy as np
import pytest

from simanything.spec import (DH, Joint, Spec, Units, dh_fk, iter_numeric_fields, load_spec, path_covers,
                              uncovered_fields)

ROOT = Path(__file__).resolve().parents[1]


def _rows():
    a = [0, -0.425, -0.3922, 0, 0, 0]
    d = [0.1625, 0, 0, 0.1333, 0.0997, 0.0996]
    al = [math.pi / 2, 0, 0, math.pi / 2, -math.pi / 2, 0]
    return [DH(a=x, alpha=y, d=z, theta_offset=0.2 * i) for i, (x, y, z) in enumerate(zip(a, al, d))]


@pytest.mark.parametrize("conv", ["dh_standard", "dh_modified"])
@pytest.mark.parametrize("slide_at", [None, 2])
def test_dh_chain_matches_textbook_fk(conv, slide_at):
    rows = _rows()
    types = ["slide" if i == slide_at else "hinge" for i in range(6)]
    spec = Spec(name="t", dof=6, units=Units(angle="rad"), convention=conv,
                joints=[Joint(name=f"j{i}", type=t, dh=r) for i, (t, r) in enumerate(zip(types, rows))])
    ch = spec.chain()
    assert all(j.qpos_offset == 0.0 for j in ch.joints)
    rng = np.random.default_rng(1)
    for _ in range(20):
        q = rng.uniform(-2, 2, 6)
        assert np.allclose(ch.fk(q), dh_fk(rows, q, conv, types), atol=1e-12)


def test_units_conversion_mm_deg():
    s = load_spec(ROOT / "examples/toy_6dof_dh.yaml")
    si = s.to_si()
    assert si.joints[1].dh.a == pytest.approx(-0.4)
    assert si.joints[0].dh.alpha == pytest.approx(math.pi / 2)
    assert si.joints[0].limits.upper == pytest.approx(2 * math.pi)
    assert si.reach.value == pytest.approx(0.90)


def test_offset_chain_fk_toy():
    s = load_spec(ROOT / "examples/toy_2link.yaml")
    ch = s.chain()
    T = ch.fk([0.0, 0.0])
    assert np.allclose(T[:3, 3], [0.55, 0, 0.1])
    # rotate shoulder +90 deg about +y: x -> -z
    T = ch.fk([math.pi / 2, 0.0])
    assert np.allclose(T[:3, 3], [0, 0, 0.1 - 0.55], atol=1e-12)


def test_source_coverage():
    s = load_spec(ROOT / "examples/toy_2link.yaml")
    assert uncovered_fields(s) == []
    s2 = s.model_copy(update={"estimates": ["base", "joints[*].origin", "ee"]})
    missing = uncovered_fields(s2)
    assert "total_mass" in missing and "joints[0].limits.lower" in missing
    assert not any(m.startswith("joints[0].origin") for m in missing)
    assert path_covers("joints[*].limits", "joints[3].limits.upper")
    assert not path_covers("joints[1]", "joints[10].dh.a")
    paths = dict(iter_numeric_fields(s))
    assert "joints[1].origin.xyz" in paths


def test_validation_errors():
    with pytest.raises(ValueError):
        Spec(name="x", dof=2, joints=[Joint(name="a", dh=DH())], convention="dh_standard")
    with pytest.raises(ValueError):
        Spec(name="x", dof=1, joints=[Joint(name="a")], convention="offset")
    with pytest.raises(ValueError):
        Spec(name="x", dof=1, joints=[Joint(name="a", dh=DH())], convention="dh_standard", sources={"joints[": "u"})


def test_schema_file_up_to_date():
    import json

    from simanything.spec import json_schema

    on_disk = json.loads((ROOT / "docs/spec.schema.json").read_text())
    assert on_disk == json.loads(json.dumps(json_schema()))

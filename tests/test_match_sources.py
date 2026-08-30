import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from match_sources import nearest_anchor  # noqa: E402


def test_nearest_anchor_prefers_finest_anchored_heading():
    md = "# B\n\n## Big Section\n\n### Fine Sub\n\nhit\n"  # "hit" is line 7
    anchors_b = [{"heading": "Big Section", "anchor": "section-big", "level": 2},
                 {"heading": "Fine Sub", "anchor": "section-fine", "level": 3}]
    assert nearest_anchor(md, 7, anchors_b) == ("Fine Sub", "section-fine")


def test_nearest_anchor_falls_back_to_h2_when_h3_unanchored():
    md = "# B\n\n## Big Section\n\n### Fine Sub\n\nhit\n"
    anchors_b = [{"heading": "Big Section", "anchor": "section-big", "level": 2},
                 {"heading": "Fine Sub", "anchor": None, "level": 3}]
    assert nearest_anchor(md, 7, anchors_b) == ("Big Section", "section-big")


def test_nearest_anchor_none_before_first_heading():
    assert nearest_anchor("# B\n\npreamble hit\n", 3, []) == (None, None)

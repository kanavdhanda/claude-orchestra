from winnow.json_truncate import needs_truncation, truncate_json


def test_list_truncated_to_exactly_n_plus_marker():
    data = list(range(50))
    out = truncate_json(data, keep_items=20)
    assert out[:20] == list(range(20))
    assert len(out) == 21
    assert out[20] == "...30 more omitted"


def test_dict_truncated_to_exactly_n_keys_plus_marker():
    data = {f"k{i}": i for i in range(25)}
    out = truncate_json(data, keep_items=20)
    kept_keys = [k for k in out if not k.startswith("...")]
    assert len(kept_keys) == 20
    assert kept_keys == list(data.keys())[:20]
    assert "...5 more omitted" in out


def test_no_truncation_below_threshold():
    data = list(range(10))
    assert needs_truncation(data, keep_items=20) is False
    assert truncate_json(data, keep_items=20) == data


def test_recurses_into_kept_children():
    data = {"items": list(range(30))}
    out = truncate_json(data, keep_items=20)
    assert len(out["items"]) == 21
    assert out["items"][-1] == "...10 more omitted"


def test_scalars_pass_through():
    assert truncate_json("hello", keep_items=20) == "hello"
    assert truncate_json(42, keep_items=20) == 42
    assert truncate_json(None, keep_items=20) is None

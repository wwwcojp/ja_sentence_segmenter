import pytest

from ja_sentence_segmenter.concatenate import simple_concatenator

RULE_NO = r"^(?P<result>.+)(の)$"


def test_concatenate_matching() -> None:
    texts = [">  私は", ">> あなたが", " > きらいです。", " >でも実は", "*好きなの", "かもしれない"]
    assert list(simple_concatenator.concatenate_matching(iter(texts), latter_matching_rule=r"^(\s*[>]+\s*)(?P<result>.+)$", remove_latter_matched=True)) == [
        ">  私はあなたがきらいです。でも実は",
        "*好きなの",
        "かもしれない",
    ]
    assert list(simple_concatenator.concatenate_matching(iter(texts), latter_matching_rule=r"^(\s*[>]+\s*)(?P<result>.+)$", remove_latter_matched=False)) == [
        ">  私は>> あなたが > きらいです。 >でも実は",
        "*好きなの",
        "かもしれない",
    ]
    assert list(simple_concatenator.concatenate_matching(iter(texts), latter_matching_rule=r"^(\s*[>*]+\s*)(?P<result>.+)$", remove_latter_matched=True)) == [
        ">  私はあなたがきらいです。でも実は好きなの",
        "かもしれない",
    ]
    assert list(simple_concatenator.concatenate_matching(iter(texts))) == [
        ">  私は",
        ">> あなたが",
        " > きらいです。",
        " >でも実は",
        "*好きなの",
        "かもしれない",
    ]

    texts2 = ["私の", "願いは", "世界征服だ", "なによりも", "それを", "求めている"]
    assert list(simple_concatenator.concatenate_matching(iter(texts2), former_matching_rule=r"^(?P<result>.+)(の)$", remove_former_matched=True)) == [
        "私願いは",
        "世界征服だ",
        "なによりも",
        "それを",
        "求めている",
    ]
    assert list(simple_concatenator.concatenate_matching(iter(texts2), former_matching_rule=r"^(?P<result>.+)(の)$", remove_former_matched=False)) == [
        "私の願いは",
        "世界征服だ",
        "なによりも",
        "それを",
        "求めている",
    ]
    assert list(simple_concatenator.concatenate_matching(iter(texts2), former_matching_rule=r"^(?P<result>.+)(の|も|を|は)$", remove_former_matched=False)) == [
        "私の願いは世界征服だ",
        "なによりもそれを求めている",
    ]

    texts3 = ["私はもう死んでいる", "> 私はあなたが", " > きらいです。", " >でも実は", "*好きなの", "かもしれない"]
    assert list(
        simple_concatenator.concatenate_matching(
            iter(texts3),
            former_matching_rule=r"^(\s*[>]+\s*)(?P<result>.+)$",
            latter_matching_rule=r"^(\s*[>]+\s*)(?P<result>.+)$",
            remove_former_matched=False,
            remove_latter_matched=True,
        )
    ) == ["私はもう死んでいる", "> 私はあなたがきらいです。でも実は", "*好きなの", "かもしれない"]
    assert list(
        simple_concatenator.concatenate_matching(
            texts3,
            former_matching_rule=r"^(\s*[>]+\s*)(?P<result>.+)$",
            latter_matching_rule=r"^(\s*[>]+\s*)(?P<result>.+)$",
            remove_former_matched=False,
            remove_latter_matched=True,
        )
    ) == ["私はもう死んでいる", "> 私はあなたがきらいです。でも実は", "*好きなの", "かもしれない"]


def test_concatenate_matching_max_concatenate_length() -> None:
    texts = ["あの"] * 100

    # 上限に達したら打ち切って次の累積を始める
    result = list(simple_concatenator.concatenate_matching(iter(texts), former_matching_rule=RULE_NO, remove_former_matched=False, max_concatenate_length=10))
    assert len(result) == 20
    assert max(len(chunk) for chunk in result) == 10
    # テキストの欠落がない
    assert "".join(result) == "".join(texts)

    # None を渡すと従来どおり無制限
    assert list(
        simple_concatenator.concatenate_matching(iter(texts), former_matching_rule=RULE_NO, remove_former_matched=False, max_concatenate_length=None)
    ) == ["".join(texts)]


def test_concatenate_matching_max_concatenate_length_validation() -> None:
    # concatenate_matching はジェネレータ関数なので、ValueError は呼び出し時点ではなく
    # 最初の next() で送出される。list() で消費して検証する。
    for invalid in (0, -1):
        with pytest.raises(ValueError, match="max_concatenate_length must be positive or None"):
            list(simple_concatenator.concatenate_matching(["あの"], max_concatenate_length=invalid))


def test_concatenate_matching_bounded_run_stays_linear() -> None:
    # 上限を設定した場合の回帰防止。上限チェックが正規表現マッチより後ろに移ると
    # 二次時間が復活し、この入力の所要時間が跳ね上がる。
    # 実時間ではなくチャンク数で検証する（CI の負荷変動に左右されないため）。
    texts = ["あの"] * 30000
    result = list(
        simple_concatenator.concatenate_matching(iter(texts), former_matching_rule=RULE_NO, remove_former_matched=False, max_concatenate_length=10000)
    )
    assert len(result) == 6
    assert "".join(result) == "".join(texts)


def test_concatenate_matching_applies_former_rule_to_oversized_first_line() -> None:
    # 1行目が単独で上限を超えていても former_matching_rule は評価されなければならない。
    # 上限は累積の伸びを止めるものであって、まだ一度も処理されていない行の処理を
    # 拒否するものではない。
    texts = ["あ" * 19999 + "の", "願いは"]

    bounded = list(
        simple_concatenator.concatenate_matching(iter(texts), former_matching_rule=RULE_NO, remove_former_matched=True, max_concatenate_length=10000)
    )
    unbounded = list(
        simple_concatenator.concatenate_matching(iter(texts), former_matching_rule=RULE_NO, remove_former_matched=True, max_concatenate_length=None)
    )

    assert bounded == unbounded
    assert bounded == ["あ" * 19999 + "願いは"]


def test_concatenate_matching_str_input() -> None:
    # str は1行として扱うので結合相手がなく、そのまま1件返る。
    result = list(simple_concatenator.concatenate_matching("私の願いは", former_matching_rule=RULE_NO))
    assert result == ["私の願いは"]
    assert result == list(simple_concatenator.concatenate_matching(["私の願いは"], former_matching_rule=RULE_NO))

    # 改行を含んでいても分割しない。呼び出し側が split_newline 等で先に分割する。
    assert list(simple_concatenator.concatenate_matching("私の\n願いは", former_matching_rule=RULE_NO, remove_former_matched=False)) == ["私の\n願いは"]


def test_concatenate_matching_rejects_unsupported_types() -> None:
    # tuple や set は従来どおりだと黙って空を返していた。静かなデータ消失を
    # 診断可能なエラーに変える。
    for unsupported in (("あの", "願いは"), {"あの"}, 42):
        with pytest.raises(TypeError, match="arg must be a str, a list or an Iterator"):
            list(simple_concatenator.concatenate_matching(unsupported))  # type: ignore[call-overload]


def test_concatenate_matching_bound_boundary_skips_latter_rule() -> None:
    # 上限境界では latter_matching_rule が評価されないため、剥がされるはずの接頭辞が
    # 1行ぶん出力に残る。docstring に明記した挙動を固定し、意図しない変化を検出する。
    quote_rule = r"^(\s*[>]+\s*)(?P<result>.+)$"
    texts = ["> " + "あ" * 8] * 6

    unbounded = list(simple_concatenator.concatenate_matching(iter(texts), latter_matching_rule=quote_rule, remove_latter_matched=True))
    bounded = list(
        simple_concatenator.concatenate_matching(iter(texts), latter_matching_rule=quote_rule, remove_latter_matched=True, max_concatenate_length=20)
    )

    # 上限なしなら先頭行の "> " だけが残る
    assert unbounded == ["> " + "あ" * 48]
    # 上限ありでは、各累積の先頭になった行の "> " も残る
    assert bounded == ["> " + "あ" * 24, "> " + "あ" * 24]
    assert "".join(unbounded).count(">") == 1
    assert "".join(bounded).count(">") == 2

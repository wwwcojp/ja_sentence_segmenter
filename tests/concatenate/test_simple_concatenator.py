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


def test_concatenate_matching_does_not_blow_up_on_large_input() -> None:
    # 上限がないと再帰的な再走査で二次時間になり、この入力で30秒かかる。
    # 実時間ではなくチャンク数で検証する（CI の負荷変動に左右されないため）。
    # 二次時間が復活した場合はテスト自体がタイムアウトして検出される。
    texts = ["あの"] * 300000
    result = list(simple_concatenator.concatenate_matching(iter(texts), former_matching_rule=RULE_NO, remove_former_matched=False))
    assert len(result) == 60
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

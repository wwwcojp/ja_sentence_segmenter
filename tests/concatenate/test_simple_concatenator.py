import pytest

from ja_sentence_segmenter.concatenate import simple_concatenator


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
    assert list(simple_concatenator.concatenate_matching(iter(texts))) == [">  私は", ">> あなたが", " > きらいです。", " >でも実は", "*好きなの", "かもしれない"]

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

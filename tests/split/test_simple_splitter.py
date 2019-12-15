import pytest

from ja_sentence_segmenter.split import simple_splitter


def test_split_newline() -> None:
    assert list(simple_splitter.split_newline("恥の多い生涯を送って来ました。\r\n自分には、人間の生活というものが、見当つかないのです。")) == [
        "恥の多い生涯を送って来ました。",
        "自分には、人間の生活というものが、見当つかないのです。",
    ]
    assert list(simple_splitter.split_newline("恥の多い生涯を送って来ました。\n自分には、人間の生活というものが、見当つかないのです。")) == [
        "恥の多い生涯を送って来ました。",
        "自分には、人間の生活というものが、見当つかないのです。",
    ]
    assert list(simple_splitter.split_newline("恥の多い生涯を送って来ました。\r自分には、人間の生活というものが、見当つかないのです。")) == [
        "恥の多い生涯を送って来ました。",
        "自分には、人間の生活というものが、見当つかないのです。",
    ]
    assert list(simple_splitter.split_newline(["恥の多い生涯を送って来ました。\n自分には、人間の生活というものが、見当つかないのです。"])) == [
        "恥の多い生涯を送って来ました。",
        "自分には、人間の生活というものが、見当つかないのです。",
    ]

    assert list(simple_splitter.split_newline(["恥の多い生涯\n", "を送って来ました。\n自分には、人間の生活というものが、", "見当つかないのです。"])) == [
        "恥の多い生涯",
        "を送って来ました。",
        "自分には、人間の生活というものが、",
        "見当つかないのです。",
    ]

    assert list(simple_splitter.split_newline(iter(["恥の多い生涯\n", "を送って来ました。\n自分には、人間の生活というものが、", "見当つかないのです。"]))) == [
        "恥の多い生涯",
        "を送って来ました。",
        "自分には、人間の生活というものが、",
        "見当つかないのです。",
    ]

    assert list(simple_splitter.split_newline([])) == []
    assert list(simple_splitter.split_newline(None)) == []
    assert list(simple_splitter.split_newline(1)) == []
    with pytest.raises(AttributeError):
        assert list(simple_splitter.split_newline([1, 2, "hoge"]))


def test_split_punctuation() -> None:
    assert list(simple_splitter.split_punctuation("私は「この星は遠い。でもない。」といった?でも、「それはそれ(だがつらい?)として!」とも思う(それは「違う。」かもしれない。)!(ほげ。)。ではまた。")) == [
        "私は「この星は遠い。でもない。」といった?",
        "でも、「それはそれ(だがつらい?)として!」とも思う(それは「違う。」かもしれない。)!",
        "(ほげ。)。",
        "ではまた。",
    ]
    assert list(
        simple_splitter.split_punctuation("私は「この星は遠い。でもない。」といった?でも、「それはそれ(だがつらい?)として!」とも思う(それは「違う。」かもしれない。)!(ほげ。)。ではまた。", split_between_quote=True)
    ) == ["私は「この星は遠い。", "でもない。", "」といった?", "でも、「それはそれ(だがつらい?)として!", "」とも思う(それは「違う。」かもしれない。)!", "(ほげ。)。", "ではまた。"]
    assert list(
        simple_splitter.split_punctuation("私は「この星は遠い。でもない。」といった?でも、「それはそれ(だがつらい?)として!」とも思う(それは「違う。」かもしれない。)!(ほげ。)。ではまた。", split_between_parens=True)
    ) == ["私は「この星は遠い。でもない。」といった?", "でも、「それはそれ(だがつらい?)として!」とも思う(それは「違う。」かもしれない。", ")!", "(ほげ。", ")。", "ではまた。"]
    assert list(
        simple_splitter.split_punctuation(
            "私は「この星は遠い。でもない。」といった?でも、「それはそれ(だがつらい?)として!」とも思う(それは「違う。」かもしれない。)!(ほげ。)。ではまた。", split_between_quote=True, split_between_parens=True
        )
    ) == ["私は「この星は遠い。", "でもない。", "」といった?", "でも、「それはそれ(だがつらい?", ")として!", "」とも思う(それは「違う。", "」かもしれない。", ")!", "(ほげ。", ")。", "ではまた。"]
    assert list(simple_splitter.split_punctuation("私は「この星は遠い。でもない。」といった?でも、「それはそれ(だがつらい?)として!」とも思う(それは「違う。」かもしれない。)!(ほげ。)。ではまた。", "。")) == [
        "私は「この星は遠い。でもない。」といった?でも、「それはそれ(だがつらい?)として!」とも思う(それは「違う。」かもしれない。)!(ほげ。)。",
        "ではまた。",
    ]

    assert list(simple_splitter.split_punctuation(["私は「この星は遠い。でもない。」といった?", "でも、「それはそれ(だがつらい?)として!」とも思う(それは「違う。」かもしれない。)!(ほげ。)。ではまた。"])) == [
        "私は「この星は遠い。でもない。」といった?",
        "でも、「それはそれ(だがつらい?)として!」とも思う(それは「違う。」かもしれない。)!",
        "(ほげ。)。",
        "ではまた。",
    ]

    assert list(simple_splitter.split_punctuation(iter(["私は「この星は遠い。でもない。」といった?", "でも、「それはそれ(だがつらい?)として!」とも思う(それは「違う。」かもしれない。)!(ほげ。)。ではまた。"]))) == [
        "私は「この星は遠い。でもない。」といった?",
        "でも、「それはそれ(だがつらい?)として!」とも思う(それは「違う。」かもしれない。)!",
        "(ほげ。)。",
        "ではまた。",
    ]

    with pytest.raises(TypeError):
        assert list(simple_splitter.split_punctuation([1, 2, "hoge"]))

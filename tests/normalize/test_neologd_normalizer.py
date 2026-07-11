# 出典： https://github.com/neologd/mecab-ipadic-neologd/wiki/Regexp.ja#python-written-by-hideaki-t--overlast

from ja_sentence_segmenter.normalize import neologd_normalizer


def test_normalize() -> None:
    assert next(neologd_normalizer.normalize("０１２３４５６７８９")) == "0123456789"
    assert next(neologd_normalizer.normalize("ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ")) == "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    assert next(neologd_normalizer.normalize("ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ")) == "abcdefghijklmnopqrstuvwxyz"
    assert next(neologd_normalizer.normalize("！”＃＄％＆’（）＊＋，－．／：；＜＞？＠［￥］＾＿｀｛｜｝")) == "!\"#$%&'()*+,-./:;<>?@[¥]^_`{|}"
    assert next(neologd_normalizer.normalize("＝。、・「」")) == "＝。、・「」"
    assert next(neologd_normalizer.normalize("ﾊﾝｶｸ")) == "ハンカク"
    assert next(neologd_normalizer.normalize("o₋o")) == "o-o"
    assert next(neologd_normalizer.normalize("majika━")) == "majikaー"
    assert next(neologd_normalizer.normalize("わ〰い")) == "わ～い"
    assert next(neologd_normalizer.normalize("スーパーーーー")) == "スーパー"
    assert next(neologd_normalizer.normalize("!#")) == "!#"
    assert next(neologd_normalizer.normalize("ゼンカク　スペース")) == "ゼンカクスペース"
    assert next(neologd_normalizer.normalize("お             お")) == "おお"
    assert next(neologd_normalizer.normalize("      おお")) == "おお"
    assert next(neologd_normalizer.normalize("おお      ")) == "おお"
    assert next(neologd_normalizer.normalize("検索 エンジン 自作 入門 を 買い ました!!!")) == "検索エンジン自作入門を買いました!!!"
    assert next(neologd_normalizer.normalize("アルゴリズム C")) == "アルゴリズムC"
    assert next(neologd_normalizer.normalize("　　　ＰＲＭＬ　　副　読　本　　　")) == "PRML副読本"
    assert next(neologd_normalizer.normalize("Coding the Matrix")) == "Coding the Matrix"
    assert (
        next(neologd_normalizer.normalize("南アルプスの　天然水　Ｓｐａｒｋｉｎｇ　Ｌｅｍｏｎ　レモン一絞り")) == "南アルプスの天然水Sparking Lemonレモン一絞り"
    )
    assert (
        next(neologd_normalizer.normalize("南アルプスの　天然水-　Ｓｐａｒｋｉｎｇ*　Ｌｅｍｏｎ+　レモン一絞り"))
        == "南アルプスの天然水-Sparking*Lemon+レモン一絞り"
    )
    # test remove tildes
    assert next(neologd_normalizer.normalize("わ〰い", True)) == "わい"

    assert list(neologd_normalizer.normalize(["０１２３４５６７８９", "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"])) == [
        "0123456789",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    ]

    assert list(neologd_normalizer.normalize(iter(["０１２３４５６７８９", "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"]))) == [
        "0123456789",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    ]

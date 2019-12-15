# 出典： https://github.com/neologd/mecab-ipadic-neologd/wiki/Regexp.ja#python-written-by-hideaki-t--overlast
import pytest

from ja_sentence_segmenter.normalize import neologd_normalizer


def test_normalize() -> None:
    assert "0123456789" == next(neologd_normalizer.normalize("０１２３４５６７８９"))
    assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" == next(neologd_normalizer.normalize("ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"))
    assert "abcdefghijklmnopqrstuvwxyz" == next(neologd_normalizer.normalize("ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ"))
    assert "!\"#$%&'()*+,-./:;<>?@[¥]^_`{|}" == next(neologd_normalizer.normalize("！”＃＄％＆’（）＊＋，－．／：；＜＞？＠［￥］＾＿｀｛｜｝"))
    assert "＝。、・「」" == next(neologd_normalizer.normalize("＝。、・「」"))
    assert "ハンカク" == next(neologd_normalizer.normalize("ﾊﾝｶｸ"))
    assert "o-o" == next(neologd_normalizer.normalize("o₋o"))
    assert "majikaー" == next(neologd_normalizer.normalize("majika━"))
    assert "わ～い" == next(neologd_normalizer.normalize("わ〰い"))
    assert "スーパー" == next(neologd_normalizer.normalize("スーパーーーー"))
    assert "!#" == next(neologd_normalizer.normalize("!#"))
    assert "ゼンカクスペース" == next(neologd_normalizer.normalize("ゼンカク　スペース"))
    assert "おお" == next(neologd_normalizer.normalize("お             お"))
    assert "おお" == next(neologd_normalizer.normalize("      おお"))
    assert "おお" == next(neologd_normalizer.normalize("おお      "))
    assert "検索エンジン自作入門を買いました!!!" == next(neologd_normalizer.normalize("検索 エンジン 自作 入門 を 買い ました!!!"))
    assert "アルゴリズムC" == next(neologd_normalizer.normalize("アルゴリズム C"))
    assert "PRML副読本" == next(neologd_normalizer.normalize("　　　ＰＲＭＬ　　副　読　本　　　"))
    assert "Coding the Matrix" == next(neologd_normalizer.normalize("Coding the Matrix"))
    assert "南アルプスの天然水Sparking Lemonレモン一絞り" == next(neologd_normalizer.normalize("南アルプスの　天然水　Ｓｐａｒｋｉｎｇ　Ｌｅｍｏｎ　レモン一絞り"))
    assert "南アルプスの天然水-Sparking*Lemon+レモン一絞り" == next(neologd_normalizer.normalize("南アルプスの　天然水-　Ｓｐａｒｋｉｎｇ*　Ｌｅｍｏｎ+　レモン一絞り"))
    # test remove tildes
    assert "わい" == next(neologd_normalizer.normalize("わ〰い", True))

    assert ["0123456789", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"] == list(neologd_normalizer.normalize(["０１２３４５６７８９", "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"]))

    assert ["0123456789", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"] == list(neologd_normalizer.normalize(iter(["０１２３４５６７８９", "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"])))
